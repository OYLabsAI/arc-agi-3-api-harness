import pytest

from arc_harness.audit import level_rows, usage_rows


def event(kind, data, seconds=0):
    return {"kind": kind, "data": data, "at": f"2026-09-05T00:00:{seconds:02d}+00:00"}


def test_historical_duplicates_are_removed_without_fabricating_fast_mode():
    usage = {"inputTokens": 100, "cachedInputTokens": 80, "outputTokens": 20,
             "reasoningOutputTokens": 5, "totalTokens": 120}
    update = event("provider_usage", {"total": usage, "last": usage})
    rows, duplicates = usage_rows([
        event("provider_started", {}), update, update,
    ], "generic", {"model": "model", "effort": "high"})
    assert duplicates == 1 and len(rows) == 1
    assert rows[0]["total_tokens"] == 120
    assert rows[0]["fast_mode"] is None and rows[0]["response_id"] is None


def test_usage_gap_cannot_be_misrepresented_as_one_call():
    with pytest.raises(ValueError, match="increment"):
        usage_rows([event("provider_started", {}), event("provider_usage", {
            "total": {"inputTokens": 200}, "last": {"inputTokens": 100},
        })], "generic", {"model": "model", "effort": "high"})


def test_level_time_partitions_at_completion_and_resets_count():
    rows = level_rows([
        event("run_started", {}, 0),
        event("action_submitted", {"action": {"name": "ACTION1"}}, 4),
        event("action_submitted", {"action": {"name": "RESET"}}, 6),
        event("observation", {"levels_completed": 1}, 10),
        event("action_submitted", {"action": {"name": "ACTION2"}}, 17),
        event("observation", {"levels_completed": 2}, 20),
    ], "generic", [1, 2])
    assert [r["wall_clock_seconds"] for r in rows] == [10, 10]
    assert [r["actions_taken"] for r in rows] == [2, 1]
    assert [r["rhae_percent"] for r in rows] == [25, 115]
    assert rows[0]["resets"] == 1
