import json
import threading
from unittest.mock import Mock

import arc_agi
import pytest
import requests
from arc_agi.models import EnvironmentInfo
from requests.adapters import HTTPAdapter

from arc_harness.environment import (
    ArcadeSession,
    ARCTransportAdapter,
    SDKEnvironment,
    TransportRemoteEnvironment,
)
from arc_harness.types import Action


def make_sdk(monkeypatch):
    """Exercise the installed SDK's real scorecard methods without the network."""
    sdk = arc_agi.Arcade.__new__(arc_agi.Arcade)
    sdk.operation_mode = arc_agi.OperationMode.ONLINE
    sdk.arc_base_url = "https://example.invalid"
    sdk.arc_api_key = "test-secret"
    sdk._default_scorecard_id = "existing-card"
    sdk._lock = threading.Lock()
    sdk._cookie_lock = threading.Lock()
    sdk.logger = Mock()
    sdk._session = requests.Session()
    sdk._session.cookies.set("route", "old-route")
    sdk._master_cookie_jar = requests.cookies.RequestsCookieJar()
    sdk._master_cookie_jar.update(sdk._session.cookies)
    monkeypatch.setattr(arc_agi, "Arcade", lambda **_: sdk)
    return sdk


def test_refreshed_game_cookie_survives_real_sdk_read_and_close(monkeypatch):
    sdk = make_sdk(monkeypatch)
    session = ArcadeSession()
    # A game wrapper shares sdk._session.cookies and receives refreshed routing
    # cookies during gameplay. Reproduce that refresh after session construction.
    sdk._session.cookies.set("route", "fresh-route")
    calls = []

    def respond(url, **kwargs):
        assert sdk._session.cookies.get("route") == "fresh-route"
        assert kwargs["headers"]["X-API-Key"] == "test-secret"
        calls.append(url)
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({"card_id": "existing-card", "score": 0}).encode()
        return response

    monkeypatch.setattr(sdk._session, "get", respond)
    monkeypatch.setattr(sdk._session, "post", respond)
    assert session.snapshot()["card_id"] == "existing-card"
    assert session.close()["card_id"] == "existing-card"
    assert calls == [
        "https://example.invalid/api/scorecard/existing-card",
        "https://example.invalid/api/scorecard/close",
    ]


def test_scorecard_reference_excludes_authentication(monkeypatch):
    make_sdk(monkeypatch)
    reference = ArcadeSession().scorecard_reference()
    assert reference == {
        "card_id": "existing-card",
        "base_url": "https://example.invalid",
        "mode": "online",
    }
    assert "test-secret" not in json.dumps(reference)
    assert "old-route" not in json.dumps(reference)


def test_initial_reset_and_actions_use_long_timeout_without_http_retries(monkeypatch):
    requests_seen = []

    def send(adapter, request, **kwargs):
        assert isinstance(adapter, ARCTransportAdapter)
        assert kwargs["timeout"] == (10, 120)
        assert adapter.max_retries.total == 0
        requests_seen.append(request.url)
        if len(requests_seen) == 2:
            raise requests.exceptions.ReadTimeout("response outcome unknown")
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({
            "game_id": "test-transport", "guid": "test-guid", "frame": [[[0]]],
            "state": "NOT_FINISHED", "levels_completed": 0, "win_levels": 1,
            "action_input": {"id": 0}, "available_actions": [1],
        }).encode()
        return response

    monkeypatch.setattr(HTTPAdapter, "send", send)
    raw_env = TransportRemoteEnvironment(
        base_url="https://example.invalid",
        environment_info=EnvironmentInfo(game_id="test-transport", title="test"),
        arc_api_key="test-secret", logger=Mock(), scorecard_id="test-card",
    )
    env = SDKEnvironment(raw_env)
    assert env.initial().levels_completed == 0
    with pytest.raises(RuntimeError, match="uncertain"):
        env.step(Action(name="ACTION1"), "test")
    assert requests_seen == [
        "https://example.invalid/api/cmd/RESET",
        "https://example.invalid/api/cmd/ACTION1",
    ]


def test_missing_initial_observation_does_not_repeat_reset():
    raw_env = Mock(observation_space=None)
    with pytest.raises(RuntimeError, match="Initial RESET outcome is uncertain"):
        SDKEnvironment(raw_env).initial()
    raw_env.reset.assert_not_called()


def test_wrapper_override_is_scoped_and_same_for_every_environment(monkeypatch):
    import arc_agi.base

    sdk = make_sdk(monkeypatch)
    original = arc_agi.base.RemoteEnvironmentWrapper
    wrappers = []

    def make(game_id):
        wrappers.append(arc_agi.base.RemoteEnvironmentWrapper)
        return Mock()

    monkeypatch.setattr(sdk, "make", make)
    session = ArcadeSession()
    session.make("first")
    session.make("second")
    assert wrappers == [TransportRemoteEnvironment, TransportRemoteEnvironment]
    assert arc_agi.base.RemoteEnvironmentWrapper is original
    with pytest.raises(ValueError, match="only be started once"):
        session.make("first")
