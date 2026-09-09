import json
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from arc_harness.cli import resolve_games
from arc_harness.environment import SDKEnvironment, redact_credentials
from arc_harness.fixtures import CorridorFixture, demo_provider
from arc_harness.perception import check_prediction, components, difference
from arc_harness.providers import ResponsesProvider, ScriptedProvider
from arc_harness.report import render_replay
from arc_harness.runner import Runner
from arc_harness.scoring import game_score, selected_set_score, total_score
from arc_harness.store import Store
from arc_harness.types import Action, Limits, ModelReply, Observation, Remember, ToolCall, tool_schemas


def call(actions, experiment="Test"):
    return ToolCall("act", {"experiment": experiment, "actions": actions})


def run(tmp_path, calls, env=None, **limits):
    limits.setdefault("max_calls", len(calls) + 1)
    provider = ScriptedProvider(calls)
    directory = tmp_path / "run"
    result = Runner(env or CorridorFixture(), provider, directory, Limits(**limits)).run()
    return result, provider, directory


def test_end_to_end_demo(tmp_path):
    directory = tmp_path / "run"
    result = Runner(CorridorFixture(), demo_provider(), directory, Limits()).run()
    assert result["won"] and result["actions_submitted"] == 5
    assert result["predictions_tested"] == 5
    assert result["official_benchmark_score_percent"] is None
    assert json.loads((directory / "result.json").read_text()) == result


def test_early_stop_continues_same_game_to_win(tmp_path):
    stop = ToolCall("stop", {"reason": "I do not know what to try"})
    actions = call([{"name": "ACTION4", "expected_pixels": [{"x": x, "y": 3, "color": 9}]}
                    for x in range(2, 7)])
    result, provider, directory = run(tmp_path, [stop, actions])
    assert result["won"] and result["actions_submitted"] == 5
    assert result["model_calls"] == 2
    assert provider.results[0]["stopped"] is False
    assert provider.results[0]["budget"]["actions_left"] == result["limits"]["max_actions"]
    events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    rejected = [e for e in events if e["kind"] == "early_stop_rejected"]
    assert len(rejected) == 1
    assert rejected[0]["data"]["reason"] == stop.arguments["reason"]


def test_repeated_early_stops_cannot_extend_budget(tmp_path):
    stop = ToolCall("stop", {"reason": "No further ideas"})
    result, provider, _ = run(tmp_path, [stop] * 5, max_calls=3)
    assert result["status"] == "model_calls_budget"
    assert result["model_calls"] == 3
    assert result["actions_submitted"] == 0 and not result["won"]
    assert [r["stopped"] for r in provider.results] == [False, False, True]


def test_bad_prediction_interrupts_batch(tmp_path):
    result, provider, _ = run(
        tmp_path,
        [
            call(
                [
                    {"name": "ACTION4", "expected_pixels": [{"x": 2, "y": 3, "color": 14}]},
                    {"name": "ACTION4", "expected_state": "NOT_FINISHED"},
                ]
            )
        ],
    )
    assert result["actions_submitted"] == 1
    assert result["prediction_failures"] == 1
    assert provider.results[0]["interrupted"] == "prediction_mismatch"


def test_noop_interrupts_batch(tmp_path):
    result, provider, _ = run(tmp_path, [call([{"name": "ACTION3", "expected_state": "NOT_FINISHED"}] * 3)])
    assert result["actions_submitted"] == 1
    assert provider.results[0]["interrupted"] == "no_observable_change"


def test_action_budget_is_hard_within_batch(tmp_path):
    result, _, _ = run(
        tmp_path, [call([{"name": "ACTION4", "expected_state": "NOT_FINISHED"}] * 5)], max_actions=2
    )
    assert result["actions_submitted"] == 2
    assert result["status"] == "actions_budget"


def test_last_model_call_can_act(tmp_path):
    result, _, _ = run(tmp_path, [call([{"name": "ACTION4"}])], max_calls=1)
    assert result["actions_submitted"] == 1
    assert result["status"] == "model_calls_budget"


def test_invalid_action_does_not_reach_environment(tmp_path):
    env = CorridorFixture()
    env.step = Mock(wraps=env.step)
    result, _, _ = run(tmp_path, [call([{"name": "ACTION6", "x": 10, "y": 10}])], env=env)
    assert result["actions_submitted"] == 0
    env.step.assert_not_called()


@pytest.mark.parametrize(
    "action",
    [
        {"name": "ACTION6"},
        {"name": "ACTION6", "x": 64, "y": 0},
        {"name": "ACTION1", "x": 1, "y": 1},
        {"name": "ACTION6", "x": True, "y": 1},
        {"name": "ACTION6", "x": 1.5, "y": 1},
        {"name": "ACTION8"},
    ],
)
def test_action_validation(action):
    with pytest.raises(ValueError):
        Action.model_validate(action)


def test_batch_without_predictions_rejected(tmp_path):
    result, provider, _ = run(tmp_path, [call([{"name": "ACTION4"}] * 2)])
    assert result["actions_submitted"] == 0
    assert "prediction" in provider.results[0]["error"]


def test_uncertain_mutation_not_retried(tmp_path):
    env = CorridorFixture()
    env.step = Mock(side_effect=ValueError("transport failed after submission"))
    result, _, directory = run(tmp_path, [call([{"name": "ACTION4"}])] * 3, env=env)
    assert result["status"] == "error" and result["actions_submitted"] == 1
    assert env.step.call_count == 1
    events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    assert next(e for e in events if e["kind"] == "error")["data"]["last_action_may_have_executed"]


def test_game_over_only_allows_reset(tmp_path):
    class Over(CorridorFixture):
        def initial(self):
            o = super().initial()
            return Observation(o.frames, "GAME_OVER", 0, 1, o.available_actions)

    result, provider, _ = run(tmp_path, [call([{"name": "ACTION4"}])], env=Over())
    assert result["actions_submitted"] == 0
    assert provider.results[0]["interrupted"] == "only_reset_is_legal"


def test_level_change_interrupts_plan(tmp_path):
    class LevelChange(CorridorFixture):
        def step(self, action, experiment):
            o = super().step(action, experiment)
            return Observation(o.frames, "NOT_FINISHED", 1, 2, o.available_actions)

    result, provider, _ = run(
        tmp_path, [call([{"name": "ACTION4", "expected_state": "NOT_FINISHED"}] * 3)], env=LevelChange()
    )
    assert result["actions_submitted"] == 1
    assert provider.results[0]["interrupted"] == "level_changed"


def test_win_stops_extra_actions(tmp_path):
    result, provider, _ = run(
        tmp_path,
        [
            call(
                [
                    {"name": "ACTION4", "expected_pixels": [{"x": min(x, 6), "y": 3, "color": 9}]}
                    for x in range(2, 10)
                ]
            )
        ],
    )
    assert result["won"] and result["actions_submitted"] == 5
    assert provider.results[0]["interrupted"] == "win"


def test_memory_evidence_and_run_isolation(tmp_path):
    one = Store(tmp_path / "one")
    with pytest.raises(ValueError):
        one.remember(Remember(key="rule", knowledge="x", evidence=[], confidence="supported"))
    with pytest.raises(ValueError):
        one.remember(Remember(key="rule", knowledge="x", evidence=[0], confidence="supported"))
    one.remember(Remember(key="rule", knowledge="x", evidence=[], confidence="hypothesis"))
    two = Store(tmp_path / "two")
    assert len(one.memories()) == 1 and two.memories() == []
    one.close()
    two.close()


def test_graph_discards_conflicting_transitions(tmp_path):
    store = Store(tmp_path / "evidence")
    store.transitions = [
        {"before": "A", "after": "B", "action": {"name": "ACTION1"}},
        {"before": "B", "after": "C", "action": {"name": "ACTION2"}},
    ]
    assert len(store.path("A", "C")["actions"]) == 2
    store.transitions.append({"before": "A", "after": "D", "action": {"name": "ACTION1"}})
    assert not store.path("A", "C")["found"]
    store.close()


def test_components_coordinates_and_delta():
    grid = np.array([[1, 1, 0], [0, 2, 0]], dtype=np.uint8)
    comp = next(c for c in components(grid)["items"] if c["color"] == 2)
    assert comp["bbox"] == [1, 1, 2, 2]
    after = grid.copy()
    after[1, 2] = 9
    assert difference(grid, after)["sample"] == [[2, 1, 0, 9]]


def test_shape_and_level_part_of_state_identity():
    def obs(grid, level=0):
        return Observation((grid,), "NOT_FINISHED", level, 2, ("ACTION1",))

    a = np.zeros((2, 4), dtype=np.uint8)
    assert obs(a).fingerprint != obs(a.reshape(4, 2)).fingerprint
    assert obs(a).fingerprint != obs(a, 1).fingerprint


def test_sdk_frame_boundary_and_snapshot_copy():
    from arcengine import FrameDataRaw, GameState

    raw = FrameDataRaw(state=GameState.NOT_FINISHED, available_actions=[1, 6], win_levels=2)
    raw.frame = [np.zeros((64, 64), dtype=np.int8)]
    o = Observation.from_sdk(raw)
    raw.frame[0][0, 0] = 2
    assert o.grid[0, 0] == 0
    assert o.available_actions == ("ACTION1", "ACTION6")
    with pytest.raises(RuntimeError):
        Observation.from_sdk(None)
    raw.frame = [np.full((2, 2), 17)]
    with pytest.raises(ValueError):
        Observation.from_sdk(raw)


def test_sdk_initial_does_not_reset_existing_game():
    env = Mock()
    from arcengine import FrameDataRaw

    env.observation_space = FrameDataRaw()
    env.observation_space.frame = [np.zeros((2, 2), dtype=np.int8)]
    SDKEnvironment(env).initial()
    env.reset.assert_not_called()


def test_prediction_handles_out_of_bounds():
    o = CorridorFixture().initial()
    a = Action(name="ACTION4", expected_pixels=[{"x": 63, "y": 63, "color": 1}])
    assert not check_prediction(a, o)["matched"]


def test_rhae_weights_caps_and_missing_games():
    assert game_score([10], [20]) == pytest.approx(0.25)
    assert game_score([10], [1]) == 1
    assert game_score([10] * 5, [1] * 4) == pytest.approx(10 / 15)
    assert game_score([10, 10], [20, 10]) == pytest.approx((0.25 + 2) / 3)
    assert game_score([10], []) == 0
    assert total_score({"A": 1.0}, ["A", "B"]) == 0.5
    with pytest.raises(ValueError):
        game_score([10], [0])
    with pytest.raises(ValueError):
        total_score({"A": float("nan")}, ["A"])


def test_strict_api_schemas_have_required_nullable_fields():
    def check(node):
        if isinstance(node, dict):
            assert "default" not in node
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for item in node.values():
                check(item)
        elif isinstance(node, list):
            for item in node:
                check(item)

    check(tool_schemas())


def test_responses_preserves_reasoning_and_pairs_tools():
    item = Mock(type="reasoning")
    item.model_dump.return_value = {"type": "reasoning", "id": "r", "encrypted_content": "opaque"}
    function = Mock(type="function_call", arguments='{"reason":"done"}', call_id="c")
    function.name = "stop"
    function.model_dump.return_value = {
        "type": "function_call",
        "name": "stop",
        "arguments": function.arguments,
        "call_id": "c",
    }
    client = Mock()
    client.with_options.return_value.responses.create.return_value = SimpleNamespace(
        status="completed", output=[item, function], usage=SimpleNamespace(input_tokens=12, output_tokens=4)
    )
    provider = ResponsesProvider(client=client)
    response = provider.next({}, None, 10, 100)
    provider.result(response.calls[0], {"stopped": True})
    assert provider.items[1]["encrypted_content"] == "opaque"
    assert provider.items[-1]["type"] == "function_call_output"
    assert provider.items[-1]["call_id"] == "c"
    kwargs = client.with_options.return_value.responses.create.call_args.kwargs
    assert kwargs["parallel_tool_calls"] is False and kwargs["store"] is False


def test_token_budget_stops_before_action(tmp_path):
    provider = ScriptedProvider([])
    provider.next = Mock(return_value=ModelReply([call([{"name": "ACTION4"}])], 200, 30))
    result = Runner(CorridorFixture(), provider, tmp_path / "run", Limits(max_tokens=100)).run()
    assert result["status"] == "tokens_budget" and result["actions_submitted"] == 0


def test_timeout_and_interrupt_record_partial_run(tmp_path):
    provider = ScriptedProvider([])
    provider.next = Mock(side_effect=KeyboardInterrupt)
    result = Runner(CorridorFixture(), provider, tmp_path / "run", Limits()).run()
    assert result["status"] == "interrupted"
    assert (tmp_path / "run/result.json").is_file()


def test_replay_escapes_model_content(tmp_path):
    _, _, directory = run(tmp_path, [call([{"name": "ACTION4"}], "</script><script>alert(1)</script>")])
    text = render_replay(directory).read_text()
    assert "</script><script>alert(1)" not in text
    assert "\\u003c/script\\u003e" in text


def test_resolve_game_manifest():
    assert resolve_games(["aa"], ["aa-123", "bb-456"]) == ["aa-123"]
    with pytest.raises(ValueError):
        resolve_games(["aa", "aa-123"], ["aa-123"])
    with pytest.raises(ValueError):
        resolve_games(["aa"], ["aa-123", "aa-456"])


def test_inspect_previous_observation_without_replaying(tmp_path):
    result, provider, _ = run(
        tmp_path,
        [call([{"name": "ACTION4"}]), ToolCall("inspect", {"observation_index": 0, "crop": [1, 3, 2, 1]})],
    )
    assert result["actions_submitted"] == 1
    assert provider.results[1]["rows"] == ["91"]


def test_compact_context_retains_lossless_evidence(tmp_path):
    result, provider, directory = run(tmp_path, [call([{"name": "ACTION4"}])])
    assert "sample" not in provider.results[0]["transitions"][0]["delta"]
    events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    transition = next(e for e in events if e["kind"] == "transition")
    assert transition["data"]["delta"]["sample"] == [[1, 3, 9, 1], [2, 3, 1, 9]]


def test_environment_creation_failure_is_reported(tmp_path, monkeypatch):
    from arc_harness.cli import evaluate, parser

    session = Mock()
    session.games.return_value = ["aa-123"]
    session.make.side_effect = RuntimeError("cannot create game")
    session.close.return_value = None
    provider = Mock()
    monkeypatch.setattr("arc_harness.cli.ArcadeSession", Mock(return_value=session))
    monkeypatch.setattr("arc_harness.cli.CodexProvider", Mock(return_value=provider))
    args = parser().parse_args(["run", "--games", "aa", "--output", str(tmp_path)])
    assert evaluate(args) == 1
    summary = json.loads(next(tmp_path.glob("*/summary.json")).read_text())
    assert summary["unrun_games"] == ["aa-123"]
    assert "cannot create game" in summary["evaluation_error"]
    session.close.assert_called_once()
    provider.close.assert_called_once()


def test_scorecard_credentials_are_redacted_without_changing_scores():
    raw = {"api_key": "secret", "score": 16.67, "environments": [{"score": 100, "API_KEY": "nested"}]}
    clean = redact_credentials(raw)
    assert clean["api_key"] == "[REDACTED]"
    assert clean["environments"][0] == {"score": 100, "API_KEY": "[REDACTED]"}
    assert clean["score"] == 16.67
    assert raw["api_key"] == "secret"


def test_selected_set_score_counts_unrun_games_as_zero():
    card = {"score": 100, "environments": [{"id": "aa", "score": 100, "runs": [{}]}]}
    assert selected_set_score(card, ["aa", "bb", "cc", "dd"]) == 25
    assert selected_set_score(None, ["aa"]) is None


def test_selected_set_score_rejects_best_of_multiple_runs():
    card = {"environments": [{"id": "aa", "score": 100, "runs": [{}, {}]}]}
    with pytest.raises(ValueError, match="single-attempt"):
        selected_set_score(card, ["aa"])


def test_selected_set_score_rejects_unexpected_environment():
    with pytest.raises(ValueError, match="outside"):
        selected_set_score({"environments": [{"id": "bb", "score": 100}]}, ["aa"])
