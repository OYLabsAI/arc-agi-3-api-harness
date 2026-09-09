from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .app_server import OVERLOAD_RECOVERY, TIMEOUT_RECOVERY, AppServerProvider, isolated_config
from .attribution import NamedArcadeSession, attribution_for
from .environment import ARC_TRANSPORT, ArcadeSession
from .providers import CodexProvider, ResponsesProvider, codex_executable
from .report import render_replay
from .runner import Runner
from .scoring import selected_set_score
from .store import write_json
from .types import Limits


def new_directory(root):
    return Path(root).resolve() / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])


def parser():
    p = argparse.ArgumentParser(
        description="ARC-AGI-3 research harness. A 100% score is a target, not a claim."
    )
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check local dependencies and authentication availability")
    games = sub.add_parser("games", help="Discover official environment IDs")
    games.add_argument("--mode", choices=["online", "offline"], default="online")
    games.add_argument("--environments-dir", default="environment_files")
    run = sub.add_parser("run", help="Evaluate once on an explicit game set")
    selection = run.add_mutually_exclusive_group(required=True)
    selection.add_argument("--games", nargs="+", help="IDs or unambiguous prefixes")
    selection.add_argument("--all", action="store_true", help="Evaluate every discovered environment")
    run.add_argument("--provider", choices=["codex", "codex-native", "openai"], default="codex")
    run.add_argument("--model", default="gpt-6-astra")
    run.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max", "ultra"], default="high")
    run.add_argument("--fast-mode", action=argparse.BooleanOptionalAction, default=False,
                     help="Pin Fast mode for all games with the Codex subscription provider")
    run.add_argument("--mode", choices=["online", "offline", "competition"], default="online")
    run.add_argument("--environments-dir", default="environment_files")
    run.add_argument("--max-actions", type=int, default=300)
    run.add_argument("--max-calls", type=int, default=100)
    run.add_argument(
        "--max-tokens", type=int, default=250000, help="Cumulative input+output cutoff; 0 disables it"
    )
    run.add_argument("--max-seconds", type=float, default=1800)
    run.add_argument("--max-batch", type=int, default=8)
    run.add_argument("--output", default="runs")
    run.add_argument("--harness-name", help="Controller-only name attached to a subscription scorecard")
    run.add_argument("--team-name", help="Team attribution; requires --harness-name and an ARC_API_KEY")
    demo = sub.add_parser("demo", help="Run a synthetic integration fixture (not benchmark performance)")
    demo.add_argument("--output", default="runs")
    replay = sub.add_parser("replay", help="Build a standalone HTML replay from a game run")
    replay.add_argument("directory", type=Path)
    return p


def doctor():
    data = {
        "harness": __version__,
        "python": sys.version.split()[0],
        "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
        "arc_api_key_present": bool(os.environ.get("ARC_API_KEY")),
        "note": "Online ARC development can use an anonymous key. Offline mode needs local environments.",
    }
    for name in ("arc-agi", "arcengine", "openai", "numpy", "pillow"):
        try:
            data[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            data[name] = "missing"
    try:
        binary = codex_executable()
        data["codex_binary"] = binary
        result = subprocess.run(
            [binary, "login", "status"], capture_output=True, text=True, timeout=10, check=False
        )
        data["codex_login_available"] = result.returncode == 0
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        data["codex"] = str(exc)
    print(json.dumps(data, indent=2))


def resolve_games(requested, available):
    result = []
    for prefix in requested:
        matches = [g for g in available if g == prefix or g.startswith(prefix + "-")]
        if len(matches) != 1:
            raise ValueError(
                f"Game {prefix!r} matches {len(matches)} environments; use an exact ID from 'games'"
            )
        if matches[0] in result:
            raise ValueError("Duplicate games are not permitted in a single evaluation")
        result.append(matches[0])
    return result


def save_scorecard_snapshot(directory, session, selected, games_finished, *, before_close=False):
    payload = {
        "captured_at": datetime.now(UTC).isoformat(),
        "games_finished": games_finished,
        "provisional": True,
        "before_close": before_close,
        "sdk_scorecard": None,
        "selected_set_score_percent": None,
        "snapshot_error": None,
        "skipped_reason": None,
    }
    try:
        if getattr(session, "mode", None) == "competition":
            payload["skipped_reason"] = "Competition mode forbids inflight scorecard reads"
            card = None
        else:
            card = session.snapshot()
        payload["sdk_scorecard"] = card
        payload["selected_set_score_percent"] = selected_set_score(card, selected)
    except Exception as exc:
        # A read-only score lookup must not change the game attempt. SDK errors
        # can embed response bodies; retain the type without leaking credentials.
        payload["snapshot_error"] = type(exc).__name__
    snapshots = directory / "scorecard-partials"
    snapshots.mkdir(exist_ok=True)
    filename = "before-close.json" if before_close else f"{games_finished:03d}.json"
    write_json(snapshots / filename, payload)
    return payload


def evaluate(args):
    if args.provider == "openai":
        raise ValueError("Use python -m arc_harness.api_run with an approved run plan for API evaluations")
    limits = Limits(args.max_actions, args.max_calls, args.max_tokens, args.max_seconds, args.max_batch)
    if args.fast_mode and args.provider != "codex-native":
        raise ValueError("--fast-mode requires --provider codex-native")
    if args.provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("Set OPENAI_API_KEY before running with --provider openai")
    directory = new_directory(args.output)
    source_sha256 = hashlib.sha256(
        b"".join(p.name.encode() + p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py")))
    ).hexdigest()
    attribution = attribution_for(args, source_sha256, directory.name)
    directory.mkdir(parents=True)
    session = (
        NamedArcadeSession(args.mode, args.environments_dir, directory / "sdk-recordings",
                           attribution=attribution)
        if attribution
        else ArcadeSession(args.mode, args.environments_dir, directory / "sdk-recordings")
    )
    available = session.games()
    selected = available if args.all else resolve_games(args.games, available)
    if not selected:
        raise ValueError(
            "No environments found. Online mode discovers public games; offline mode requires local files."
        )
    snapshot = directory / "source" / "arc_harness"
    snapshot.mkdir(parents=True)
    for path in Path(__file__).parent.glob("*.py"):
        shutil.copyfile(path, snapshot / path.name)
    manifest = {
        "version": __version__,
        "created_at": datetime.now(UTC).isoformat(),
        "mode": args.mode,
        "provider": args.provider,
        "model": args.model,
        "effort": args.effort,
        "fast_mode": args.fast_mode if args.provider == "codex-native" else None,
        "native_config": isolated_config(args.effort, args.fast_mode) if args.provider == "codex-native" else None,
        "overload_recovery": OVERLOAD_RECOVERY if args.provider == "codex-native" else None,
        "timeout_recovery": TIMEOUT_RECOVERY if args.provider == "codex-native" else None,
        "arc_transport": ARC_TRANSPORT if args.mode in ("online", "competition") else None,
        "scope": "all_discovered_environments" if args.all else "selected_environment_subset",
        "discovered_games": available,
        "selected_games": selected,
        "limits_per_game": asdict(limits),
        "target_score_percent": 100,
        "verified_benchmark_score_percent": None,
        "cross_game_memory": False,
        "game_source_exposed_to_model": False,
        "contest_submission": False,
        "native_model_decisions": args.provider == "codex-native",
        "source_snapshot": "source/arc_harness",
        "source_sha256": source_sha256,
        "attribution": attribution,
        "dependency_versions": {
            name: importlib.metadata.version(name)
            for name in ("arc-agi", "arcengine", "openai", "numpy", "pillow")
        },
    }
    write_json(directory / "manifest.json", manifest)
    results, scorecard, close_error, evaluation_error = [], None, None, None
    preclose_checkpoint_error = None
    try:
        for game_id in selected:
            print(f"Starting {game_id} · {args.model} · {args.effort}", flush=True)
            provider_class = {
                "codex": CodexProvider,
                "codex-native": AppServerProvider,
                "openai": ResponsesProvider,
            }[args.provider]
            provider = provider_class(args.model, args.effort, **(
                {"config": manifest["native_config"]} if args.provider == "codex-native" else {}
            ))
            try:
                environment = session.make(game_id)
                write_json(directory / "scorecard-session.json", session.scorecard_reference())
                if not results:
                    save_scorecard_snapshot(directory, session, selected, 0)
            except Exception:
                if attribution:
                    try:
                        write_json(directory / "scorecard-session.json", session.scorecard_reference())
                    except Exception:
                        # Preserve the original error if this extra checkpoint fails.
                        pass
                provider.close()
                raise
            safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", game_id)
            game_dir = directory / safe_name
            result = Runner(
                environment,
                provider,
                game_dir,
                limits,
                game_id,
                progress=lambda message: print(message, flush=True),
            ).run()
            results.append(result)
            render_replay(game_dir)
            write_json(directory / "results.json", results)
            save_scorecard_snapshot(directory, session, selected, len(results))
            if result["status"] in ("interrupted", "error"):
                break
    except KeyboardInterrupt:
        evaluation_error = "Interrupted before the next game could complete"
    except Exception as exc:
        evaluation_error = f"{type(exc).__name__}: {exc}"
    finally:
        # Save an authoritative read before closure can invalidate the card.
        # This stays separate from a successfully closed official scorecard.
        # Avoid implicitly opening an empty card if no game could be created.
        try:
            if session.scorecard_reference()["card_id"] is not None:
                save_scorecard_snapshot(directory, session, selected, len(results), before_close=True)
        except Exception as exc:
            # Still attempt closure if writing the checkpoint fails.
            preclose_checkpoint_error = type(exc).__name__
        try:
            scorecard = session.close()
        except Exception as exc:
            close_error = f"{type(exc).__name__}: {exc}"
        try:
            declared_score = selected_set_score(scorecard, selected)
        except (KeyError, ValueError, TypeError) as exc:
            declared_score = None
            close_error = f"Scorecard validation failed: {exc}"
        write_json(directory / "scorecard.json", {"sdk_scorecard": scorecard, "close_error": close_error})
        summary = {
            "scope": manifest["scope"],
            "games_selected": len(selected),
            "games_run": len(results),
            "games_won": sum(r["won"] for r in results),
            "unrun_games": selected[len(results) :],
            "actions_submitted": sum(r["actions_submitted"] for r in results),
            "reported_tokens": sum(r["input_tokens"] + r["output_tokens"] for r in results),
            "sdk_scorecard_score": scorecard.get("score") if scorecard else None,
            "selected_set_score_percent": declared_score,
            "complete_selected_set": len(results) == len(selected)
            and not any(r["status"] in ("error", "interrupted") for r in results),
            "verified_benchmark_score_percent": None,
            "target_score_percent": 100,
            "note": "SDK scorecard covers its stated environment set. This is not a verified private-set benchmark result.",
            "scorecard_error": close_error,
            "evaluation_error": evaluation_error,
            "preclose_checkpoint_error": preclose_checkpoint_error,
            "directory": str(directory),
        }
        write_json(directory / "summary.json", summary)
        if args.provider == "codex-native":
            from .audit import export_run

            try:
                export_run(directory, directory / "exports")
            except Exception as exc:
                write_json(directory / "export-error.json", {"type": type(exc).__name__, "message": str(exc)})
    print(json.dumps(summary, indent=2))
    return 1 if (
        close_error or evaluation_error or preclose_checkpoint_error
        or any(r["status"] == "error" for r in results)
    ) else 0


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            doctor()
        elif args.command == "games":
            session = ArcadeSession(args.mode, args.environments_dir)
            print(json.dumps(session.games(), indent=2))
        elif args.command == "run":
            return_code = evaluate(args)
            if return_code:
                raise SystemExit(return_code)
        elif args.command == "demo":
            from .fixtures import CorridorFixture, demo_provider

            directory = new_directory(args.output)
            result = Runner(
                CorridorFixture(),
                demo_provider(),
                directory,
                Limits(),
                game_id="SYNTHETIC-integration-fixture",
                progress=print,
            ).run()
            print(json.dumps(result, indent=2))
            print(f"Replay: {render_replay(directory)}")
        elif args.command == "replay":
            print(render_replay(args.directory.resolve()))
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
