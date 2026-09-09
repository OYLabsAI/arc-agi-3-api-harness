"""Tiny synthetic environment for end-to-end software checks, not an ARC-AGI game."""

import numpy as np

from .providers import ScriptedProvider
from .types import Observation, ToolCall


class CorridorFixture:
    def __init__(self):
        self.x = 1

    def initial(self):
        grid = np.full((8, 8), 5, dtype=np.uint8)
        grid[3, 1:7] = 1
        grid[3, 6] = 14
        grid[3, self.x] = 9
        won = self.x == 6
        return Observation((grid,), "WIN" if won else "NOT_FINISHED", int(won), 1, ("ACTION3", "ACTION4"))

    def step(self, action, experiment):
        if action.name == "ACTION4":
            self.x = min(6, self.x + 1)
        elif action.name == "ACTION3":
            self.x = max(1, self.x - 1)
        elif action.name == "RESET":
            self.x = 1
        return self.initial()


def demo_provider():
    return ScriptedProvider(
        [
            ToolCall(
                "act",
                {
                    "experiment": "Synthetic integration check: move the marker to the endpoint.",
                    "actions": [
                        {"name": "ACTION4", "expected_pixels": [{"x": x, "y": 3, "color": 9}]}
                        for x in range(2, 7)
                    ],
                },
            )
        ]
    )
