import copy
import importlib.util

import pytest

from arc_harness.api_run import ROOT
from arc_harness.scoring import selected_set_score

spec = importlib.util.spec_from_file_location("catalog_checker", ROOT / "scripts/independent_audit.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def card():
    return {"environments": [
        {"id": "selected", "score": 100, "runs": [{}]},
        {"id": "unplayed", "score": 0, "actions": 0, "resets": 0,
         "levels_completed": 0, "completed": False, "level_count": 2,
         "runs": [{"score": 0, "actions": 0, "resets": 0, "levels_completed": 0,
                   "completed": False, "state": "NOT_FINISHED", "level_actions": [0, 0],
                   "level_scores": [0.0, 0.0]}]}]}


def test_only_pilot_may_accept_arc_unplayed_catalog_entries():
    c = card()
    assert selected_set_score(c, ["selected"], allow_unplayed=True) == 100
    assert checker.selected_catalog(c, ["selected"], "pilot")
    with pytest.raises(ValueError):
        selected_set_score(c, ["selected"])
    assert not checker.selected_catalog(c, ["selected"], "public-repeat")


@pytest.mark.parametrize("mutation", [
    lambda e: e.update(actions=1),
    lambda e: e.update(resets=1),
    lambda e: e.update(score=0.01),
    lambda e: e.update(completed=True),
    lambda e: e.update(actions=False),
    lambda e: e["runs"][0].update(actions=1),
    lambda e: e["runs"][0].update(state="GAME_OVER"),
    lambda e: e["runs"][0].update(level_scores=[0, 1]),
    lambda e: e["runs"][0].update(level_actions=[]),
    lambda e: e["runs"].append(copy.deepcopy(e["runs"][0])),
])
def test_pilot_cannot_hide_any_other_played_or_malformed_entry(mutation):
    c = card()
    mutation(c["environments"][1])
    with pytest.raises(ValueError):
        selected_set_score(c, ["selected"], allow_unplayed=True)
    assert not checker.selected_catalog(c, ["selected"], "pilot")


def test_duplicate_catalog_entry_is_rejected():
    c = card()
    c["environments"].append(copy.deepcopy(c["environments"][1]))
    with pytest.raises(ValueError):
        selected_set_score(c, ["selected"], allow_unplayed=True)
    assert not checker.selected_catalog(c, ["selected"], "pilot")
