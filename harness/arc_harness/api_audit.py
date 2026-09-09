"""Exports and consistency audit for API attempts, including incomplete evaluations."""

from __future__ import annotations

import json
from pathlib import Path

from .audit import level_rows, write_exports
from .scoring import selected_environments
from .store import write_json


def export_api_run(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    results = json.loads((root / "results.json").read_text())
    cost = json.loads((root / "cost-report.json").read_text())
    summary = json.loads((root / "summary.json").read_text())
    card = json.loads((root / "scorecard.json").read_text()).get("sdk_scorecard")
    selected = manifest["selected_games"]
    official = {e["id"]: e for e in card.get("environments", [])} if card else {}
    try:
        selected_card = selected_environments(card, selected, allow_unplayed=manifest["scope"] == "pilot") if card else {}
        official_selection = set(selected_card) == set(selected) if card else manifest["fixture"]
    except (ValueError, KeyError, TypeError):
        official_selection = False
    checks = {"selected_order_preserved": [r["game_id"] for r in results] == selected[:len(results)],
              "unrun_denominator_preserved": summary["unrun_games"] == selected[len(results):],
              "cost_within_cap": cost["charged_or_reserved_usd"] <= cost["approved_usd"],
              "no_unresolved_usage": cost["uncertain_requests"] == 0,
              "all_operation_costs_known": manifest["fixture"] or cost.get("cost_coverage_complete") is True,
              "all_games_evaluated": bool(summary["complete_selected_set"]),
              "official_selected_set": official_selection}
    rows, actions, levels, all_tickets, all_counts, errors = [], [], [], [], [], []
    for result in results:
        game = result["game_id"]
        events = [json.loads(line) for line in (root / game / "events.jsonl").read_text().splitlines()]
        by_kind = {}
        for event in events:
            by_kind.setdefault(event["kind"], []).append(event["data"])
        submissions = by_kind.get("action_submitted", [])
        transitions = by_kind.get("transition", [])
        observations = by_kind.get("observation", [])
        calls = [i for e in by_kind.get("api_response_items", []) if not e["compact"]
                 for i in e["output"] if i.get("type") == "function_call"]
        outputs = by_kind.get("api_tool_result", [])
        tickets = by_kind.get("api_request_completed", [])
        all_tickets.extend(t["ledger_request"] for t in tickets)
        all_counts.extend(by_kind.get("api_input_count", []))
        baselines = None
        remote_checks = True
        if game in official:
            entry = official[game]
            plays = entry.get("runs", [])
            remote_checks = len(plays) == 1 and entry["actions"] == result["actions_submitted"]
            remote_checks = remote_checks and entry["levels_completed"] == result["levels_completed"]
            if len(plays) == 1:
                baselines = plays[0]["level_baseline_actions"]
        rc = {"action_submissions": [x["number"] for x in submissions] == list(range(1, len(submissions) + 1)),
              "action_count": len(submissions) == result["actions_submitted"],
              "no_ambiguous_action": len(submissions) == len(transitions),
              "observation_chain": len(observations) == len(transitions) + 1,
              "transition_links": all(t["before"] == observations[i]["state_hash"] and
                                       t["after"] == observations[i + 1]["state_hash"]
                                       for i, t in enumerate(transitions)),
              "tool_pairs": [c["call_id"] for c in calls] == [o["call_id"] for o in outputs],
              "unique_call_ids": len(calls) == len({c["call_id"] for c in calls}),
              "input_usage": sum(t["usage"]["input_tokens"] for t in tickets) == result["input_tokens"],
              "output_usage": sum(t["usage"]["output_tokens"] for t in tickets) == result["output_tokens"],
              "remote_result": remote_checks}
        game_levels = level_rows(events, game, baselines)
        levels.extend(game_levels)
        actions.extend({"game_id": game, "number": a["number"], "action": a["action"]["name"],
                        "before": a["before"]} for a in submissions)
        errors.extend({"game_id": game, **e} for e in by_kind.get("error", []))
        rows.append({"game_id": game, "checks": rc, "passed": all(rc.values()),
                     "levels": result["levels_completed"], "won": result["won"]})
    accounted = [r["id"] for r in cost["requests"] if r["status"] == "accounted"]
    checks["ledger_request_pairing"] = accounted == all_tickets
    counts = cost.get("input_count_operations", [])
    checks["counting_operation_pairing"] = len(counts) == len(all_counts) and all(
        saved["status"] == "recorded" and saved["id"] == event.get("ledger_count")
        and all(saved.get(k) == event.get(k) for k in ("compact", "input_tokens", "request_id", "object"))
        for saved, event in zip(counts, all_counts, strict=False))
    export = root / "exports"
    export.mkdir(exist_ok=True)
    write_exports(export, "actions", actions)
    write_exports(export, "levels", levels)
    write_exports(export, "games", results)
    write_json(export / "requests.json", cost["requests"])
    write_json(export / "errors.json", errors)
    audit = {"checks": checks, "games": rows, "passed": all(checks.values()) and all(r["passed"] for r in rows),
             "fixture": manifest["fixture"], "verified_by_arc_prize": False}
    write_json(export / "audit.json", audit)
    return audit
