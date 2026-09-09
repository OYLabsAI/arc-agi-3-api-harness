from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

ActionName = Literal["RESET", "ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6", "ACTION7"]
StateName = Literal["NOT_PLAYED", "NOT_FINISHED", "WIN", "GAME_OVER"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Pixel(StrictModel):
    x: int = Field(ge=0, le=63)
    y: int = Field(ge=0, le=63)
    color: int = Field(ge=0, le=15)


class Action(StrictModel):
    name: ActionName
    x: int | None = Field(default=None, ge=0, le=63)
    y: int | None = Field(default=None, ge=0, le=63)
    expected_pixels: list[Pixel] = Field(default_factory=list, max_length=64)
    expected_state: StateName | None = None
    expected_levels: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def coordinates(self):
        if self.name == "ACTION6" and (self.x is None or self.y is None):
            raise ValueError("ACTION6 requires x and y")
        if self.name != "ACTION6" and (self.x is not None or self.y is not None):
            raise ValueError("Only ACTION6 accepts coordinates")
        return self

    def command(self) -> dict:
        return {"name": self.name, "x": self.x, "y": self.y}


class Act(StrictModel):
    experiment: str = Field(min_length=1, max_length=2000)
    actions: list[Action] = Field(min_length=1, max_length=8)


class Inspect(StrictModel):
    observation_index: int | None = Field(default=None, ge=0)
    frame_index: int = Field(default=-1, ge=-64, le=63)
    crop: list[int] | None = Field(default=None, min_length=4, max_length=4)


class History(StrictModel):
    query: str = Field(default="", max_length=200)
    limit: int = Field(default=8, ge=1, le=20)


class Remember(StrictModel):
    key: str = Field(min_length=1, max_length=100)
    knowledge: str = Field(min_length=1, max_length=4000)
    evidence: list[int] = Field(default_factory=list, max_length=50)
    confidence: Literal["hypothesis", "supported", "refuted"]


class Plan(StrictModel):
    target_hash: str = Field(min_length=64, max_length=64)


class Stop(StrictModel):
    reason: str = Field(min_length=1, max_length=1000)


TOOL_MODELS = {
    "act": Act,
    "inspect": Inspect,
    "history": History,
    "remember": Remember,
    "plan": Plan,
    "stop": Stop,
}
TOOL_DESCRIPTIONS = {
    "act": "Execute 1-8 actions. Each consumes an interaction. Batches stop on failed predictions, no change, level changes, game over, or win. Experiment is a concise hypothesis/test summary, not private reasoning.",
    "inspect": "Free detailed inspection of an observed animation frame; optional crop is [x, y, width, height]. Returns exact colors and components. Never queries hidden game state.",
    "history": "Free search of this game's observed transitions and memories. Query matches literal text; empty query retrieves recent entries.",
    "remember": "Record or revise a concise world-model fact, goal, or hypothesis. Cite transition indices; supported claims require evidence. Memory is scoped to this game/run.",
    "plan": "Find a shortest path to a previously observed state using unambiguous observed transitions only. This empirical model may miss hidden state; verify every proposed action.",
    "stop": "Stop after environment WIN or an exhausted budget, with an explanation. Unfinished games with budget remaining continue. Only the environment can declare WIN.",
}


def strict_schema(schema: dict) -> dict:
    schema = json.loads(json.dumps(schema))

    def visit(node):
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)
    return schema


def tool_schemas() -> list[dict]:
    return [
        {
            "type": "function",
            "name": name,
            "description": TOOL_DESCRIPTIONS[name],
            "strict": True,
            "parameters": strict_schema(cls.model_json_schema()),
        }
        for name, cls in TOOL_MODELS.items()
    ]


@dataclass(frozen=True)
class Observation:
    frames: tuple[np.ndarray, ...]
    state: str
    levels_completed: int
    win_levels: int
    available_actions: tuple[str, ...]

    @classmethod
    def from_sdk(cls, raw):
        if raw is None:
            raise RuntimeError(
                "Environment returned no observation; action outcome is uncertain. Stopping without retry."
            )
        frames = []
        for frame in raw.frame:
            array = np.asarray(frame)
            if array.ndim != 2 or not (0 < array.shape[0] <= 64 and 0 < array.shape[1] <= 64):
                raise ValueError("Expected an observed grid no larger than 64 x 64")
            if not np.issubdtype(array.dtype, np.integer) or np.any(array < 0) or np.any(array > 15):
                raise ValueError("Grid colors must be integers 0-15")
            array = np.array(array, dtype=np.uint8, copy=True)
            array.flags.writeable = False
            frames.append(array)
        if not frames:
            raise ValueError("Environment returned no frames")
        names = tuple(
            a.name if hasattr(a, "name") else ("RESET" if int(a) == 0 else f"ACTION{int(a)}")
            for a in raw.available_actions
        )
        state = raw.state.name if hasattr(raw.state, "name") else str(raw.state)
        if state not in ("NOT_PLAYED", "NOT_FINISHED", "WIN", "GAME_OVER"):
            raise ValueError(f"Unknown game state: {state}")
        return cls(tuple(frames), state, int(raw.levels_completed), int(raw.win_levels), names)

    @property
    def grid(self):
        return self.frames[-1]

    @property
    def fingerprint(self):
        # Include shape, level, state, and legal actions to avoid visual aliases across levels.
        header = json.dumps(
            [self.grid.shape, self.state, self.levels_completed, self.win_levels, self.available_actions]
        ).encode()
        return hashlib.sha256(header + self.grid.tobytes()).hexdigest()

    def metadata(self):
        return {
            "state_hash": self.fingerprint,
            "state": self.state,
            "levels_completed": self.levels_completed,
            "win_levels": self.win_levels,
            "available_actions": list(self.available_actions),
            "animation_frames": len(self.frames),
        }

    def payload(self):
        return {**self.metadata(), "frames": [f.tolist() for f in self.frames]}


@dataclass
class ToolCall:
    name: str
    arguments: dict
    call_id: str = ""


@dataclass
class ModelReply:
    calls: list[ToolCall]
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class Limits:
    max_actions: int = 300
    max_calls: int = 100
    max_tokens: int = 250_000
    max_seconds: float = 1800
    max_batch: int = 8

    def __post_init__(self):
        if any(
            v <= 0
            for v in (self.max_actions, self.max_calls, self.max_seconds, self.max_batch)
        ):
            raise ValueError("All budgets must be positive")
        if self.max_tokens < 0:
            raise ValueError("max_tokens must be nonnegative; zero disables the cumulative token cutoff")
        if self.max_batch > 8:
            raise ValueError("max_batch cannot exceed 8")
