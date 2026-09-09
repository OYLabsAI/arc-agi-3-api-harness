"""Controller-only scorecard attribution. Never supplied to the solver."""

import copy
import os
from unittest.mock import patch

from .environment import ArcadeSession, SDKEnvironment, TransportRemoteEnvironment, redact_credentials


def attribution_for(args, source_sha256, run_id):
    harness = (getattr(args, "harness_name", None) or "").strip()
    team = (getattr(args, "team_name", None) or "").strip()
    if not harness and not team:
        return None
    if not harness or not team:
        raise ValueError("Provide both --harness-name and --team-name")
    if args.provider != "codex-native" or args.mode != "competition":
        raise ValueError("Named subscription runs require --provider codex-native --mode competition")
    if not os.environ.get("ARC_API_KEY", "").strip():
        raise ValueError("Set the intended ARC account's ARC_API_KEY for a named run")
    return {
        "harness_name": harness,
        "team_name": team,
        "run_id": run_id,
        "source_sha256": source_sha256,
        "model": args.model,
        "effort": args.effort,
        "fast_mode": args.fast_mode,
        "mode": args.mode,
        "provider": "codex-native",
        "authentication": "chatgpt_subscription",
        "evaluation_scope": "public",
        "source_visibility": "private",
        "verified_by_arc_prize": False,
    }


class NamedArcadeSession(ArcadeSession):
    """Route every game and finalization to one explicitly named card."""

    def __init__(self, mode, environments_dir, recordings_dir, *, attribution):
        super().__init__(mode, environments_dir, recordings_dir)
        self.attribution = copy.deepcopy(attribution)
        self.card_id = None
        self._card_creation_attempted = False

    def scorecard_reference(self):
        return {"card_id": self.card_id, "base_url": self.arc.arc_base_url, "mode": self.mode}

    def make(self, game_id):
        if game_id in self.started:
            raise ValueError("An environment can only be started once per evaluation")
        self.started.add(game_id)
        if self.card_id is None:
            if self._card_creation_attempted:
                raise RuntimeError("Named scorecard creation outcome is uncertain; no retry permitted")
            self._card_creation_attempted = True
            self.card_id = self.arc.create_scorecard(
                tags=[self.attribution["harness_name"], self.attribution["team_name"],
                      self.attribution.get("evaluation_scope", "public"),
                      self.attribution.get("provider", "codex-native")],
                opaque=self.attribution,
            )
            if not self.card_id:
                raise RuntimeError("Named scorecard creation returned no identifier")
        # Preserve the successful run's transport for the very first RESET too.
        with patch("arc_agi.base.RemoteEnvironmentWrapper", TransportRemoteEnvironment):
            env = self.arc.make(game_id, scorecard_id=self.card_id)
        if env is None:
            raise RuntimeError(f"Cannot create environment {game_id}")
        return SDKEnvironment(env)

    def snapshot(self):
        if self.card_id is None or self.mode == "competition":
            return None
        card = self.arc.get_scorecard(self.card_id)
        return redact_credentials(card.model_dump(mode="json")) if card is not None else None

    def close(self):
        if self.card_id is None:
            return None
        card = self.arc.close_scorecard(self.card_id)
        return redact_credentials(card.model_dump(mode="json")) if card is not None else None
