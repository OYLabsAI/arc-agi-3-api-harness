"""Strict public score gate, separate from execution and submission compliance.

The CLI reads saved evidence without importing provider code or contacting a service.
Decimal parsing prevents a displayed/rounded 100 from being accepted as a raw 100.
This gate does not replace action/usage, release, cost, runtime or organizer audits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from decimal import Decimal
from pathlib import Path

PUBLIC_GAMES = (
    "ar25-0c556536", "bp35-0a0ad940", "cd82-fb555c5d", "cn04-2fe56bfb", "dc22-fdcac232",
    "ft09-0d8bbf25", "g50t-5849a774", "ka59-38d34dbb", "lf52-271a04aa", "lp85-305b61c3",
    "ls20-9607627b", "m0r0-492f87ba", "r11l-495a7899", "re86-8af5384d", "s5i5-18d95033",
    "sb26-7fbdac44", "sc25-635fd71a", "sk48-d8078629", "sp80-589a99af", "su15-1944f8ab",
    "tn36-ef4dde99", "tr87-cd924810", "tu93-0768757b", "vc33-5430563c", "wa30-ee6fef47",
)


def exact_hundred(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return False
    return math.isfinite(value) and Decimal(str(value)) == Decimal(100)


def integer(value):
    return type(value) is int and value >= 0


def public_score_gate(card, results, selected, *, run_id, source_sha256, fixture):
    checks = {"live_attempt": fixture is False,
              "exact_declared_order": selected == list(PUBLIC_GAMES),
              "source_identity_present": isinstance(source_sha256, str)
              and re.fullmatch(r"[a-f0-9]{64}", source_sha256) is not None,
              "run_identity_present": isinstance(run_id, str) and bool(run_id)}
    card = card if isinstance(card, dict) else {}
    checks["raw_official_score_exact_100"] = exact_hundred(card.get("score"))
    checks["competition_mode"] = card.get("competition_mode") is True
    checks["official_card_identity"] = isinstance(card.get("card_id"), str) and bool(card["card_id"])
    checks["official_totals"] = all(type(card.get(k)) is int and card[k] == v for k, v in {
        "total_environments": 25, "total_environments_completed": 25,
        "total_levels": 183, "total_levels_completed": 183}.items())
    opaque = card.get("opaque")
    expected = {"run_id": run_id, "source_sha256": source_sha256, "model": "gpt-6-astra",
                "effort": "high", "provider": "openai-responses", "authentication": "openai_api_key",
                "mode": "competition", "evaluation_scope": "public-repeat",
                "harness_name": "OY1 AGI", "team_name": "OY Labs"}
    checks["api_attempt_attribution"] = isinstance(opaque, dict) and all(
        opaque.get(k) == v for k, v in expected.items()) and opaque.get("fast_mode") is False
    environments = card.get("environments")
    valid_envs = isinstance(environments, list) and all(isinstance(e, dict) for e in environments)
    ids = [e.get("id") for e in environments] if valid_envs else []
    checks["exact_official_selection"] = len(ids) == 25 and sorted(ids, key=str) == sorted(PUBLIC_GAMES)
    valid_results = isinstance(results, list) and all(isinstance(r, dict) for r in results)
    checks["exact_result_order"] = valid_results and [r.get("game_id") for r in results] == list(PUBLIC_GAMES)
    checks["all_25_wins"] = valid_results and len(results) == 25 and all(r.get("won") is True for r in results)
    checks["all_183_local_levels"] = valid_results and all(integer(r.get("levels_completed")) for r in results)
    if checks["all_183_local_levels"]:
        checks["all_183_local_levels"] = sum(r["levels_completed"] for r in results) == 183
    games = []
    if checks["exact_official_selection"] and checks["exact_result_order"]:
        by_id = {e["id"]: e for e in environments}
        for result in results:
            game = by_id[result["game_id"]]
            plays = game.get("runs")
            single = isinstance(plays, list) and len(plays) == 1 and isinstance(plays[0], dict)
            play = plays[0] if single else {}
            rc = {"one_official_run": single, "game_raw_100": exact_hundred(game.get("score")),
                  "run_raw_100": exact_hundred(play.get("score")),
                  "official_win": game.get("completed") is True and play.get("completed") is True
                  and play.get("state") == "WIN",
                  "levels_reconcile": all(integer(v) for v in (game.get("level_count"),
                  game.get("levels_completed"), play.get("levels_completed"), result.get("levels_completed")))
                  and game["level_count"] > 0
                  and game["level_count"] == game.get("levels_completed") == play.get("levels_completed")
                  == result.get("levels_completed"),
                  "actions_reconcile": all(integer(v) for v in (result.get("actions_submitted"),
                  game.get("actions"), play.get("actions")))
                  and result["actions_submitted"] == game.get("actions") == play.get("actions")}
            games.append({"game_id": result["game_id"], "checks": rc, "passed": all(rc.values())})
        checks["all_official_levels"] = sum(e["levels_completed"] for e in environments
                                             if integer(e.get("levels_completed"))) == 183
        checks["total_actions_reconcile"] = integer(card.get("total_actions")) and all(
            integer(r.get("actions_submitted")) for r in results) and card["total_actions"] == sum(
                r["actions_submitted"] for r in results)
    else:
        checks["all_official_levels"] = checks["total_actions_reconcile"] = False
    checks["all_game_checks"] = len(games) == 25 and all(g["passed"] for g in games)
    passed = all(checks.values())
    return {"passed": passed, "status": "PUBLIC SCORE GATE PASSED" if passed else "TARGET NOT MET",
            "checks": checks, "games": games, "scope": "exact public API score and result consistency",
            "full_submission_compliance_established": False, "verified_by_arc_prize": False,
            "remaining_acceptance": "Independent action/usage, full release, runtime/cost and submission gates"}


def main():
    parser = argparse.ArgumentParser(description="Read-only raw 100 public API score acceptance")
    parser.add_argument("run", type=Path)
    parser.add_argument("--expected-source-sha256", required=True)
    args = parser.parse_args()
    try:
        def read(name):
            return json.loads((args.run / name).read_text(), parse_float=Decimal,
                              parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))

        manifest, summary, raw, results = (read(name) for name in
                                          ("manifest.json", "summary.json", "scorecard.json", "results.json"))
        report = public_score_gate(raw.get("sdk_scorecard"), results, manifest.get("selected_games"),
                                   run_id=summary.get("run_id"), source_sha256=args.expected_source_sha256,
                                   fixture=manifest.get("fixture"))
        source = args.run / "source/arc_harness"
        actual = hashlib.sha256(b"".join(p.name.encode() + p.read_bytes() for p in sorted(source.glob("*.py")))).hexdigest()
        extra = {"source_matches_expected": manifest.get("source_sha256") == actual == args.expected_source_sha256,
                 "full_public_scope": manifest.get("scope") == summary.get("scope") == "public-repeat",
                 "clean_completion": summary.get("complete_selected_set") is True
                 and summary.get("evaluation_error") is None and raw.get("close_error") is None,
                 "summary_raw_100": exact_hundred(summary.get("selected_set_score_percent"))}
        report["checks"].update(extra)
        report["passed"] = report["passed"] and all(extra.values())
        if not report["passed"]:
            report["status"] = "TARGET NOT MET"
    except Exception as exc:
        report = {"passed": False, "status": "TARGET NOT MET", "error_type": type(exc).__name__,
                  "reason": "Required evidence is missing or invalid; no score accepted"}
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
