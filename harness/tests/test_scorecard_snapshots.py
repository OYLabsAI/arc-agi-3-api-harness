import json
from types import SimpleNamespace
from unittest.mock import Mock

from arc_harness.cli import save_scorecard_snapshot
from arc_harness.environment import ArcadeSession


def test_score_snapshot_does_not_close_session_and_redacts_credentials(tmp_path):
    raw = {
        "api_key": "test-secret",
        "score": 100,
        "environments": [{"id": "a", "score": 100, "runs": [{}]}],
    }
    session = ArcadeSession.__new__(ArcadeSession)
    session.arc = SimpleNamespace(
        get_scorecard=Mock(return_value=SimpleNamespace(model_dump=lambda **_: raw)),
        close_scorecard=Mock(),
    )
    result = save_scorecard_snapshot(tmp_path, session, ["a", "b"], 1)
    assert result["selected_set_score_percent"] == 50
    assert result["provisional"] is True
    assert result["snapshot_error"] is None
    saved = (tmp_path / "scorecard-partials/001.json").read_text()
    assert "test-secret" not in saved
    assert json.loads(saved) == result
    session.arc.close_scorecard.assert_not_called()


def test_score_snapshot_failure_preserves_attempt_and_does_not_log_response(tmp_path):
    session = SimpleNamespace(snapshot=Mock(side_effect=ValueError("body: test-secret")))
    result = save_scorecard_snapshot(tmp_path, session, ["a"], 1)
    assert result["snapshot_error"] == "ValueError"
    assert result["selected_set_score_percent"] is None
    assert "test-secret" not in (tmp_path / "scorecard-partials/001.json").read_text()


def test_before_close_checkpoint_retains_finished_game_snapshot(tmp_path):
    raw = {"score": 100, "environments": [{"id": "a", "score": 100, "runs": [{}]}]}
    session = SimpleNamespace(snapshot=Mock(return_value=raw))
    save_scorecard_snapshot(tmp_path, session, ["a"], 1)
    ordinary = (tmp_path / "scorecard-partials/001.json").read_bytes()
    result = save_scorecard_snapshot(tmp_path, session, ["a"], 1, before_close=True)
    assert result["before_close"] is True
    assert result["selected_set_score_percent"] == 100
    assert (tmp_path / "scorecard-partials/001.json").read_bytes() == ordinary
    assert json.loads((tmp_path / "scorecard-partials/before-close.json").read_text()) == result


def test_competition_never_reads_inflight_scorecard(tmp_path):
    session = SimpleNamespace(mode="competition", snapshot=Mock())
    result = save_scorecard_snapshot(tmp_path, session, ["a"], 1)
    session.snapshot.assert_not_called()
    assert result["sdk_scorecard"] is None
    assert result["snapshot_error"] is None
    assert "Competition" in result["skipped_reason"]
