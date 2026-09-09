from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from unittest.mock import patch

from arc_agi.remote_wrapper import RemoteEnvironmentWrapper
from requests.adapters import HTTPAdapter

from .types import Observation

ARC_TRANSPORT = {
    "connect_timeout_seconds": 10,
    "read_timeout_seconds": 120,
    "automatic_http_retries": 0,
    "uncertain_action_outcome": "stop_without_repeating_action",
    "preserve_routing_cookies": True,
}


class ARCTransportAdapter(HTTPAdapter):
    """Override SDK 0.9.9's fixed 10-second read timeout without replaying POSTs."""

    def __init__(self):
        super().__init__(max_retries=0)

    def send(self, request, **kwargs):
        kwargs["timeout"] = (
            ARC_TRANSPORT["connect_timeout_seconds"],
            ARC_TRANSPORT["read_timeout_seconds"],
        )
        return super().send(request, **kwargs)


def configure_transport(session):
    session.mount("https://", ARCTransportAdapter())
    session.mount("http://", ARCTransportAdapter())


class TransportRemoteEnvironment(RemoteEnvironmentWrapper):
    def reset(self):
        # The SDK constructor calls reset before returning the wrapper. Install
        # the adapter here so the first RESET has the same timeout as all actions.
        if not isinstance(self._session.get_adapter(self.base_url), ARCTransportAdapter):
            configure_transport(self._session)
        return super().reset()


def redact_credentials(value):
    """SDK scorecards may echo an API key; never persist it with shareable results."""
    if isinstance(value, dict):
        secrets = {
            "api_key",
            "apikey",
            "arc_api_key",
            "openai_api_key",
            "authorization",
            "access_token",
            "refresh_token",
        }
        return {
            key: "[REDACTED]" if key.casefold() in secrets else redact_credentials(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_credentials(item) for item in value]
    if isinstance(value, str):
        for name in ("OPENAI_API_KEY", "ARC_API_KEY"):
            secret = os.environ.get(name)
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return re.sub(r"sk-[A-Za-z0-9_-]{12,}", "[REDACTED]", value)
    return value


class ArcadeSession:
    """Only the documented observation/action interface crosses into the solver."""

    def __init__(self, mode="online", environments_dir="environment_files", recordings_dir="recordings"):
        from arc_agi import Arcade, OperationMode

        if mode not in ("online", "offline", "competition"):
            raise ValueError("Mode must be online, offline, or competition")
        logger = logging.getLogger("arc_harness.sdk")
        logger.setLevel(logging.WARNING)
        self.mode = mode
        self.arc = Arcade(
            operation_mode=OperationMode[mode.upper()],
            environments_dir=str(Path(environments_dir).resolve()),
            recordings_dir=str(Path(recordings_dir).resolve()),
            logger=logger,
        )
        if self.arc.operation_mode in (OperationMode.ONLINE, OperationMode.COMPETITION):
            # SDK 0.9.9 passes _session.cookies to game wrappers, while its
            # scorecard methods merge a separate, older master jar back into it.
            # Share the actual jar so refreshed routing cookies survive a long
            # game and subsequent scorecard reads/closure. Never log cookies.
            self.arc._master_cookie_jar = self.arc._session.cookies
            configure_transport(self.arc._session)
        self.started = set()

    def scorecard_reference(self):
        """Persist a recoverable identifier without credentials or cookies."""
        return {
            "card_id": self.arc._default_scorecard_id,
            "base_url": self.arc.arc_base_url,
            "mode": self.mode,
        }

    def games(self):
        return sorted(game.game_id for game in self.arc.get_environments())

    def make(self, game_id):
        if game_id in self.started:
            raise ValueError("An environment can only be started once per evaluation")
        self.started.add(game_id)
        # SDK 0.9.9 has no wrapper-factory/timeout argument. Scope the replacement
        # to this synchronous construction; do not modify the installed SDK.
        with patch("arc_agi.base.RemoteEnvironmentWrapper", TransportRemoteEnvironment):
            env = self.arc.make(game_id)
        if env is None:
            raise RuntimeError(f"Cannot create environment {game_id}")
        return SDKEnvironment(env)

    def close(self):
        card = self.arc.close_scorecard()
        return redact_credentials(card.model_dump(mode="json")) if card is not None else None

    def snapshot(self):
        """Read the existing scorecard between games without closing it.

        The controller stores this separately from observations; scores and human
        baselines never enter the model's game conversation.
        """
        card = self.arc.get_scorecard()
        return redact_credentials(card.model_dump(mode="json")) if card is not None else None


class SDKEnvironment:
    def __init__(self, env):
        self._env = env

    def initial(self):
        raw = self._env.observation_space
        if raw is None:
            raise RuntimeError("Initial RESET outcome is uncertain; stopping without retry")
        return Observation.from_sdk(raw)

    def step(self, action, experiment):
        from arcengine import GameAction

        data = {"x": action.x, "y": action.y} if action.name == "ACTION6" else None
        # Never retry a mutating request automatically: a timeout can hide a successful action.
        return Observation.from_sdk(
            self._env.step(GameAction[action.name], data=data, reasoning={"experiment": experiment})
        )
