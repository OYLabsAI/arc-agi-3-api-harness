from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path

from pydantic import ValidationError

from .environment import redact_credentials
from .perception import check_prediction, describe, difference
from .store import Store, write_json
from .types import TOOL_MODELS, Limits


class Runner:
    def __init__(
        self, environment, provider, directory: Path, limits: Limits, game_id="undisclosed", progress=None
    ):
        self.env, self.provider, self.limits = environment, provider, limits
        self.store = Store(directory)
        self.game_id = game_id
        self.progress = progress or (lambda message: None)
        self.actions = self.calls = self.input_tokens = self.output_tokens = 0
        self.started = time.monotonic()
        self.obs = None
        self.stop_reason = None
        self.last_result = None
        if hasattr(provider, "set_event_sink"):
            provider.set_event_sink(self.provider_event)

    def provider_event(self, kind, data):
        self.store.event(kind, data)
        if kind == "provider_recovery":
            detail = (f"retry {data['retry']} in {data['delay_seconds']}s"
                      if data["status"] == "waiting" else "recovered")
            self.progress(f"{self.game_id} · model recovery · {detail} · {self.actions} actions used")
        elif kind == "provider_error":
            self.progress(f"{self.game_id} · provider error · {data['code']}")

    def budget(self):
        return {
            "actions_left": max(0, self.limits.max_actions - self.actions),
            "model_calls_left": max(0, self.limits.max_calls - self.calls),
            "tokens_left": (
                max(0, self.limits.max_tokens - self.input_tokens - self.output_tokens)
                if self.limits.max_tokens
                else None
            ),
            "seconds_left": round(max(0, self.limits.max_seconds - (time.monotonic() - self.started)), 2),
        }

    def exhausted(self, include_calls=True):
        for name, left in self.budget().items():
            if name == "model_calls_left" and not include_calls:
                continue
            if left is not None and left <= 0:
                return name.replace("_left", "_budget")
        return None

    def context(self):
        # Game identifier and human baselines are deliberately absent from model input.
        return {
            "observation": self.obs.metadata(),
            "perception": describe(self.obs.grid, include_rows=True),
            "budget": self.budget(),
        }

    def dispatch(self, call):
        if call.name not in TOOL_MODELS:
            raise ValueError(f"Unknown tool: {call.name}")
        args = TOOL_MODELS[call.name].model_validate(call.arguments)
        if call.name == "act":
            return self.act(args)
        if call.name == "remember":
            return self.store.remember(args)
        if call.name == "history":
            return self.store.history(args.query, args.limit)
        if call.name == "plan":
            return self.store.path(self.obs.fingerprint, args.target_hash)
        if call.name == "stop":
            terminal_reason = "win" if self.obs.state == "WIN" else self.exhausted()
            if terminal_reason:
                self.stop_reason = terminal_reason
                return {"stopped": True, "reason": terminal_reason}
            budget = self.budget()
            self.store.event("early_stop_rejected", {
                "reason": args.reason, "observation": self.obs.metadata(), "budget": budget,
            })
            return {
                "stopped": False,
                "reason": "The game is unfinished and budget remains. Continue from the observed evidence, "
                          "revisit unsupported assumptions, and test alternative hypotheses. "
                          "Only environment WIN or an exhausted budget ends this game.",
                "budget": budget,
            }
        if call.name == "inspect":
            observation = self.obs
            if args.observation_index is not None:
                if args.observation_index >= len(self.store.observations):
                    raise ValueError("observation_index has not occurred")
                observation = self.store.observations[args.observation_index]
            try:
                grid = observation.frames[args.frame_index]
            except IndexError:
                raise ValueError("frame_index is outside the observed animation") from None
            if args.crop is not None:
                x, y, w, h = args.crop
                if min(x, y) < 0 or min(w, h) < 1 or x + w > grid.shape[1] or y + h > grid.shape[0]:
                    raise ValueError("Crop must fit inside the observed frame")
                grid = grid[y : y + h, x : x + w]
            return {
                "crop_origin": args.crop[:2] if args.crop else [0, 0],
                **describe(grid, include_rows=True),
            }
        raise AssertionError("Unreachable tool")

    def act(self, request):
        if len(request.actions) > self.limits.max_batch:
            raise ValueError(f"At most {self.limits.max_batch} actions per batch")
        if len(request.actions) > 1 and any(
            not (a.expected_pixels or a.expected_state is not None or a.expected_levels is not None)
            for a in request.actions
        ):
            raise ValueError(
                "Each action in a batch needs a testable prediction; use a single action to explore"
            )
        transitions, interrupted = [], None
        for action in request.actions:
            if self.exhausted(include_calls=False):
                interrupted = self.exhausted(include_calls=False)
                break
            if self.obs.state == "WIN":
                interrupted = "win"
                break
            if self.obs.state in ("GAME_OVER", "NOT_PLAYED") and action.name != "RESET":
                interrupted = "only_reset_is_legal"
                break
            if action.name != "RESET" and action.name not in self.obs.available_actions:
                interrupted = "action_not_available"
                break
            before = self.obs
            # Write ahead of the effect; ambiguous remote failures never trigger a replay.
            self.actions += 1
            self.store.event(
                "action_submitted",
                {
                    "number": self.actions,
                    "action": action.model_dump(),
                    "experiment": request.experiment,
                    "before": before.fingerprint,
                },
            )
            try:
                self.obs = self.env.step(action, request.experiment)
            except Exception as exc:
                raise RuntimeError(f"Environment action outcome is uncertain; not retrying: {exc}") from exc
            self.store.observation(self.obs)
            prediction = check_prediction(action, self.obs)
            delta = difference(before.grid, self.obs.grid)
            transition = self.store.transition(
                before, action, self.obs, request.experiment, prediction, delta
            )
            # Full evidence remains in the journal. Avoid multiplying hundreds of sampled
            # pixels across batched results, repeated context, and the provider transcript.
            transitions.append({**transition, "delta": {k: v for k, v in delta.items() if k != "sample"}})
            self.progress(
                f"{self.game_id} · action {self.actions} · {action.name} · {self.obs.levels_completed}/{self.obs.win_levels} levels · {self.obs.state}"
            )
            if self.obs.state == "WIN":
                interrupted = "win"
            elif self.obs.state == "GAME_OVER":
                interrupted = "game_over"
            elif self.obs.levels_completed != before.levels_completed:
                interrupted = "level_changed"
            elif not prediction["matched"]:
                interrupted = "prediction_mismatch"
            elif before.fingerprint == self.obs.fingerprint:
                interrupted = "no_observable_change"
            if interrupted:
                break
        return {
            "executed": len(transitions),
            "interrupted": interrupted,
            "transitions": transitions,
            "observation": self.obs.metadata(),
        }

    def run(self):
        error = None
        self.store.event(
            "run_started",
            {
                "game_id": self.game_id,
                "provider": type(self.provider).__name__,
                "model": self.provider.model,
                "effort": self.provider.effort,
                "limits": asdict(self.limits),
            },
        )
        try:
            self.obs = self.env.initial()
            self.store.observation(self.obs)
            while not self.stop_reason and self.obs.state != "WIN":
                reason = self.exhausted()
                if reason:
                    self.stop_reason = reason
                    break
                self.calls += 1
                self.progress(f"{self.game_id} · thinking {self.calls} · {self.actions} actions used")
                budget = self.budget()
                reply = self.provider.next(
                    self.context(),
                    self.store.directory / "current.png",
                    timeout=max(0.1, min(
                        getattr(self.provider, "decision_timeout_seconds", 300), budget["seconds_left"],
                    )),
                    token_allowance=budget["tokens_left"],
                )
                self.input_tokens += reply.input_tokens
                self.output_tokens += reply.output_tokens
                if hasattr(self.provider, "drain_events"):
                    for event in self.provider.drain_events():
                        self.store.event(event["kind"], event["data"])
                self.store.event(
                    "model_reply",
                    {
                        "call": self.calls,
                        "input_tokens": reply.input_tokens,
                        "output_tokens": reply.output_tokens,
                        "tools": [{"name": c.name, "arguments": c.arguments} for c in reply.calls],
                    },
                )
                # A final model call may act; max_calls gates inference, not its already-returned decision.
                if not reply.calls:
                    raise RuntimeError("Model returned no tool calls")
                if len(reply.calls) != 1:
                    for call in reply.calls:
                        self.provider.result(
                            call, {"error": "Return exactly one tool call per turn; nothing executed"}
                        )
                    continue
                call = reply.calls[0]
                if (
                    self.limits.max_tokens
                    and self.input_tokens + self.output_tokens >= self.limits.max_tokens
                ):
                    self.stop_reason = "tokens_budget"
                    self.provider.result(call, {"stopped": True, "reason": self.stop_reason})
                    break
                if time.monotonic() - self.started >= self.limits.max_seconds:
                    self.stop_reason = "seconds_budget"
                    self.provider.result(call, {"stopped": True, "reason": self.stop_reason})
                    break
                try:
                    result = self.dispatch(call)
                except (ValueError, ValidationError) as exc:
                    result = {
                        "error": str(exc),
                        "hint": "Correct the tool arguments; no invalid command was submitted.",
                    }
                self.last_result = result
                self.store.event("tool_result", {"tool": call.name, "result": result})
                self.provider.result(call, result)
            if self.obs.state == "WIN":
                self.stop_reason = "win"
        except KeyboardInterrupt:
            self.stop_reason, error = "interrupted", "Interrupted by user"
        except Exception as exc:
            self.stop_reason, error = "error", redact_credentials(f"{type(exc).__name__}: {exc}")
            self.store.event(
                "error",
                {
                    "message": error,
                    "last_action_may_have_executed": self.actions > len(self.store.transitions),
                },
            )
        finally:
            finalization_errors, provider_stats = [], None

            def finalization_failed(phase, exc):
                nonlocal error
                finalization_errors.append({"phase": phase, "error_type": type(exc).__name__})
                self.stop_reason = "interrupted" if isinstance(exc, KeyboardInterrupt) else "error"
                error = error or f"Provider {phase} failed ({type(exc).__name__})"

            if hasattr(self.provider, "finalize"):
                try:
                    self.provider.finalize()
                    for event in self.provider.drain_events():
                        self.store.event(event["kind"], event["data"])
                except (Exception, KeyboardInterrupt) as exc:
                    finalization_failed("finalize", exc)
            if hasattr(self.provider, "stats"):
                # The native provider exposes session totals; tool requests can
                # arrive before their matching usage notification.
                try:
                    provider_stats = self.provider.stats()
                    usage = provider_stats.get("accounted_usage", provider_stats.get("total_usage", {}))
                    self.input_tokens = max(self.input_tokens, usage.get("inputTokens", 0))
                    self.output_tokens = max(self.output_tokens, usage.get("outputTokens", 0))
                except (Exception, KeyboardInterrupt) as exc:
                    finalization_failed("stats", exc)
            try:
                self.provider.close()
            except (Exception, KeyboardInterrupt) as exc:
                finalization_failed("close", exc)
            result = {
                "game_id": self.game_id,
                "status": self.stop_reason,
                "error": error,
                "won": bool(self.obs and self.obs.state == "WIN"),
                "levels_completed": self.obs.levels_completed if self.obs else 0,
                "win_levels": self.obs.win_levels if self.obs else None,
                "actions_submitted": self.actions,
                "model_calls": self.calls,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "elapsed_seconds": round(time.monotonic() - self.started, 3),
                "predictions_tested": sum(t["prediction"]["tested"] for t in self.store.transitions),
                "prediction_failures": sum(not t["prediction"]["matched"] for t in self.store.transitions),
                "model": self.provider.model,
                "effort": self.provider.effort,
                "limits": asdict(self.limits),
                "official_benchmark_score_percent": None,
            }
            if provider_stats is not None:
                result["provider_stats"] = provider_stats
            if finalization_errors:
                result["finalization_errors"] = finalization_errors
            try:
                self.store.event("run_finished", result)
            finally:
                try:
                    write_json(self.store.directory / "result.json", result)
                finally:
                    self.store.close()
        return result
