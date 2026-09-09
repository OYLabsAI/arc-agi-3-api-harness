"""Subscription-backed Codex with native tools inside one continuous game turn.

Protocol validated against the installed Codex's generated JSON schema. No OAuth
credentials or opaque reasoning items are read, copied, or written by this client.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import queue
import signal
import subprocess
import tempfile
import threading
import time
import tomllib
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .prompt import SYSTEM
from .providers import codex_executable
from .types import TOOL_MODELS, ModelReply, ToolCall, tool_schemas

OVERLOAD_RECOVERY = {
    "retryable_error": "serverOverloaded",
    "delays_seconds": [5, 10, 20, 40, 60, 60, 60, 60],
    "decision_recovery_deadline_seconds": 900,
    "preserve_thread": True,
    "repeat_environment_actions": False,
}

TIMEOUT_RECOVERY = {
    "decision_timeout_seconds": 600,
    "delays_seconds": [0, 5],
    "interrupt_timeout_seconds": 20,
    "max_environment_idle_seconds": 840,
    "preserve_thread": True,
    "repeat_environment_actions": False,
}


def isolated_config(effort, fast_mode=False):
    disabled = (
        "shell_tool",
        "unified_exec",
        "multi_agent",
        "apps",
        "plugins",
        "hooks",
        "browser_use",
        "computer_use",
        "image_generation",
        "memories",
        "view_image",
        "goals",
        "sleep_tool",
        "tool_suggest",
        "skill_search",
    )
    config = {
        "model_provider": "openai",
        "model_reasoning_effort": effort,
        "service_tier": "fast" if fast_mode else "default",
        "features.fast_mode": fast_mode,
        "model_auto_compact_token_limit": 175000,
        "tool_output_token_limit": 32768,
        "project_doc_max_bytes": 0,
        "web_search": "disabled",
        "approval_policy": "never",
        "features.skip_host_skill_discovery": True,
        **{f"features.{name}": False for name in disabled},
    }
    # app-server has no exec --ignore-user-config flag. Explicitly disable each
    # configured MCP server as well as connectors; never inspect their secrets.
    root = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    path = root / "config.toml"
    if path.exists():
        with path.open("rb") as stream:
            names = list(tomllib.load(stream).get("mcp_servers", {}))
        for name in names:
            config[f"mcp_servers.{name}.enabled"] = False
    return config


class JsonRpcProcess:
    def __init__(self, binary, directory, config):
        args = [binary, "app-server", "--stdio"]
        for key, value in config.items():
            # Values here are strings, integers, or booleans: JSON literals are
            # also valid TOML literals. They are argv values, never shell code.
            args.extend(["-c", key + "=" + json.dumps(value)])
        keep = (
            "HOME",
            "PATH",
            "USER",
            "LOGNAME",
            "TMPDIR",
            "CODEX_HOME",
            "LANG",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
        )
        self.process = subprocess.Popen(
            args,
            cwd=directory,
            env={k: os.environ[k] for k in keep if k in os.environ},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        self.messages = queue.Queue()
        self.errors = deque(maxlen=12)
        self.sequence = 0
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._read_errors, daemon=True).start()

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    self.messages.put(json.loads(line))
                except json.JSONDecodeError:
                    continue
        finally:
            self.messages.put(None)

    def _read_errors(self):
        for line in self.process.stderr:
            self.errors.append(line.rstrip())

    def send(self, message):
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def request(self, method, params):
        self.sequence += 1
        request_id = f"client-{self.sequence}"
        self.send({"id": request_id, "method": method, "params": params})
        return request_id

    def receive(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Codex did not return the next game decision within its time limit")
        try:
            message = self.messages.get(timeout=remaining)
        except queue.Empty:
            raise TimeoutError("Codex did not return the next game decision within its time limit") from None
        if message is None:
            raise RuntimeError("Codex App Server exited: " + "\n".join(self.errors)[-2000:])
        return message

    def close(self):
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=5)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()


class AppServerProvider:
    model: str
    effort: str
    decision_timeout_seconds = TIMEOUT_RECOVERY["decision_timeout_seconds"]

    def __init__(self, model="gpt-6-astra", effort="high", transport=None, config=None):
        self.model, self.effort = model, effort
        self.temp = tempfile.TemporaryDirectory(prefix="arc-native-solver-")
        self.config = dict(config) if config is not None else isolated_config(effort)
        self.fast_mode = self.config["features.fast_mode"]
        self.requested_service_tier = "fast" if self.fast_mode else "default"
        if self.config["service_tier"] != self.requested_service_tier:
            raise ValueError("Fast mode and service tier must agree")
        self.config_sha256 = hashlib.sha256(json.dumps(self.config, sort_keys=True).encode()).hexdigest()
        self.rpc = transport or JsonRpcProcess(codex_executable(), self.temp.name, self.config)
        self.thread_id = self.turn_id = None
        self.pending_request = self.pending_result = None
        self.total = {"inputTokens": 0, "outputTokens": 0}
        self.reported = dict(self.total)
        self.last_usage = {}
        self.usage_events = self.compactions = self.turns = self.final_restarts = 0
        self.events = []
        self.event_sink = None
        self.finalized = False
        self.turn_ended = False
        self.finalization_error = None
        self.response_ids = set()
        self.response_usage = {}
        self.missing_response_usage = 0
        self.service_tier = None
        self.turn_error = None
        self.provider_errors = self.overload_retries = 0
        self.decision_timeouts = self.timeout_retries = self.cancelled_tool_calls = 0
        self.last_environment_activity = None

    def set_event_sink(self, sink):
        self.event_sink = sink
        for event in self.drain_events():
            sink(event["kind"], event["data"])

    def _emit(self, kind, data):
        if self.event_sink is None:
            self.events.append({"kind": kind, "data": data})
        else:
            self.event_sink(kind, data)

    def _event(self, message):
        method, params = message.get("method"), message.get("params", {})
        if method == "rawResponse/completed":
            # Retain only IDs and usage, never raw response items or reasoning content.
            response_id = params["responseId"]
            if response_id in self.response_ids:
                return
            self.response_ids.add(response_id)
            usage = params.get("usage")
            if usage is None:
                self.missing_response_usage += 1
            else:
                for key, value in usage.items():
                    self.response_usage[key] = self.response_usage.get(key, 0) + value
            self._emit("provider_model_call", {
                "received_at": datetime.now(UTC).isoformat(),
                "response_id": response_id,
                "thread_id": params.get("threadId"),
                "turn_id": params.get("turnId"),
                "model_id": self.model,
                "reasoning_effort": self.effort,
                "fast_mode": self.fast_mode,
                "service_tier": self.service_tier,
                "config_sha256": self.config_sha256,
                "usage": usage,
                "source": "rawResponse/completed",
            })
        elif method == "model/rerouted":
            raise RuntimeError("Codex rerouted the model; rejecting evaluation")
        elif method == "thread/tokenUsage/updated":
            usage = params["tokenUsage"]
            self.total = usage["total"]
            self.last_usage = usage["last"]
            self.usage_events += 1
            self._emit("provider_usage", usage)
        elif method == "turn/started":
            self.turn_id = params["turn"]["id"]
            self.turn_ended = False
            self.turn_error = None
            self.turns += 1
        elif method == "turn/completed":
            self.turn_ended = True
            if params["turn"].get("error") and self.turn_error is None:
                self._event({"method": "error", "params": {
                    "error": params["turn"]["error"], "willRetry": False,
                    "threadId": self.thread_id, "turnId": params["turn"]["id"],
                }})
            self.turn_error = params["turn"].get("error") or self.turn_error
        elif method == "item/completed" and params.get("item", {}).get("type") == "contextCompaction":
            self.compactions += 1
            self._emit("provider_compaction", {"count": self.compactions})
        elif method == "error":
            error = params.get("error", {})
            self.provider_errors += 1
            self._emit("provider_error", {
                "received_at": datetime.now(UTC).isoformat(),
                "thread_id": params.get("threadId", self.thread_id),
                "turn_id": params.get("turnId", self.turn_id),
                "model_id": self.model, "reasoning_effort": self.effort,
                "fast_mode": self.fast_mode, "service_tier": self.service_tier,
                "config_sha256": self.config_sha256,
                "code": error.get("codexErrorInfo"), "message": error.get("message"),
                "will_retry_in_codex": params.get("willRetry", False),
                "response_id": None, "usage": None,
                "usage_note": "No response ID or token usage accompanies this error notification.",
            })
            if not params.get("willRetry", False):
                # Consume the terminal turn notification before recovering or
                # exiting. Starting a turn here could overlap the failed turn.
                self.turn_error = error
        elif method in ("item/started", "item/completed"):
            item_type = params.get("item", {}).get("type")
            if item_type in (
                "commandExecution",
                "mcpToolCall",
                "webSearch",
                "fileChange",
                "collabAgentToolCall",
                "imageGeneration",
            ):
                raise RuntimeError(f"Unexpected external tool {item_type}; rejecting evaluation")

    def _request(self, method, params, deadline):
        request_id = self.rpc.request(method, params)
        while True:
            message = self.rpc.receive(deadline)
            if message.get("id") == request_id and "method" not in message:
                if "error" in message:
                    if method == "turn/interrupt" and self.turn_ended:
                        # Completion can race with interruption. The observed
                        # completed turn is the barrier, even if interrupt says
                        # that there is no longer an active turn.
                        return {}
                    raise RuntimeError(f"Codex {method}: {message['error']}")
                return message["result"]
            if "id" in message and "method" in message:
                if method == "turn/interrupt":
                    self._reject_cancelled_tool(message)
                    continue
                self.rpc.send(
                    {
                        "id": message["id"],
                        "error": {"code": -32601, "message": "Not available in this evaluation"},
                    }
                )
                raise RuntimeError(f"Unexpected server request during {method}: {message['method']}")
            self._event(message)

    def _reject_cancelled_tool(self, message):
        params = message.get("params", {})
        self.rpc.send({"id": message["id"], "error": {
            "code": -32601, "message": "Decision cancelled before execution; no game action was taken",
        }})
        if (message["method"] != "item/tool/call" or params.get("threadId") != self.thread_id
                or params.get("turnId") != self.turn_id
                or params.get("tool", "").removeprefix("arc_") not in TOOL_MODELS):
            raise RuntimeError("Unexpected server request during interruption")
        self.cancelled_tool_calls += 1
        self._emit("provider_cancelled_tool", {
            "thread_id": self.thread_id, "turn_id": params.get("turnId"),
            "call_id": params.get("callId"), "tool": params.get("tool"),
            "executed": False,
        })

    def _interrupt_turn(self, deadline):
        if not self.turn_ended:
            self._request("turn/interrupt", {"threadId": self.thread_id, "turnId": self.turn_id}, deadline)
        while not self.turn_ended:
            message = self.rpc.receive(deadline)
            if "id" in message and "method" in message:
                self._reject_cancelled_tool(message)
            else:
                self._event(message)

    def _recovery_context(self, context, started, seconds_left, token_allowance):
        updated = dict(context)
        if "budget" in context:
            updated["budget"] = {
                **context["budget"],
                "seconds_left": round(max(0, seconds_left - (time.monotonic() - started)), 2),
            }
            if token_allowance is not None:
                spent = sum(max(0, self.accounted_usage().get(k, 0) - self.reported.get(k, 0))
                            for k in ("inputTokens", "outputTokens"))
                updated["budget"]["tokens_left"] = max(0, token_allowance - spent)
                if spent >= token_allowance:
                    raise RuntimeError("Token budget exhausted during model recovery")
        return updated

    def _start(self, deadline):
        self._request(
            "initialize",
            {
                "clientInfo": {"name": "arc_subscription_harness", "version": __version__},
                "capabilities": {"experimentalApi": True},
            },
            deadline,
        )
        self.rpc.send({"method": "initialized", "params": {}})
        account = self._request("account/read", {"refreshToken": False}, deadline)
        if (account.get("account") or {}).get("type") != "chatgpt":
            raise RuntimeError("Subscription provider requires an existing ChatGPT Codex login")
        result = self._request(
            "thread/start",
            {
                "model": self.model,
                "modelProvider": "openai",
                "allowProviderModelFallback": False,
                "cwd": self.temp.name,
                "ephemeral": True,
                "experimentalRawEvents": True,
                "serviceTier": self.requested_service_tier,
                "environments": [],
                "approvalPolicy": "never",
                "sandbox": "read-only",
                "config": self.config,
                "baseInstructions": SYSTEM
                + "\nTool names have an arc_ prefix. Continue calling tools until WIN or an exhausted budget. Select one tool at a time and await its result. A tokens_left value of null means no cumulative token cutoff.\n",
                "developerInstructions": "",
                "personality": "none",
                "dynamicTools": [
                    {
                        "type": "function",
                        "name": "arc_" + t["name"],
                        "description": t["description"],
                        "inputSchema": t["parameters"],
                    }
                    for t in tool_schemas()
                ],
            },
            deadline,
        )
        self.thread_id = result["thread"]["id"]
        if result.get("model", self.model) != self.model:
            raise RuntimeError("Codex selected a different model; rejecting evaluation")
        if result.get("reasoningEffort", self.effort) != self.effort:
            raise RuntimeError("Codex selected a different reasoning effort; rejecting evaluation")
        if result.get("instructionSources"):
            raise RuntimeError("Codex loaded external instruction files; rejecting evaluation")
        self.service_tier = result.get("serviceTier")
        accepted_tiers = ("fast", "priority") if self.fast_mode else (None, "default")
        if self.service_tier not in accepted_tiers:
            raise RuntimeError("Codex did not select the requested service tier; rejecting evaluation")
        self._emit("provider_started", {
            "provider": "codex-app-server",
            "model": self.model,
            "effort": self.effort,
            "thread_id": self.thread_id,
            "ephemeral": True,
            "auth": "chatgpt",
            "effective_model": result.get("model"),
            "effective_effort": result.get("reasoningEffort"),
            "fast_mode": self.fast_mode,
            "service_tier": self.service_tier,
            "config_sha256": self.config_sha256,
            "auto_compact_token_limit": self.config["model_auto_compact_token_limit"],
            "overload_recovery": OVERLOAD_RECOVERY,
            "timeout_recovery": TIMEOUT_RECOVERY,
        })

    @staticmethod
    def image_url(path):
        return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()

    def _start_turn(self, context, image_path, deadline):
        self.turn_error = None
        self.turn_ended = False
        inputs = [{"type": "text", "text": json.dumps(context)}]
        if image_path:
            inputs.append({"type": "image", "url": self.image_url(image_path), "detail": "original"})
        result = self._request(
            "turn/start",
            {
                "threadId": self.thread_id,
                "input": inputs,
                "effort": self.effort,
                "serviceTier": self.requested_service_tier,
                "summary": "auto",
            },
            deadline,
        )
        self.turn_id = result["turn"]["id"]

    def next(self, context, image_path, timeout, token_allowance):
        started = time.monotonic()
        if self.last_environment_activity is None:
            self.last_environment_activity = started
        seconds_left = context.get("budget", {}).get("seconds_left", timeout)
        recovery_deadline = min(
            started + min(seconds_left, max(timeout, OVERLOAD_RECOVERY["decision_recovery_deadline_seconds"])),
            self.last_environment_activity + TIMEOUT_RECOVERY["max_environment_idle_seconds"],
        )
        deadline = min(started + timeout, recovery_deadline)
        retries = 0
        timeout_retries = 0
        if self.thread_id is None:
            self._start(deadline)
            self._start_turn(context, image_path, deadline)
        elif self.pending_request is not None:
            if self.pending_result is None:
                raise RuntimeError("Previous native tool call has no result")
            payload = {"tool_result": self.pending_result, "current": context}
            content = [{"type": "inputText", "text": json.dumps(payload)}]
            if image_path:
                content.append({"type": "inputImage", "imageUrl": self.image_url(image_path)})
            self.rpc.send(
                {
                    "id": self.pending_request,
                    "result": {
                        "contentItems": content,
                        "success": "error" not in self.pending_result,
                    },
                }
            )
            self.pending_request = self.pending_result = None
        while True:
            try:
                message = self.rpc.receive(deadline)
            except TimeoutError as exc:
                self.decision_timeouts += 1
                self.provider_errors += 1
                self._emit("provider_error", {
                    "received_at": datetime.now(UTC).isoformat(), "source": "harness",
                    "thread_id": self.thread_id, "turn_id": self.turn_id,
                    "code": "decisionTimeout", "message": str(exc), "usage": None,
                    "response_id": None, "will_retry_in_codex": False,
                    "model_id": self.model, "reasoning_effort": self.effort,
                    "fast_mode": self.fast_mode, "service_tier": self.service_tier,
                    "config_sha256": self.config_sha256,
                })
                delays = TIMEOUT_RECOVERY["delays_seconds"]
                remaining = recovery_deadline - time.monotonic()
                if timeout_retries >= len(delays) or remaining <= delays[timeout_retries]:
                    raise TimeoutError("Codex decision timeout recovery budget exhausted") from exc
                # A timed-out inference never grants permission to repeat its
                # last tool response or to execute a late-arriving action.
                self._interrupt_turn(min(
                    time.monotonic() + TIMEOUT_RECOVERY["interrupt_timeout_seconds"], recovery_deadline,
                ))
                if self.turn_error and self.turn_error.get("codexErrorInfo") != "serverOverloaded":
                    raise RuntimeError("Codex turn failed during interruption: " + json.dumps(self.turn_error))
                delay = delays[timeout_retries]
                if recovery_deadline - time.monotonic() <= delay:
                    raise TimeoutError("Codex decision timeout recovery budget exhausted") from exc
                timeout_retries += 1
                self.timeout_retries += 1
                self._emit("provider_recovery", {
                    "status": "waiting", "retry": timeout_retries, "delay_seconds": delay,
                    "remaining_seconds": round(recovery_deadline - time.monotonic(), 3),
                    "thread_id": self.thread_id, "failed_turn_id": self.turn_id,
                    "code": "decisionTimeout", "turn_ended_confirmed": self.turn_ended,
                })
                if delay:
                    time.sleep(delay)
                deadline = min(time.monotonic() + timeout, recovery_deadline)
                updated = self._recovery_context(context, started, seconds_left, token_allowance)
                self._start_turn(updated, image_path, deadline)
                continue
            self._event(message)
            if "method" in message and "id" in message:
                if message["method"] != "item/tool/call":
                    self.rpc.send(
                        {
                            "id": message["id"],
                            "error": {"code": -32601, "message": "Only game tools are available"},
                        }
                    )
                    raise RuntimeError("Unexpected server request: " + message["method"])
                params = message["params"]
                name = params["tool"].removeprefix("arc_")
                if params["threadId"] != self.thread_id or name not in TOOL_MODELS:
                    raise RuntimeError("Native tool call is outside this game")
                if self.turn_error is not None:
                    raise RuntimeError("Native tool request followed a terminal provider error")
                self.pending_request = message["id"]
                total = self.accounted_usage()
                usage = {
                    k: max(0, total.get(k, 0) - self.reported.get(k, 0))
                    for k in ("inputTokens", "outputTokens")
                }
                self.reported = dict(total)
                if retries or timeout_retries:
                    self._emit("provider_recovery", {
                        "status": "recovered", "retries": retries + timeout_retries,
                        "overload_retries": retries, "timeout_retries": timeout_retries,
                        "thread_id": self.thread_id, "turn_id": self.turn_id,
                    })
                return ModelReply(
                    [ToolCall(name, params["arguments"], params["callId"])],
                    usage["inputTokens"],
                    usage["outputTokens"],
                )
            if message.get("method") == "turn/completed":
                turn = message["params"]["turn"]
                error = turn.get("error") or self.turn_error or {}
                if turn["status"] == "failed" and error.get("codexErrorInfo") == "serverOverloaded":
                    delays = OVERLOAD_RECOVERY["delays_seconds"]
                    remaining = recovery_deadline - time.monotonic()
                    if retries >= len(delays) or remaining <= delays[retries]:
                        raise RuntimeError("Codex overload recovery budget exhausted")
                    delay = delays[retries]
                    retries += 1
                    self.overload_retries += 1
                    self._emit("provider_recovery", {
                        "status": "waiting", "retry": retries, "delay_seconds": delay,
                        "remaining_seconds": round(remaining, 3),
                        "thread_id": self.thread_id, "failed_turn_id": self.turn_id,
                        "code": "serverOverloaded",
                    })
                    time.sleep(delay)
                    now = time.monotonic()
                    if now >= recovery_deadline:
                        raise TimeoutError("Codex overload recovery time limit exhausted")
                    deadline = min(now + timeout, recovery_deadline)
                    updated = self._recovery_context(context, started, seconds_left, token_allowance)
                    # The previous tool response was already sent exactly once.
                    # Resume the same conversation using only the current observation.
                    self._start_turn(updated, image_path, deadline)
                    continue
                if turn["status"] != "completed":
                    raise RuntimeError(
                        "Codex turn did not complete: " + json.dumps(error or turn["status"])
                    )
                self.final_restarts += 1
                if self.final_restarts > 2:
                    raise RuntimeError("Model repeatedly ended without choosing a game tool")
                self._start_turn(
                    {"instruction": "The game is unfinished. Continue with a game tool.", **context},
                    image_path,
                    deadline,
                )

    def result(self, call, result):
        if self.pending_request is None:
            raise RuntimeError("No native tool request is pending")
        self.pending_result = result
        if call.name == "act" and result.get("executed", 0) > 0:
            self.last_environment_activity = time.monotonic()

    def drain_events(self):
        events, self.events = self.events, []
        return events

    def accounted_usage(self):
        # Raw responses include compaction inference omitted from thread counters.
        # Retain both, and use the greater observed total if notifications lag.
        return {k: max(self.total.get(k, 0), self.response_usage.get(k, 0))
                for k in self.total.keys() | self.response_usage.keys()}

    def stats(self):
        return {
            "provider": "codex-app-server",
            "native_turns": self.turns,
            "usage_events": self.usage_events,
            "compactions": self.compactions,
            "total_usage": self.total,
            "accounted_usage": self.accounted_usage(),
            "provider_errors": self.provider_errors,
            "overload_retries": self.overload_retries,
            "overload_recovery": OVERLOAD_RECOVERY,
            "timeout_recovery": TIMEOUT_RECOVERY,
            "decision_timeouts": self.decision_timeouts,
            "timeout_retries": self.timeout_retries,
            "cancelled_tool_calls": self.cancelled_tool_calls,
            "completed_model_responses": len(self.response_ids),
            "response_usage": self.response_usage,
            "missing_response_usage": self.missing_response_usage,
            "per_call_usage_reconciled": bool(self.response_ids) and not self.missing_response_usage
            and all(self.response_usage.get(k, 0) == self.total.get(k, 0)
                    for k in ("inputTokens", "cachedInputTokens", "outputTokens", "reasoningOutputTokens")),
            "last_request_usage": self.last_usage,
            "usage_complete": self.finalized and self.turn_ended and self.finalization_error is None
            and not self.missing_response_usage and not self.provider_errors,
            "finalization_error": self.finalization_error,
        }

    def finalize(self):
        """Collect late usage after interrupting; never send the final tool result.

        Native tool requests can precede the corresponding usage notification.
        Waiting for turn completion avoids losing the final request's accounting.
        """
        if self.finalized or self.turn_id is None:
            return
        deadline = time.monotonic() + TIMEOUT_RECOVERY["interrupt_timeout_seconds"]
        try:
            self._interrupt_turn(deadline)
        except Exception as exc:
            self.finalization_error = f"{type(exc).__name__}: {exc}"
        self.finalized = True

    def close(self):
        # Interrupt while the model waits on its tool result; never start another
        # inference after the runner has ended or the environment has won.
        self.rpc.close()
        self.temp.cleanup()
