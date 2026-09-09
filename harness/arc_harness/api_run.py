"""One entry point for private local preparation, Kaggle fixtures, and authorized runs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import re
import signal
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

# The SDK otherwise loads cwd/.env at import time. Evaluator credentials are explicit.
os.environ["PYTHON_DOTENV_DISABLED"] = "1"

from . import __version__
from .api_budget import MAX_INPUT, BudgetStop, Ledger
from .api_provider import APIProvider
from .attribution import NamedArcadeSession
from .deadline import wall_timeout
from .environment import ARC_TRANSPORT, configure_transport
from .fixtures import CorridorFixture, demo_provider
from .release_integrity import ReleaseIntegrityError, snapshot_release, verify_release
from .report import render_replay
from .runner import Runner
from .scoring import selected_set_score
from .store import write_json
from .types import Limits

ROOT = Path(__file__).resolve().parent.parent


def require_billing_review(review=None):
    if review is None:
        review = json.loads((ROOT / "reports/PROVIDER-BILLING-REVIEW.json").read_text())
    expected = {"status": "SATISFIED", "model": "gpt-6-astra", "service_tier": "default",
                "transport": "model_max_input_no_count", "maximum_input_tokens": MAX_INPUT,
                "response_output_cap": 16000, "compaction_output_cap": 20000}
    if any(review.get(k) != v for k, v in expected.items()) or review.get("paid_launch_allowed") is not True:
        raise ValueError("Paid launch blocked: provider billing review NOT SATISFIED")


def load_plan(path, *, paid=False):
    path = Path(path).resolve()
    plan = json.loads(path.read_text())
    allowed = {"schema_version", "preset", "dataset", "provider", "authentication", "model", "effort",
               "service_tier", "max_input_tokens", "max_output_tokens", "compact_threshold", "approved_usd",
               "approval_record", "proposed_usd", "max_requests", "max_elapsed_seconds", "cleanup_seconds",
               "output_mode", "organizer_contract_confirmed", "harness_name", "team_name", "limits"}
    if set(plan) != allowed:
        raise ValueError("Run plan has missing or unknown fields")
    expected = {"schema_version": 1, "provider": "openai-responses", "authentication": "openai_api_key",
                "model": "gpt-6-astra", "effort": "high", "service_tier": "default"}
    if any(plan.get(k) != v for k, v in expected.items()):
        raise ValueError("Unsupported run configuration; no provider/model/auth fallback")
    if plan["preset"] not in ("pilot", "public-repeat", "organizer"):
        raise ValueError("Unknown evaluation preset")
    bounds = {"max_input_tokens": (MAX_INPUT, MAX_INPUT), "max_output_tokens": (1, 16000),
              "compact_threshold": (1, 175000), "max_requests": (1, 26000),
              "max_elapsed_seconds": (601, 41400), "cleanup_seconds": (180, 600)}
    for key, (low, high) in bounds.items():
        if type(plan[key]) is not int or not low <= plan[key] <= high:
            raise ValueError(f"Invalid {key}")
    if plan["compact_threshold"] > plan["max_input_tokens"]:
        raise ValueError("Compaction threshold exceeds input ceiling")
    if plan["cleanup_seconds"] >= plan["max_elapsed_seconds"]:
        raise ValueError("Cleanup margin exceeds deadline")
    if not isinstance(plan["limits"], dict) or set(plan["limits"]) != {
        "max_actions", "max_calls", "max_tokens", "max_seconds", "max_batch"
    }:
        raise ValueError("Explicit per-game limits required")
    for key, value in plan["limits"].items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Invalid per-game limit")
        if key != "max_seconds" and type(value) is not int:
            raise ValueError("Per-game counts must be integers")
    Limits(**plan["limits"])
    for name in ("harness_name", "team_name"):
        if not isinstance(plan[name], str) or not 1 <= len(plan[name].strip()) <= 100:
            raise ValueError("Explicit controller attribution required")
    if plan["preset"] == "organizer":
        if plan["output_mode"] != "protected":
            raise ValueError("Organizer evaluation requires protected output")
        if paid:
            raise ValueError("Organizer live execution disabled pending ARC delivery/retention agreement")
    elif plan["output_mode"] != "public":
        raise ValueError("Public preset requires public output policy")
    if not plan["dataset"]:
        raise ValueError("Explicit dataset required; organizer never falls back to the public set")
    dataset_path = (path.parent / plan["dataset"]).resolve()
    dataset = json.loads(dataset_path.read_text())
    if set(dataset) != {"schema_version", "interface", "games"} or dataset["schema_version"] != 1:
        raise ValueError("Invalid selection manifest")
    if dataset["interface"] != "arc-sdk-remote-ids":
        raise ValueError("Unsupported dataset interface; ARC must confirm organizer delivery")
    games = dataset["games"]
    if (not isinstance(games, list) or not games or len(games) != len(set(games))
            or any(not isinstance(g, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,100}", g)
                   for g in games)):
        raise ValueError("Nonempty unique safe environment identifiers required")
    public = json.loads((ROOT / "plans/public-games.json").read_text())["games"]
    if plan["preset"] == "public-repeat" and games != public:
        raise ValueError("Public repeat requires all 25 exact versions in frozen order")
    if plan["preset"] == "pilot" and games != public[:1]:
        raise ValueError("The prepared pilot is the first exact public environment only")
    if paid:
        from decimal import Decimal, InvalidOperation

        try:
            cap = Decimal(str(plan["approved_usd"]))
            valid = cap.is_finite() and 0 < cap <= 10000 and cap * 1000000 == int(cap * 1000000)
        except (InvalidOperation, TypeError, ValueError):
            valid = False
        if not valid or not isinstance(plan["approval_record"], str) or not plan["approval_record"].strip():
            raise ValueError("Owner-approved USD cap and approval record required before launch")
        if not os.environ.get("OPENAI_API_KEY", "").strip() or not os.environ.get("ARC_API_KEY", "").strip():
            raise ValueError("OPENAI_API_KEY and the intended ARC_API_KEY are required")
        require_billing_review()
    return plan, games, hashlib.sha256(dataset_path.read_bytes()).hexdigest()


def source_digest():
    return hashlib.sha256(b"".join(p.name.encode() + p.read_bytes()
                                  for p in sorted((ROOT / "arc_harness").glob("*.py")))).hexdigest()


def files_manifest(root):
    root = Path(root)
    return [{"path": str(p.relative_to(root)), "bytes": p.stat().st_size,
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()
            and not any(x in p.parts for x in ("__pycache__", ".pytest_cache", ".ruff_cache", ".git", ".venv"))
            and not p.name.endswith((".sqlite-wal", ".sqlite-shm")) and p.name != "evidence-manifest.json"]


class GlobalRunner(Runner):
    def __init__(self, *args, ledger, integrity_check, **kwargs):
        self.ledger = ledger
        self.integrity_check = integrity_check
        super().__init__(*args, **kwargs)

    def budget(self):
        self.integrity_check()
        result = super().budget()
        # Leave a complete ARC transport timeout before every next action.
        result["seconds_left"] = max(0, min(result["seconds_left"], self.ledger.remaining_seconds() - 130))
        return result


class APISession(NamedArcadeSession):
    def __init__(self, *args, **kwargs):
        import requests

        for key in ("ARC_BASE_URL", "ONLY_RESET_LEVELS", "OPERATION_MODE"):
            if os.environ.get(key):
                raise ValueError("Remove inherited ARC routing/method overrides before API evaluation")
        original = requests.Session

        def session():
            result = original()
            result.trust_env = False
            configure_transport(result)
            return result

        with patch("requests.Session", session):
            super().__init__(*args, **kwargs)

    def make(self, game_id):
        # Game wrappers create their own Session before the first RESET.
        import requests

        original = requests.Session

        def session():
            result = original()
            result.trust_env = False
            configure_transport(result)
            return result

        with patch("requests.Session", session):
            return super().make(game_id)


def evaluate(plan, games, dataset_sha, output, *, started=None, fixture=False, provider_factory=None,
             session_factory=None, expected_release_sha256=None):
    started = time.monotonic() if started is None else started
    if not fixture and not expected_release_sha256:
        raise ValueError("Separately reviewed release manifest hash required before paid launch")
    if not fixture:
        require_billing_review()
    release = verify_release(ROOT, expected_release_sha256)
    # Freeze an independent copy of the actual runtime configuration, including external approvals.
    plan, games = json.loads(json.dumps([plan, games]))
    configuration = json.dumps([plan, games, dataset_sha], sort_keys=True)

    def integrity_check():
        verify_release(ROOT, release["manifest_sha256"])
        if json.dumps([plan, games, dataset_sha], sort_keys=True) != configuration:
            raise ReleaseIntegrityError("Runtime plan or selection changed")

    if Path(output).resolve().is_relative_to(ROOT):
        raise ValueError("Run output must be outside the frozen release")
    directory = Path(output).resolve() / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                                         + "-" + uuid.uuid4().hex[:8])
    directory.mkdir(parents=True, mode=0o700)
    snapshot_release(ROOT, directory / "source", release["manifest_sha256"])
    ledger = Ledger(directory / "cost-ledger.sqlite", approved_usd=25 if fixture else plan["approved_usd"],
                    max_requests=plan["max_requests"], max_seconds=plan["max_elapsed_seconds"],
                    cleanup_seconds=plan["cleanup_seconds"], started=started)
    old_alarm = old_term = None
    previous_timer = signal.getitimer(signal.ITIMER_REAL) if hasattr(signal, "setitimer") else (0, 0)
    timer_started = time.monotonic()
    try:
        attribution = {"harness_name": plan["harness_name"], "team_name": plan["team_name"],
                       "run_id": directory.name, "source_sha256": source_digest(), "model": plan["model"],
                       "release_manifest_sha256": release["manifest_sha256"],
                       "effort": plan["effort"], "fast_mode": False, "mode": "competition",
                       "provider": "openai-responses", "authentication": "openai_api_key",
                       "evaluation_scope": plan["preset"], "source_visibility": "private",
                       "verified_by_arc_prize": False}
        manifest = {"version": __version__, "created_at": datetime.now(UTC).isoformat(),
                    "source_sha256": source_digest(), "selected_games": games, "dataset_sha256": dataset_sha,
                    "release_manifest_sha256": release["manifest_sha256"],
                    "runtime_configuration_sha256": hashlib.sha256(configuration.encode()).hexdigest(),
                    "scope": "synthetic_fixture" if fixture else plan["preset"], "plan": plan,
                    "model": plan["model"], "effort": plan["effort"], "attribution": attribution,
                    "arc_transport": ARC_TRANSPORT, "cross_game_memory": False,
                    "fixture": fixture, "python": sys.version, "platform": sys.platform,
                    "dependency_versions": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}}
        write_json(directory / "manifest.json", manifest)
        session, results, card, error, close_error = None, [], None, None, None
        exit_code = 1
        if hasattr(signal, "setitimer"):
            def interrupted(signum, frame):
                raise KeyboardInterrupt

            old_alarm = signal.signal(signal.SIGALRM, interrupted)
            old_term = signal.signal(signal.SIGTERM, interrupted)
            signal.setitimer(signal.ITIMER_REAL, max(0.001, ledger.remaining_seconds()))
        try:
            ledger.check_time(660)
            integrity_check()
            if not fixture:
                probe = APIProvider(ledger, integrity_check=integrity_check)
                try:
                    write_json(directory / "api-preflight.json", probe.preflight())
                finally:
                    probe.close()
                session = (session_factory or APISession)(
                    "competition", directory / "empty-environments", directory / "sdk-recordings",
                    attribution=attribution)
                available = session.games()
                if any(g not in available for g in games):
                    raise ValueError("Required exact environment unavailable; no scorecard created")
            for game in games:
                ledger.check_time(660)
                integrity_check()
                provider = (provider_factory(ledger) if provider_factory else demo_provider() if fixture else
                            APIProvider(ledger, max_output_tokens=plan["max_output_tokens"],
                                        max_input_tokens=plan["max_input_tokens"],
                                        compact_threshold=plan["compact_threshold"]))
                provider.integrity_check = integrity_check
                try:
                    environment = CorridorFixture() if fixture else session.make(game)
                except BaseException:
                    provider.close()
                    raise
                finally:
                    if session:
                        write_json(directory / "scorecard-session.json", session.scorecard_reference())
                result = GlobalRunner(environment, provider, directory / game, Limits(**plan["limits"]),
                                      game_id=game, ledger=ledger, integrity_check=integrity_check).run()
                results.append(result)
                write_json(directory / "results.json", results)
                write_json(directory / "cost-report.json", ledger.report())
                render_replay(directory / game)
                if result["status"] in ("error", "interrupted"):
                    error = result["status"]
                    break
        except KeyboardInterrupt:
            error = "interrupted_or_global_deadline"
        except BudgetStop as exc:
            error = str(exc)
        except Exception as exc:
            error = type(exc).__name__  # Never copy raw service bodies to ordinary logs.
        finally:
            if old_alarm is not None:
                signal.setitimer(signal.ITIMER_REAL, max(0.001, ledger.deadline - time.monotonic()))
            # Persist a conservative terminal marker before any remote closure or export.
            # If finalization is interrupted, this marker cannot be mistaken for success.
            write_json(directory / "summary.json", {
                "scope": manifest["scope"], "fixture": fixture, "run_id": directory.name,
                "exit_code": 1, "complete_selected_set": False, "finalization_status": "in_progress",
                "evaluation_error": error, "games_selected": len(games), "games_run": len(results),
                "unrun_games": games[len(results):],
            })
            write_json(directory / "results.json", results)
            write_json(directory / "cost-report.json", ledger.report())
            if session:
                try:
                    close_seconds = min(130, ledger.deadline - time.monotonic() - 30)
                    with wall_timeout(close_seconds, "scorecard_cleanup_deadline"):
                        card = session.close()
                    if session.scorecard_reference()["card_id"] and card is None:
                        close_error = "scorecard_close_returned_no_evidence"
                except (Exception, KeyboardInterrupt) as exc:
                    close_error = type(exc).__name__
            try:
                integrity_check()
                verify_release(directory / "source", release["manifest_sha256"])
                release_status = "RELEASE FILE CHECKS PASSED"
            except ReleaseIntegrityError:
                error = "release_integrity_failed"
                release_status = "NOT SATISFIED"
            write_json(directory / "release-integrity.json", {
                "status": release_status, "release_manifest_sha256": release["manifest_sha256"],
                "files_checked": len(release["files"]), "full_submission_compliance_established": False,
            })
            write_json(directory / "results.json", results)
            write_json(directory / "scorecard.json", {"sdk_scorecard": card, "close_error": close_error})
            cost = ledger.report()
            write_json(directory / "cost-report.json", cost)
            complete = len(results) == len(games) and not error and not close_error
            score = None
            if card:
                try:
                    score = selected_set_score(card, games, allow_unplayed=plan["preset"] == "pilot")
                except (ValueError, TypeError, KeyError):
                    error, complete = "scorecard_validation_failed", False
            summary = {"scope": manifest["scope"], "games_selected": len(games), "games_run": len(results),
                       "games_won": sum(r["won"] for r in results), "unrun_games": games[len(results):],
                       "complete_selected_set": bool(complete), "evaluation_error": error,
                       "scorecard_error": close_error, "selected_set_score_percent": score,
                       "verified_benchmark_score_percent": None,
                       "actions_submitted": sum(r["actions_submitted"] for r in results),
                       "reported_tokens": sum(r["input_tokens"] + r["output_tokens"] for r in results),
                       "cost": {k: v for k, v in cost.items() if k != "requests"},
                       "finished_at": datetime.now(UTC).isoformat(), "elapsed_seconds": time.monotonic() - started,
                       "fixture": fixture, "run_id": directory.name}
            summary["release_integrity_status"] = release_status
            exit_code = 0 if complete and not cost["uncertain_requests"] else 1
            summary["exit_code"] = exit_code
            write_json(directory / "summary.json", summary)
            try:
                from .api_audit import export_api_run

                audit = export_api_run(directory)
                if not audit["passed"]:
                    exit_code = 1
                    summary["audit_passed"] = False
            except Exception as exc:
                exit_code = 1
                write_json(directory / "export-error.json", {"error_type": type(exc).__name__})
            if plan["preset"] == "public-repeat":
                from .public_acceptance import public_score_gate

                acceptance = public_score_gate(card, results, games, run_id=directory.name,
                                               source_sha256=manifest["source_sha256"], fixture=fixture)
                write_json(directory / "public-score-acceptance.json", acceptance)
                summary["public_100_status"] = acceptance["status"]
                if not acceptance["passed"]:
                    exit_code = 1
            summary["exit_code"] = exit_code
            summary["finalization_status"] = "completed"
            write_json(directory / "summary.json", summary)
            write_json(directory / "evidence-manifest.json", {"files": files_manifest(directory)})
        return exit_code, directory, summary
    except BaseException as exc:
        # Existing artifacts remain; an aborted finalizer is never a successful run.
        try:
            write_json(directory / "finalization-error.json", {"exit_code": 1,
                       "error_type": type(exc).__name__, "finalization_status": "failed"})
            path = directory / "summary.json"
            failed = json.loads(path.read_text()) if path.exists() else {"run_id": directory.name}
            failed.update(exit_code=1, complete_selected_set=False, finalization_status="failed",
                          finalization_error=type(exc).__name__)
            write_json(path, failed)
        except (OSError, ValueError):
            pass  # Persistent storage failure cannot be repaired by inventing evidence.
        raise
    finally:
        if old_alarm is not None:
            signal.setitimer(signal.ITIMER_REAL, 0)
        try:
            ledger.close()
        finally:
            if old_alarm is not None:
                signal.signal(signal.SIGALRM, old_alarm)
                signal.signal(signal.SIGTERM, old_term)
                left = previous_timer[0] - (time.monotonic() - timer_started)
                if previous_timer[0] and left > 0:
                    signal.setitimer(signal.ITIMER_REAL, left, previous_timer[1])



def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepared API evaluation; paid launch requires an approved plan")
    parser.add_argument("command", choices=("check", "fixture", "run"))
    parser.add_argument("--plan", type=Path, default=ROOT / "plans/pilot.json")
    parser.add_argument("--output", type=Path, default=ROOT.parent / "runs")
    parser.add_argument("--expected-release-sha256")
    parser.add_argument("--started-monotonic", type=float)
    args = parser.parse_args(argv)
    try:
        plan, games, dataset_sha = load_plan(args.plan, paid=args.command == "run")
        if args.command == "check":
            release = verify_release(ROOT, args.expected_release_sha256)
            print(json.dumps({"local_configuration_valid": True, "selected_count": len(games),
                              "release_manifest_sha256": release["manifest_sha256"],
                              "source_sha256": source_digest(), "paid_authorization_present":
                              plan["approved_usd"] is not None, "credentials_checked": False}))
            return 0
        code, directory, summary = evaluate(plan, games, dataset_sha, args.output,
                                             started=args.started_monotonic, fixture=args.command == "fixture",
                                             expected_release_sha256=args.expected_release_sha256)
        print(json.dumps({"directory": str(directory), "run_id": summary["run_id"], "exit_code": code,
                          "fixture": summary["fixture"], "games_run": summary["games_run"],
                          "games_selected": summary["games_selected"]}))
        return code
    except Exception as exc:
        print(json.dumps({"preflight_failed": True, "error_type": type(exc).__name__,
                          "message": str(exc) if isinstance(exc, ValueError) else "See local configuration"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
