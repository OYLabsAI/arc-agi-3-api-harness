"""Reference RHAE calculation, matching the documented April 2026 methodology.

This module never supplies baselines to agents. Runtime reports preserve SDK scorecards;
this function is for audits with externally supplied, legitimate human baselines.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def game_score(human_actions: Sequence[int], completed_actions: Sequence[int]) -> float:
    if not human_actions or len(completed_actions) > len(human_actions):
        raise ValueError("Need all level baselines and no more completed levels than total levels")
    if any(type(v) is not int or v <= 0 for v in [*human_actions, *completed_actions]):
        raise ValueError("Action counts must be positive integers")
    denominator = sum(range(1, len(human_actions) + 1))
    weighted = sum((i + 1) * min(1.15, (human_actions[i] / a) ** 2) for i, a in enumerate(completed_actions))
    completion_cap = sum(range(1, len(completed_actions) + 1)) / denominator
    return min(completion_cap, weighted / denominator)


def total_score(scores: dict[str, float], expected_games: Sequence[str]) -> float:
    if not expected_games or len(set(expected_games)) != len(expected_games):
        raise ValueError("Evaluation manifest must contain unique expected game IDs")
    if set(scores) - set(expected_games):
        raise ValueError("Results include games outside the evaluation manifest")
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in scores.values()):
        raise ValueError("Scores must be finite fractions in [0, 1]")
    # Missing games are zeros. Never inflate a run by dropping unsolved environments.
    return sum(scores.get(game, 0) for game in expected_games) / len(expected_games)


def untouched_placeholder(environment: dict) -> bool:
    """Recognize ARC's zero-action catalog entries; never hide another played game."""
    plays = environment.get("runs", [])
    if len(plays) != 1 or environment.get("completed") is not False:
        return False
    play = plays[0]
    if play.get("completed") is not False or play.get("state") != "NOT_FINISHED":
        return False
    if any(type(row.get(k)) not in (int, float) or row[k] != 0
           for row in (environment, play) for k in ("actions", "resets", "levels_completed", "score")):
        return False
    levels = environment.get("level_count")
    return type(levels) is int and levels > 0 and all(
        isinstance(play.get(k), list) and len(play[k]) == levels
        and all(type(v) in (int, float) and v == 0 for v in play[k])
        for k in ("level_actions", "level_scores"))


def selected_environments(scorecard, expected_games, *, allow_unplayed=False):
    entries, seen = {}, set()
    for environment in scorecard.get("environments", []):
        game = environment["id"]
        if game in seen or len(environment.get("runs", [])) > 1:
            raise ValueError("A single-attempt scorecard cannot contain duplicate entries or runs")
        seen.add(game)
        if game not in expected_games:
            if not allow_unplayed or not untouched_placeholder(environment):
                raise ValueError("Played or unverifiable environment outside the evaluation manifest")
        else:
            entries[game] = environment
    return entries


def selected_set_score(scorecard: dict | None, expected_games: Sequence[str], *,
                       allow_unplayed=False) -> float | None:
    """Average official game scores over the declared set, with unrun games zero.

    Preserve unavailable scoring as null. Do not choose a best run or silently
    accept duplicates/unexpected games in a single-attempt evaluation.
    """
    if scorecard is None:
        return None
    scores = {}
    for environment in selected_environments(scorecard, expected_games, allow_unplayed=allow_unplayed).values():
        game_id = environment["id"]
        if game_id in scores or len(environment.get("runs", [])) > 1:
            raise ValueError("A single-attempt scorecard must contain one entry/run per environment")
        score = environment.get("score")
        if score is None:
            return None
        scores[game_id] = score / 100
    return total_score(scores, expected_games) * 100
