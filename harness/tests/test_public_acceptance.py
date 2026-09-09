import copy
import json
from decimal import Decimal

import pytest

from arc_harness.api_run import ROOT, evaluate, load_plan
from arc_harness.public_acceptance import PUBLIC_GAMES, exact_hundred, public_score_gate


@pytest.fixture
def evidence():
    source = "a" * 64
    run = "synthetic-acceptance-fixture"
    card = {"score": 100.0, "competition_mode": True, "card_id": "synthetic-card",
            "total_environments": 25, "total_environments_completed": 25,
            "total_levels": 183, "total_levels_completed": 183,
            "opaque": {"run_id": run, "source_sha256": source, "model": "gpt-6-astra",
                "effort": "high", "provider": "openai-responses", "authentication": "openai_api_key",
                "mode": "competition", "evaluation_scope": "public-repeat", "fast_mode": False,
                "harness_name": "OY1 AGI", "team_name": "OY Labs"}, "environments": []}
    results = []
    for index, game in enumerate(PUBLIC_GAMES):
        levels = 8 if index < 8 else 7
        actions = 4 * levels
        card["environments"].append({"id": game, "score": 100.0, "completed": True,
            "level_count": levels, "levels_completed": levels, "actions": actions,
            "runs": [{"score": 100.0, "completed": True, "state": "WIN",
                      "levels_completed": levels, "actions": actions}]})
        results.append({"game_id": game, "won": True, "levels_completed": levels,
                        "actions_submitted": actions})
    card["total_actions"] = sum(r["actions_submitted"] for r in results)
    return {"card": card, "results": results, "selected": list(PUBLIC_GAMES),
            "run_id": run, "source_sha256": source, "fixture": False}


def test_well_formed_score_gate_is_not_full_compliance(evidence):
    report = public_score_gate(**evidence)
    assert report["passed"]
    assert report["full_submission_compliance_established"] is False
    assert report["verified_by_arc_prize"] is False


@pytest.mark.parametrize("score", [99.999, Decimal("99.999999999999999999999"),
                                    "100.0", True, None, float("nan"), float("inf"), 101])
def test_raw_hundred_never_uses_display_rounding(evidence, score):
    evidence["card"]["score"] = score
    assert not public_score_gate(**evidence)["passed"]


def test_decimal_read_preserves_below_hundred():
    raw = json.loads('{"score": 99.9999999999999999999999}', parse_float=Decimal)
    assert not exact_hundred(raw["score"])


@pytest.mark.parametrize("mutation", [
    lambda e: e.update(fixture=True),
    lambda e: e["selected"].reverse(),
    lambda e: e["results"].reverse(),
    lambda e: e["results"].pop(),
    lambda e: e["results"][0].update(won=False),
    lambda e: e["card"].update(competition_mode=False),
    lambda e: e["card"].update(total_levels_completed=182),
    lambda e: e["card"].update(total_actions=1),
    lambda e: e["card"].pop("card_id"),
    lambda e: e["card"]["opaque"].update(authentication="chatgpt_subscription"),
    lambda e: e["card"]["opaque"].update(run_id="different-attempt"),
    lambda e: e["card"]["opaque"].update(source_sha256="b" * 64),
    lambda e: e["card"]["opaque"].update(fast_mode=True),
    lambda e: e["card"]["environments"].pop(),
    lambda e: e["card"]["environments"].append(copy.deepcopy(e["card"]["environments"][0])),
    lambda e: e["card"]["environments"][0].update(id="different-version"),
    lambda e: e["card"]["environments"][0].update(score=99.999),
    lambda e: e["card"]["environments"][0]["runs"].append(copy.deepcopy(e["card"]["environments"][0]["runs"][0])),
    lambda e: e["card"]["environments"][0]["runs"].clear(),
    lambda e: e["card"]["environments"][0]["runs"][0].update(actions=1),
    lambda e: e["card"]["environments"][0]["runs"][0].update(state="GAME_OVER"),
])
def test_corrupted_or_inapplicable_evidence_fails(evidence, mutation):
    mutation(evidence)
    report = public_score_gate(**evidence)
    assert not report["passed"]
    assert report["status"] == "TARGET NOT MET"


def test_missing_card_does_not_pass(evidence):
    evidence["card"] = None
    assert not public_score_gate(**evidence)["passed"]


def test_full_fixture_completion_cannot_succeed_as_public_100(tmp_path):
    plan, games, dataset_sha = load_plan(ROOT / "plans/public-repeat.json")
    code, directory, summary = evaluate(plan, games, dataset_sha, tmp_path, fixture=True)
    assert summary["complete_selected_set"] is True
    assert summary["games_won"] == 25
    assert code == summary["exit_code"] == 1
    assert summary["public_100_status"] == "TARGET NOT MET"
    report = json.loads((directory / "public-score-acceptance.json").read_text())
    assert report["checks"]["live_attempt"] is False
    assert report["checks"]["raw_official_score_exact_100"] is False
