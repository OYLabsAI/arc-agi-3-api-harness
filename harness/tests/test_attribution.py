import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
from test_sdk_session import make_sdk

from arc_harness.attribution import NamedArcadeSession, attribution_for
from arc_harness.cli import evaluate, parser
from arc_harness.environment import TransportRemoteEnvironment


def args(*extra):
    return parser().parse_args([
        "run", "--games", "game-a", "--provider", "codex-native", "--mode", "competition",
        "--harness-name", "OY1 AGI", "--team-name", "OY Labs", *extra,
    ])


def test_key_required_before_named_run_has_side_effects(monkeypatch, tmp_path):
    monkeypatch.delenv("ARC_API_KEY", raising=False)
    session = Mock()
    monkeypatch.setattr("arc_harness.cli.NamedArcadeSession", session)
    with pytest.raises(ValueError, match="ARC_API_KEY"):
        evaluate(args("--output", str(tmp_path / "runs")))
    session.assert_not_called()
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("extra", [
    ["--provider", "openai"], ["--provider", "codex"],
    ["--mode", "offline"], ["--mode", "online"], ["--team-name", ""],
])
def test_named_configuration_fails_closed(monkeypatch, extra):
    monkeypatch.setenv("ARC_API_KEY", "test-secret")
    with pytest.raises(ValueError):
        attribution_for(args(*extra), "source-digest", "run-id")


def test_unnamed_mode_retains_existing_behavior(monkeypatch):
    monkeypatch.delenv("ARC_API_KEY", raising=False)
    original = parser().parse_args(["run", "--games", "game-a"])
    assert attribution_for(original, "source-digest", "run-id") is None


def test_real_sdk_named_competition_lifecycle_preserves_transport(monkeypatch):
    import arc_agi.base

    monkeypatch.setenv("ARC_API_KEY", "test-secret")
    identity = attribution_for(args(), "source-digest", "run-id")
    assert "test-secret" not in json.dumps(identity)
    assert identity["fast_mode"] is False
    sdk = make_sdk(monkeypatch)
    sdk.operation_mode = arc_agi.OperationMode.COMPETITION
    session = NamedArcadeSession("competition", "unused", "unused", attribution=identity)
    calls = []

    def respond(url, **kwargs):
        calls.append((url, kwargs))
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({
            "card_id": "named-card", "score": 0, "api_key": "test-secret",
        }).encode()
        return response

    original = arc_agi.base.RemoteEnvironmentWrapper

    def make(game_id, **kwargs):
        assert arc_agi.base.RemoteEnvironmentWrapper is TransportRemoteEnvironment
        return SimpleNamespace()

    monkeypatch.setattr(sdk._session, "post", respond)
    monkeypatch.setattr(sdk._session, "get", Mock(side_effect=AssertionError("No inflight reads")))
    monkeypatch.setattr(sdk, "make", Mock(side_effect=make))
    session.make("game-a")
    session.make("game-b")
    assert arc_agi.base.RemoteEnvironmentWrapper is original
    assert session.snapshot() is None
    closed = session.close()
    assert closed["card_id"] == "named-card"
    assert "test-secret" not in json.dumps(closed)
    assert session.scorecard_reference()["card_id"] == "named-card"
    assert sdk._default_scorecard_id == "existing-card"
    assert [c[0] for c in calls] == [
        "https://example.invalid/api/scorecard/open",
        "https://example.invalid/api/scorecard/close",
    ]
    assert calls[0][1]["json"] == {
        "tags": ["OY1 AGI", "OY Labs", "public", "codex-native"],
        "opaque": identity,
        "competition_mode": True,
    }
    assert calls[-1][1]["json"]["card_id"] == "named-card"
    for call in sdk.make.call_args_list:
        assert call.kwargs == {"scorecard_id": "named-card"}
    with pytest.raises(ValueError, match="only be started once"):
        session.make("game-a")
    assert sdk.make.call_count == 2


def test_failed_first_game_preserves_named_card_without_repeating_reset(monkeypatch):
    sdk = make_sdk(monkeypatch)
    session = NamedArcadeSession("competition", "unused", "unused", attribution={
        "harness_name": "OY1 AGI", "team_name": "OY Labs",
    })
    sdk.create_scorecard = Mock(return_value="named-card")
    sdk.make = Mock(side_effect=TimeoutError("uncertain action"))
    sdk.close_scorecard = Mock(return_value=None)
    assert session.close() is None
    sdk.close_scorecard.assert_not_called()
    with pytest.raises(TimeoutError):
        session.make("game-a")
    assert session.scorecard_reference()["card_id"] == "named-card"
    with pytest.raises(ValueError):
        session.make("game-a")
    assert sdk.create_scorecard.call_count == sdk.make.call_count == 1
    session.close()
    sdk.close_scorecard.assert_called_once_with("named-card")


def test_uncertain_card_creation_is_never_retried_for_another_game(monkeypatch):
    sdk = make_sdk(monkeypatch)
    session = NamedArcadeSession("competition", "unused", "unused", attribution={
        "harness_name": "OY1 AGI", "team_name": "OY Labs",
    })
    sdk.create_scorecard = Mock(side_effect=TimeoutError("uncertain card creation"))
    sdk.make = Mock()
    sdk.close_scorecard = Mock()
    with pytest.raises(TimeoutError):
        session.make("game-a")
    with pytest.raises(RuntimeError, match="no retry"):
        session.make("game-b")
    assert session.close() is None
    assert session.scorecard_reference()["card_id"] is None
    sdk.create_scorecard.assert_called_once()
    sdk.make.assert_not_called()
    sdk.close_scorecard.assert_not_called()


def test_cli_checkpoints_card_id_when_first_game_creation_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_API_KEY", "test-secret")
    session = Mock(
        mode="competition",
        games=Mock(return_value=["game-a"]),
        make=Mock(side_effect=TimeoutError("uncertain first RESET")),
        scorecard_reference=Mock(return_value={"card_id": "named-card", "mode": "competition"}),
        close=Mock(return_value=None),
    )
    provider = Mock()
    monkeypatch.setattr("arc_harness.cli.NamedArcadeSession", Mock(return_value=session))
    monkeypatch.setattr("arc_harness.cli.AppServerProvider", Mock(return_value=provider))
    monkeypatch.setattr("arc_harness.cli.isolated_config", lambda *args: {})
    assert evaluate(args("--output", str(tmp_path))) == 1
    run = next(tmp_path.iterdir())
    assert json.loads((run / "scorecard-session.json").read_text())["card_id"] == "named-card"
    manifest = json.loads((run / "manifest.json").read_text())
    assert manifest["attribution"]["source_sha256"] == manifest["source_sha256"]
    assert manifest["attribution"]["harness_name"] == "OY1 AGI"
    assert "test-secret" not in (run / "manifest.json").read_text()
    session.make.assert_called_once_with("game-a")
    session.close.assert_called_once()
    session.snapshot.assert_not_called()
    provider.close.assert_called_once()
