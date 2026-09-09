"""Read-only standard-library auditor. Never import or execute candidate modules."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from decimal import Decimal
from pathlib import Path, PurePosixPath


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    return json.loads(
        raw,
        object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")),
    )


def read(path):
    return decode(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe(root, name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or ".." in p.parts or p.as_posix() != name or "\\" in name:
        raise ValueError("Unsafe evidence path")
    path = root / name
    if any(parent.is_symlink() for parent in [path, *path.parents] if parent != root.parent):
        raise ValueError("Symlink in evidence path")
    return path


def inventory(root, entries):
    seen = set()
    for e in entries:
        if e["path"] in seen:
            raise ValueError("Duplicate inventory path")
        seen.add(e["path"])
        p = safe(root, e["path"])
        if not p.is_file() or p.stat().st_size != e["bytes"] or sha(p) != e["sha256"]:
            raise ValueError("Evidence content differs from pinned inventory")
    return seen


def natural(n):
    return type(n) is int and n >= 0


def selected_catalog(card, selected, scope):
    entries = card["environments"]
    if len({e["id"] for e in entries}) != len(entries):
        return False
    if not set(selected).issubset({e["id"] for e in entries}):
        return False
    for e in entries:
        if e["id"] in selected:
            continue
        if scope != "pilot" or len(e.get("runs", [])) != 1:
            return False
        r = e["runs"][0]
        if e.get("completed") is not False or r.get("completed") is not False:
            return False
        if r.get("state") != "NOT_FINISHED":
            return False
        for obj in (e, r):
            for k in ("actions", "resets", "levels_completed", "score"):
                if type(obj.get(k)) not in (int, float) or obj[k] != 0:
                    return False
        if not natural(e.get("level_count")) or e["level_count"] == 0:
            return False
        for field in ("level_actions", "level_scores"):
            if not isinstance(r.get(field), list) or len(r[field]) != e["level_count"]:
                return False
            if any(type(v) not in (int, float) or v != 0 for v in r[field]):
                return False
    return True


def observed_hash(obs):
    frames = obs["frames"]
    if not frames or obs["animation_frames"] != len(frames):
        raise ValueError("Invalid observation frames")
    for grid in frames:
        if not grid or not 0 < len(grid) <= 64 or not 0 < len(grid[0]) <= 64:
            raise ValueError("Invalid observed shape")
        if any(len(row) != len(grid[0]) or any(not natural(x) or x > 15 for x in row) for row in grid):
            raise ValueError("Invalid observed pixels")
    grid = frames[-1]
    header = json.dumps(
        [
            [len(grid), len(grid[0])],
            obs["state"],
            obs["levels_completed"],
            obs["win_levels"],
            obs["available_actions"],
        ]
    ).encode()
    return hashlib.sha256(header + bytes(x for row in grid for x in row)).hexdigest()


def normalized_action(a):
    default = {"x": None, "y": None, "expected_pixels": [], "expected_state": None, "expected_levels": None}
    result = {**default, **a}
    if result.get("name") not in ["RESET", *[f"ACTION{i}" for i in range(1, 8)]]:
        raise ValueError("Invalid action name")
    if result["name"] == "ACTION6":
        if any(not natural(result[k]) or result[k] > 63 for k in ("x", "y")):
            raise ValueError("Invalid click")
    elif result["x"] is not None or result["y"] is not None:
        raise ValueError("Coordinates on non-click")
    return result


def cost(usage):
    i, o = usage["input_tokens"], usage["output_tokens"]
    if not natural(i) or not natural(o) or usage["total_tokens"] != i + o:
        raise ValueError("Usage totals do not reconcile")
    details = usage.get("input_tokens_details") or {}
    cached, writes = details.get("cached_tokens"), details.get("cache_write_tokens")
    reasoning = (usage.get("output_tokens_details") or {}).get("reasoning_tokens")
    if reasoning is not None and (not natural(reasoning) or reasoning > o):
        raise ValueError("Invalid reasoning subset")
    if cached is not None and (not natural(cached) or cached > i):
        raise ValueError("Invalid cache subset")
    if writes is not None and (not natural(writes) or writes > i - (cached or 0)):
        raise ValueError("Invalid cache-write subset")
    rate = Decimal(2) if i > 272000 else Decimal(1)
    if cached is None or writes is None:
        tokens = Decimal(i) * Decimal("12.5")
        estimate = None
    else:
        tokens = (i - cached - writes) * Decimal(10) + cached + writes * Decimal("12.5")
        estimate = True
    amount = int((tokens * rate + o * (75 if i > 272000 else 50)).to_integral_value(rounding="ROUND_CEILING"))
    return amount if estimate else None, amount


def audit_run(root, expected_release, expected_evidence, *, require_complete=True):
    root = Path(root).resolve()
    checks, failures = {}, []

    def check(name, condition):
        checks[name] = bool(condition)
        if not condition:
            failures.append(name)

    try:
        check("externally_pinned_evidence", sha(root / "evidence-manifest.json") == expected_evidence)
        if not checks["externally_pinned_evidence"]:
            raise ValueError("Evidence identity mismatch")
        names = inventory(root, read(root / "evidence-manifest.json")["files"])
        required = {
            "manifest.json",
            "summary.json",
            "results.json",
            "cost-report.json",
            "cost-ledger.sqlite",
            "scorecard.json",
            "source/RELEASE-MANIFEST.json",
        }
        check("required_files_pinned", required <= names)
        release_path = root / "source/RELEASE-MANIFEST.json"
        check("externally_pinned_release", sha(release_path) == expected_release)
        release = read(release_path)
        source_names = inventory(root / "source", release["files"])
        actual_source = {p.relative_to(root / "source").as_posix() for p in (root / "source").rglob("*")
                         if p.is_file() and not any(part in {"__pycache__", ".pytest_cache", ".ruff_cache"}
                                                   for part in p.relative_to(root / "source").parts)}
        check("exact_source_inventory", actual_source == source_names | {"RELEASE-MANIFEST.json"})
        check("source_files_in_evidence", all("source/" + n in names for n in source_names))
        manifest, summary, results, report = [
            read(root / n) for n in ("manifest.json", "summary.json", "results.json", "cost-report.json")
        ]
        selected = manifest["selected_games"]
        check(
            "safe_unique_selection",
            bool(selected)
            and len(selected) == len(set(selected))
            and all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,100}", g) for g in selected),
        )
        if not checks["safe_unique_selection"]:
            raise ValueError("Unsafe selection")
        check("release_attribution", manifest["release_manifest_sha256"] == expected_release)
        solver_digest = hashlib.sha256(b"".join(p.name.encode() + p.read_bytes()
            for p in sorted((root / "source/arc_harness").glob("*.py")))).hexdigest()
        check("solver_source_attribution", manifest["source_sha256"] == solver_digest)
        check("run_identity", summary["run_id"] == root.name)
        check("selected_order", [r["game_id"] for r in results] == selected[: len(results)])
        check("unrun_denominator", summary["unrun_games"] == selected[len(results) :])
        check("no_counting_endpoint", report.get("input_count_operations") == [])
        check("all_operation_costs_covered", report.get("cost_coverage_complete") is True)
        with sqlite3.connect((root / "cost-ledger.sqlite").as_uri() + "?mode=ro&immutable=1", uri=True) as db:
            raw_rows = db.execute(
                "SELECT id,kind,reserved,charge,status,detail FROM requests ORDER BY id"
            ).fetchall()
            check("no_count_dispatch", db.execute("SELECT COUNT(*) FROM input_counts").fetchone()[0] == 0)
        db_rows = [
            {
                "id": i,
                "kind": kind,
                "reservation_micro_usd": reserve,
                "charge_micro_usd": charge,
                "status": status,
                **decode(detail),
            }
            for i, kind, reserve, charge, status, detail in raw_rows
        ]
        check("ledger_matches_export", db_rows == report["requests"])
        ledger = {r["id"]: r for r in db_rows}
        totals, ticket_ids, call_ids = [0, 0], [], set()
        for r in db_rows:
            label = f"request_{r['id']}"
            check(label + "_accounted", r["status"] == "accounted")
            if r["status"] != "accounted":
                continue
            estimate, amount = cost(r["usage"])
            check(label + "_cost", r["charge_micro_usd"] == amount and r["estimated_micro_usd"] == estimate)
            check(
                label + "_reservation",
                r["input_bound"] == 922000
                and r["output_bound"] == (20000 if r["kind"] == "compaction" else 16000)
                and r["reservation_micro_usd"] == r["input_bound"] * 25 + r["output_bound"] * 75
                and r["usage"]["input_tokens"] <= r["input_bound"]
                and r["usage"]["output_tokens"] <= r["output_bound"]
                and amount <= r["reservation_micro_usd"],
            )
            check(
                label + "_settings",
                r["effective_model"] == "gpt-6-astra"
                and r["effective_effort"] == "high"
                and (manifest["version"] == "0.3.6+api7" or r.get("reasoning_context") == "all_turns")
                and r["service_tier"] == "default"
                and r["response_status"] == "completed",
            )
        for result in results:
            game = result["game_id"]
            events_path = safe(root, game + "/events.jsonl")
            check(
                game + "_events_pinned",
                game + "/events.jsonl" in names and game + "/evidence.sqlite" in names,
            )
            lines = events_path.read_text().splitlines()
            events = [decode(line) for line in lines]
            with sqlite3.connect(
                safe(root, game + "/evidence.sqlite").as_uri() + "?mode=ro&immutable=1", uri=True
            ) as db:
                db_events = [
                    (kind, decode(payload))
                    for kind, payload in db.execute("SELECT kind,payload FROM events ORDER BY id")
                ]
            check(game + "_journals_agree", db_events == [(e["kind"], e) for e in events])
            observations, submissions, transitions, usage_events = [], [], [], []
            pending, current_calls, batch, latest_output = {}, [], [], None
            for event in events:
                kind, data = event["kind"], event["data"]
                if kind == "observation":
                    check(
                        game + "_frame_" + str(len(observations)),
                        data["index"] == len(observations) and data["state_hash"] == observed_hash(data),
                    )
                    observations.append(data)
                elif kind == "api_request_completed":
                    ticket_ids.append(data["ledger_request"])
                    usage_events.append(data)
                    saved = ledger[data["ledger_request"]]
                    check(
                        game + "_usage_" + str(data["ledger_request"]),
                        all(
                            data.get(k) == saved.get(k)
                            for k in (
                                "kind",
                                "usage",
                                "request_id",
                                "response_id",
                                "effective_model",
                                "effective_effort",
                                "service_tier",
                                "response_status",
                            )
                        ),
                    )
                elif kind == "api_response_items":
                    if data["compact"]:
                        check(
                            game + "_compaction_" + str(data["ledger_request"]),
                            bool(data["output"]) and all(i["type"] == "compaction" for i in data["output"]),
                        )
                    else:
                        current_calls = [i for i in data["output"] if i["type"] == "function_call"]
                        for call in current_calls:
                            check(game + "_unique_" + call["call_id"], call["call_id"] not in call_ids)
                            call_ids.add(call["call_id"])
                            pending[call["call_id"]] = call
                elif (
                    kind == "model_reply"
                    and manifest["attribution"]["provider"] == "openai-responses"
                    and db_rows
                ):
                    check(
                        game + "_reply_" + str(data["call"]),
                        data["tools"]
                        == [
                            {"name": c["name"].removeprefix("arc_"), "arguments": decode(c["arguments"])}
                            for c in current_calls
                        ],
                    )
                elif kind == "action_submitted":
                    submissions.append(data)
                    batch.append(data)
                    if db_rows:
                        check(
                            game + "_action_origin_" + str(data["number"]),
                            len(current_calls) == 1
                            and current_calls[0]["name"] == "arc_act"
                            and data["action"]
                            == normalized_action(
                                decode(current_calls[0]["arguments"])["actions"][len(batch) - 1]
                            )
                            and data["experiment"] == decode(current_calls[0]["arguments"])["experiment"],
                        )
                elif kind == "transition":
                    index = len(transitions)
                    transitions.append(data)
                    sub = submissions[index]
                    before, after = observations[index : index + 2]
                    check(
                        game + "_transition_" + str(index),
                        data["index"] == index
                        and sub["number"] == index + 1
                        and sub["before"] == data["before"] == before["state_hash"]
                        and data["after"] == after["state_hash"]
                        and data["action"] == {k: sub["action"][k] for k in ("name", "x", "y")}
                        and data["experiment"] == sub["experiment"]
                        and data["levels_completed"] == after["levels_completed"]
                        and data["state"] == after["state"],
                    )
                elif kind == "tool_result":
                    latest_output = data
                    if not db_rows:
                        batch = []
                elif kind == "api_tool_result":
                    call = pending.pop(data["call_id"])
                    check(
                        game + "_tool_" + data["call_id"], data["tool"] == call["name"].removeprefix("arc_")
                    )
                    if len(current_calls) == 1:
                        check(
                            game + "_tool_result_" + data["call_id"],
                            latest_output == {"tool": data["tool"], "result": data["output"]},
                        )
                        if data["tool"] == "act" and "executed" in data["output"]:
                            check(
                                game + "_batch_" + data["call_id"],
                                data["output"]["executed"] == len(batch)
                                and [t["action"] for t in data["output"]["transitions"]]
                                == [{k: a["action"][k] for k in ("name", "x", "y")} for a in batch],
                            )
                    batch = []
                    latest_output = None
            check(game + "_no_pending_tools", not pending)
            check(
                game + "_action_totals",
                len(submissions) == len(transitions) == result["actions_submitted"]
                and len(observations) == len(transitions) + 1,
            )
            check(
                game + "_final_state",
                observations[-1]["levels_completed"] == result["levels_completed"]
                and (observations[-1]["state"] == "WIN") == result["won"],
            )
            for index, key in enumerate(("input_tokens", "output_tokens")):
                count = sum(e["usage"][key] for e in usage_events)
                totals[index] += count
                check(game + "_" + key, count == result[key])
        check(
            "unique_request_evidence", ticket_ids == [r["id"] for r in db_rows if r["status"] == "accounted"]
        )
        check(
            "all_usage_reconciles",
            totals
            == [
                sum(r["usage"][k] for r in db_rows if r["status"] == "accounted")
                for k in ("input_tokens", "output_tokens")
            ],
        )
        check("summary_tokens", sum(totals) == summary["reported_tokens"])
        check("summary_actions", sum(r["actions_submitted"] for r in results) == summary["actions_submitted"])
        charge = sum(r["charge_micro_usd"] for r in db_rows)
        check("cost_export_total", Decimal(str(report["charged_or_reserved_usd"])) * 1000000 == charge)
        check("within_authorized_cap", charge <= Decimal(str(report["approved_usd"])) * 1000000)
        check(
            "request_limit",
            len(db_rows) == report["dispatched_operations"] <= manifest["plan"]["max_requests"],
        )
        if require_complete:
            check(
                "clean_complete_attempt",
                summary["finalization_status"] == "completed"
                and summary["exit_code"] == 0
                and summary["complete_selected_set"] is True
                and not summary["evaluation_error"],
            )
        if not manifest["fixture"]:
            card = read(root / "scorecard.json")["sdk_scorecard"]
            check("official_selection", selected_catalog(card, selected, manifest["scope"]))
            check(
                "official_attribution",
                all(
                    card["opaque"].get(k) == manifest["attribution"].get(k)
                    for k in (
                        "run_id",
                        "source_sha256",
                        "release_manifest_sha256",
                        "authentication",
                        "model",
                        "effort",
                        "provider",
                    )
                ),
            )
            official = {e["id"]: e for e in card["environments"]}
            for r in results:
                e = official[r["game_id"]]
                plays = e["runs"]
                check(
                    r["game_id"] + "_official",
                    len(plays) == 1
                    and e["actions"] == r["actions_submitted"] == plays[0]["actions"]
                    and e["levels_completed"] == r["levels_completed"] == plays[0]["levels_completed"],
                )
    except Exception as exc:
        checks["evidence_parse_and_reconciliation"] = False
        failures.append("evidence_parse_and_reconciliation:" + type(exc).__name__)
    return {
        "passed": bool(checks) and all(checks.values()),
        "checks": checks,
        "failures": failures,
        "auditor": "standalone standard-library script; no candidate imports or network",
        "expected_release_sha256": expected_release,
        "expected_evidence_sha256": expected_evidence,
        "scope": "saved action/usage/cost/source consistency; external provider truth and organizer approval remain separate",
        "full_submission_compliance_established": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--expected-release-sha256", required=True)
    p.add_argument("--expected-evidence-sha256", required=True)
    p.add_argument("--allow-incomplete", action="store_true")
    a = p.parse_args()
    report = audit_run(
        a.run, a.expected_release_sha256, a.expected_evidence_sha256, require_complete=not a.allow_incomplete
    )
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
