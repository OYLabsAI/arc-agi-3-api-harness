import json
from collections import deque
from types import SimpleNamespace

import pytest

from arc_harness.app_server import OVERLOAD_RECOVERY, TIMEOUT_RECOVERY, AppServerProvider, isolated_config
from arc_harness.fixtures import CorridorFixture
from arc_harness.providers import ScriptedProvider
from arc_harness.runner import Runner
from arc_harness.types import Limits, ModelReply, ToolCall


class FakeRpc:
    def __init__(self, account_type="chatgpt"):
        self.account_type = account_type
        self.sent, self.methods = [], []
        self.messages = deque()
        self.closed = False

    def request(self, method, params):
        self.methods.append(method)
        request_id = f"client-{len(self.methods)}"
        results = {
            "initialize": {},
            "account/read": {"account": {"type": self.account_type}},
            "thread/start": {"thread": {"id": "test-thread"}, "model": "gpt-6-astra"},
            "turn/start": {"turn": {"id": "test-turn"}},
            "turn/interrupt": {},
        }
        self.sent.append({"method": method, "params": params})
        self.messages.append({"id": request_id, "result": results[method]})
        if method == "turn/start":
            self.queue_call(1, 100, 20)
        elif method == "turn/interrupt":
            self.messages.extend(
                [
                    {
                        "method": "thread/tokenUsage/updated",
                        "params": {
                            "tokenUsage": {"total": {"inputTokens": 400, "outputTokens": 80}, "last": {}}
                        },
                    },
                    {
                        "method": "turn/completed",
                        "params": {"turn": {"id": "test-turn", "status": "interrupted"}},
                    },
                ]
            )
        return request_id

    def queue_call(self, number, input_tokens, output_tokens):
        self.messages.extend(
            [
                {
                    "method": "thread/tokenUsage/updated",
                    "params": {
                        "tokenUsage": {
                            "total": {"inputTokens": input_tokens, "outputTokens": output_tokens},
                            "last": {"inputTokens": 100, "outputTokens": 20},
                        }
                    },
                },
                {
                    "id": f"server-{number}",
                    "method": "item/tool/call",
                    "params": {
                        "threadId": "test-thread",
                        "turnId": "test-turn",
                        "callId": f"call-{number}",
                        "tool": "arc_act",
                        "arguments": {"experiment": "Move", "actions": [{"name": "ACTION4"}]},
                    },
                },
            ]
        )

    def send(self, message):
        self.sent.append(message)
        if message.get("id") == "server-1":
            self.queue_call(2, 250, 55)

    def receive(self, deadline):
        return self.messages.popleft()

    def close(self):
        self.closed = True


def test_native_tool_continuation_and_incremental_usage():
    rpc = FakeRpc()
    provider = AppServerProvider(transport=rpc)
    try:
        first = provider.next({"frame": "initial"}, None, 10, None)
        assert (first.input_tokens, first.output_tokens) == (100, 20)
        assert first.calls[0].call_id == "call-1"
        provider.result(first.calls[0], {"executed": 1})
        second = provider.next({"frame": "after-action"}, None, 10, None)
        assert (second.input_tokens, second.output_tokens) == (150, 35)
        assert rpc.methods.count("turn/start") == 1
        response = next(m for m in rpc.sent if m.get("id") == "server-1")
        content = response["result"]["contentItems"]
        assert json.loads(content[0]["text"])["current"] == {"frame": "after-action"}
        assert response["result"]["success"] is True
        assert provider.stats()["usage_events"] == 2
        assert len(provider.drain_events()) == 3
        assert provider.drain_events() == []
    finally:
        provider.close()
    assert rpc.closed


def test_subscription_provider_rejects_api_billing():
    rpc = FakeRpc(account_type="apiKey")
    provider = AppServerProvider(transport=rpc)
    try:
        with pytest.raises(RuntimeError, match="ChatGPT Codex login"):
            provider.next({}, None, 10, None)
        assert "turn/start" not in rpc.methods
    finally:
        provider.close()


def test_native_provider_rejects_external_tool_use():
    provider = AppServerProvider(transport=FakeRpc())
    try:
        with pytest.raises(RuntimeError, match="Unexpected external tool"):
            provider._event({"method": "item/started", "params": {"item": {"type": "commandExecution"}}})
    finally:
        provider.close()


def test_disabled_token_cutoff_keeps_action_limit(tmp_path):
    provider = ScriptedProvider([])
    provider.next = lambda *a, **kw: ModelReply(
        [ToolCall("act", {"experiment": "Move", "actions": [{"name": "ACTION4"}]})], 2_000_000, 1000
    )
    result = Runner(CorridorFixture(), provider, tmp_path / "run", Limits(max_tokens=0, max_actions=2)).run()
    assert result["status"] == "actions_budget"
    assert result["actions_submitted"] == 2
    assert result["input_tokens"] == 4_000_000


def test_negative_token_cutoff_is_rejected():
    with pytest.raises(ValueError, match="nonnegative"):
        Limits(max_tokens=-1)


def test_native_finalization_collects_late_usage_without_another_inference():
    rpc = FakeRpc()
    provider = AppServerProvider(transport=rpc)
    try:
        first = provider.next({}, None, 10, None)
        provider.result(first.calls[0], {"stopped": True})
        provider.finalize()
        stats = provider.stats()
        assert stats["usage_complete"] is True
        assert stats["total_usage"]["inputTokens"] == 400
        assert rpc.methods.count("turn/start") == 1
        assert not any(m.get("id") == "server-1" for m in rpc.sent)
        provider.finalize()
        assert rpc.methods.count("turn/interrupt") == 1
    finally:
        provider.close()


def test_request_usage_is_deduplicated_and_excludes_response_contents():
    provider = AppServerProvider(transport=FakeRpc())
    usage = {"inputTokens": 100, "cachedInputTokens": 80, "outputTokens": 20,
             "reasoningOutputTokens": 5, "totalTokens": 120}
    message = {"method": "rawResponse/completed", "params": {
        "responseId": "response-1", "threadId": "test-thread", "turnId": "test-turn",
        "usage": usage, "usageMetadata": {"private": "must-not-export"},
    }}
    try:
        provider._event(message)
        provider._event(message)
        provider.total = usage
        events = provider.drain_events()
        assert len(events) == 1
        assert events[0]["data"]["fast_mode"] is False
        assert "must-not-export" not in json.dumps(events)
        assert provider.stats()["completed_model_responses"] == 1
        assert provider.stats()["per_call_usage_reconciled"] is True
        provider._event({"method": "rawResponse/completed", "params": {"responseId": "response-2"}})
        assert provider.stats()["per_call_usage_reconciled"] is False
    finally:
        provider.close()


def test_standard_processing_and_raw_usage_are_requested():
    rpc = FakeRpc()
    provider = AppServerProvider(transport=rpc)
    try:
        provider.next({}, None, 10, None)
        start = next(m["params"] for m in rpc.sent if m.get("method") == "thread/start")
        assert start["experimentalRawEvents"] is True
        assert start["serviceTier"] == "default"
        assert start["config"]["features.fast_mode"] is False
        with pytest.raises(RuntimeError, match="rerouted"):
            provider._event({"method": "model/rerouted", "params": {}})
    finally:
        provider.close()


@pytest.fixture
def retry_clock(monkeypatch):
    clock = SimpleNamespace(now=1000., delays=[])

    def sleep(seconds):
        clock.delays.append(seconds)
        clock.now += seconds

    monkeypatch.setattr("arc_harness.app_server.time", SimpleNamespace(
        monotonic=lambda: clock.now, sleep=sleep,
    ))
    return clock


class RecoveryRpc(FakeRpc):
    def __init__(self, failures=1, code="serverOverloaded", after_action=False):
        super().__init__()
        self.failures = failures
        self.code = code
        self.after_action = after_action
        self.received = []

    def queue_failure(self, will_retry=False):
        error = {"message": "Provider failure", "codexErrorInfo": self.code}
        self.messages.append({"method": "error", "params": {
            "error": error, "willRetry": will_retry,
            "threadId": "test-thread", "turnId": "test-turn",
        }})
        if not will_retry:
            self.messages.append({"method": "turn/completed", "params": {
                "turn": {"id": "test-turn", "status": "failed", "error": error},
            }})

    def request(self, method, params):
        if method == "turn/start" and self.methods.count("turn/start"):
            assert self.received[-1]["method"] == "turn/completed"
            assert params["threadId"] == "test-thread"
        request_id = super().request(method, params)
        if method == "turn/start":
            self.messages.pop()
            self.messages.pop()
            if self.failures and not self.after_action:
                self.failures -= 1
                self.queue_failure()
            else:
                self.queue_call(2 if self.methods.count("turn/start") > 1 else 1, 250, 55)
        return request_id

    def send(self, message):
        if message.get("id") == "server-1" and self.after_action:
            self.sent.append(message)
            self.after_action = False
            self.failures -= 1
            self.queue_failure()
        else:
            super().send(message)

    def receive(self, deadline):
        message = super().receive(deadline)
        self.received.append(message)
        return message


def test_overload_recovers_same_thread_and_refreshes_time_budget(retry_clock):
    rpc = RecoveryRpc(failures=2)
    provider = AppServerProvider(transport=rpc)
    live = []
    provider.set_event_sink(lambda kind, data: live.append({"kind": kind, "data": data}))
    context = {"observation": "current", "budget": {"seconds_left": 7200, "tokens_left": None}}
    try:
        reply = provider.next(context, None, 300, None)
        assert reply.calls[0].name == "act"
        assert retry_clock.delays == [5, 10]
        assert rpc.methods.count("thread/start") == 1
        assert rpc.methods.count("turn/start") == 3
        turns = [m["params"] for m in rpc.sent if m.get("method") == "turn/start"]
        latest = json.loads(turns[-1]["input"][0]["text"])
        assert latest["observation"] == "current"
        assert latest["budget"]["seconds_left"] == 7185
        assert context["budget"]["seconds_left"] == 7200
        assert all(t["effort"] == "high" for t in turns)
        assert provider.stats()["overload_retries"] == 2
        assert len([e for e in live if e["kind"] == "provider_error"]) == 2
        assert all(e["data"]["usage"] is None for e in live if e["kind"] == "provider_error")
        assert live[-1]["data"]["status"] == "recovered"
        assert provider.drain_events() == []
    finally:
        provider.close()


def test_recovery_after_tool_result_never_repeats_an_environment_action(tmp_path, retry_clock):
    rpc = RecoveryRpc(after_action=True)
    result = Runner(CorridorFixture(), AppServerProvider(transport=rpc), tmp_path / "run",
                    Limits(max_actions=2, max_tokens=0)).run()
    assert result["status"] == "actions_budget"
    assert result["actions_submitted"] == 2
    assert result["provider_stats"]["overload_retries"] == 1
    assert result["provider_stats"]["finalization_error"] is None
    assert rpc.methods.count("thread/start") == 1
    responses = [m for m in rpc.sent if m.get("id") == "server-1"]
    assert len(responses) == 1
    payload = json.loads(responses[0]["result"]["contentItems"][0]["text"])
    assert payload["tool_result"]["executed"] == 1
    recovery_turn = [m["params"] for m in rpc.sent if m.get("method") == "turn/start"][-1]
    resumed_context = json.loads(recovery_turn["input"][0]["text"])
    assert resumed_context["observation"] == payload["current"]["observation"]
    log = (tmp_path / "run" / "provider-recovery.jsonl").read_text()
    assert '"status": "waiting"' in log and '"status": "recovered"' in log


@pytest.mark.parametrize("code", ["usageLimitExceeded", "rateLimitExceeded", "unauthorized", "other"])
def test_non_overload_errors_stop_without_retry_and_finalize_cleanly(code, retry_clock):
    rpc = RecoveryRpc(code=code)
    provider = AppServerProvider(transport=rpc)
    try:
        with pytest.raises(RuntimeError, match=code):
            provider.next({"budget": {"seconds_left": 7200}}, None, 300, None)
        provider.finalize()
        assert retry_clock.delays == []
        assert rpc.methods.count("turn/start") == 1
        assert "turn/interrupt" not in rpc.methods
        assert provider.stats()["finalization_error"] is None
        assert provider.stats()["usage_complete"] is False
    finally:
        provider.close()


def test_persistent_overload_stops_at_bounded_retry_count(retry_clock):
    rpc = RecoveryRpc(failures=100)
    provider = AppServerProvider(transport=rpc)
    try:
        with pytest.raises(RuntimeError, match="recovery budget exhausted"):
            provider.next({"budget": {"seconds_left": 7200}}, None, 300, None)
        assert retry_clock.delays == OVERLOAD_RECOVERY["delays_seconds"]
        assert rpc.methods.count("turn/start") == 1 + len(retry_clock.delays)
        provider.finalize()
        assert "turn/interrupt" not in rpc.methods
    finally:
        provider.close()


def test_recovery_never_extends_game_deadline(retry_clock):
    rpc = RecoveryRpc(failures=100)
    provider = AppServerProvider(transport=rpc)
    try:
        with pytest.raises(RuntimeError, match="recovery budget exhausted"):
            provider.next({"budget": {"seconds_left": 12}}, None, 12, None)
        assert retry_clock.delays == [5]
        assert rpc.methods.count("turn/start") == 2
    finally:
        provider.close()


def test_recovery_deadline_includes_inference_time(retry_clock):
    rpc = RecoveryRpc(failures=100)
    receive = rpc.receive

    def slow_receive(deadline):
        message = receive(deadline)
        if message.get("method") == "error":
            retry_clock.now = min(retry_clock.now + 280, deadline)
            if retry_clock.now >= deadline:
                raise TimeoutError("decision deadline")
        return message

    rpc.receive = slow_receive
    provider = AppServerProvider(transport=rpc)
    try:
        with pytest.raises(TimeoutError, match="timeout recovery budget exhausted"):
            provider.next({"budget": {"seconds_left": 7200}}, None, 300, None)
        assert retry_clock.now == 1000 + TIMEOUT_RECOVERY["max_environment_idle_seconds"]
        assert retry_clock.delays == [5, 10]
        assert rpc.methods.count("turn/start") == 3
    finally:
        provider.close()


def test_failed_turn_without_error_notification_is_still_logged(retry_clock):
    rpc = RecoveryRpc(failures=0)
    provider = AppServerProvider(transport=rpc)
    try:
        provider._start(1300)
        provider._start_turn({}, None, 1300)
        rpc.messages.clear()
        rpc.queue_failure()
        rpc.messages.popleft()
        provider.next({"budget": {"seconds_left": 7200}}, None, 300, None)
        assert provider.stats()["provider_errors"] == 1
        assert provider.stats()["overload_retries"] == 1
    finally:
        provider.close()


def test_codex_internal_retry_does_not_start_a_duplicate_turn(retry_clock):
    rpc = RecoveryRpc(failures=0)
    provider = AppServerProvider(transport=rpc)
    try:
        provider._start(1300)
        provider._start_turn({}, None, 1300)
        rpc.messages.clear()
        rpc.queue_failure(will_retry=True)
        rpc.queue_call(1, 100, 20)
        provider.next({}, None, 300, None)
        assert rpc.methods.count("turn/start") == 1
        assert retry_clock.delays == []
    finally:
        provider.close()


def test_compaction_response_tokens_are_included_beyond_thread_counters():
    provider = AppServerProvider(transport=FakeRpc())
    try:
        for identity, inputs, outputs in [("normal", 100, 20), ("compaction", 80, 5)]:
            provider._event({"method": "rawResponse/completed", "params": {
                "responseId": identity,
                "usage": {"inputTokens": inputs, "outputTokens": outputs, "totalTokens": inputs + outputs},
            }})
        provider.total = {"inputTokens": 100, "outputTokens": 20, "totalTokens": 120}
        assert provider.stats()["accounted_usage"]["totalTokens"] == 205
        assert provider.stats()["total_usage"]["totalTokens"] == 120
        assert provider.stats()["per_call_usage_reconciled"] is False
    finally:
        provider.close()


@pytest.mark.parametrize("effective_tier", ["fast", "priority", "default", None])
def test_fast_mode_is_pinned_verified_and_logged(effective_tier, retry_clock):
    rpc = FakeRpc()
    request = rpc.request

    def start(method, params):
        identity = request(method, params)
        if method == "thread/start":
            rpc.messages[-1]["result"]["serviceTier"] = effective_tier
        return identity

    rpc.request = start
    provider = AppServerProvider(transport=rpc, config=isolated_config("high", True))
    try:
        if effective_tier not in ("fast", "priority"):
            with pytest.raises(RuntimeError, match="requested service tier"):
                provider.next({}, None, 600, None)
            assert "turn/start" not in rpc.methods
            return
        provider.next({}, None, 600, None)
        for message in rpc.sent:
            if message.get("method") in ("thread/start", "turn/start"):
                assert message["params"]["serviceTier"] == "fast"
        provider._event({"method": "rawResponse/completed", "params": {
            "responseId": "fast-response", "usage": {"inputTokens": 100, "outputTokens": 20},
        }})
        records = [e for e in provider.drain_events() if e["kind"] in
                   ("provider_started", "provider_model_call")]
        assert len(records) == 2 and all(e["data"]["fast_mode"] is True for e in records)
        assert retry_clock.delays == []
    finally:
        provider.close()


class TimeoutRpc(FakeRpc):
    def __init__(self, clock, failures=1, after_action=False, late_tool=False, confirm=True):
        super().__init__()
        self.clock, self.failures, self.after_action = clock, failures, after_action
        self.late_tool, self.confirm = late_tool, confirm
        self.stalling = False
        self.terminal_observed = False

    def request(self, method, params):
        if method == "turn/start" and self.methods.count("turn/start"):
            assert self.terminal_observed
            self.terminal_observed = False
        identity = super().request(method, params)
        if method == "turn/start":
            self.messages.pop()
            self.messages.pop()
            if self.failures and not self.after_action:
                self.failures -= 1
                self.stalling = True
            else:
                self.queue_call(2 if self.methods.count("turn/start") > 1 else 1, 250, 55)
        elif method == "turn/interrupt":
            self.stalling = False
            if self.late_tool:
                self.queue_call(99, 300, 60)
                call, usage = self.messages.pop(), self.messages.pop()
                self.messages.appendleft(call)
                self.messages.appendleft(usage)
            if not self.confirm:
                self.messages = deque(m for m in self.messages if m.get("method") != "turn/completed")
                self.stalling = True
        return identity

    def send(self, message):
        if message.get("id") == "server-1" and self.after_action:
            self.sent.append(message)
            self.after_action = False
            self.failures -= 1
            self.stalling = True
        else:
            super().send(message)

    def receive(self, deadline):
        if not self.messages and self.stalling:
            self.clock.now = deadline
            raise TimeoutError("simulated stalled inference")
        message = super().receive(deadline)
        if message.get("method") == "turn/completed":
            self.terminal_observed = True
        return message


def test_timeout_cancels_then_resumes_without_repeating_actions(tmp_path, retry_clock):
    rpc = TimeoutRpc(retry_clock, after_action=True, late_tool=True)
    result = Runner(CorridorFixture(), AppServerProvider(transport=rpc), tmp_path / "run",
                    Limits(max_actions=2, max_tokens=0)).run()
    assert result["status"] == "actions_budget"
    assert result["actions_submitted"] == 2
    stats = result["provider_stats"]
    assert stats["timeout_retries"] == stats["decision_timeouts"] == 1
    assert stats["cancelled_tool_calls"] >= 1
    assert stats["usage_complete"] is False
    assert stats["finalization_error"] is None
    assert rpc.methods.count("thread/start") == 1
    assert rpc.methods.count("turn/start") == 2
    assert len([m for m in rpc.sent if m.get("id") == "server-1"]) == 1
    assert all("error" in m for m in rpc.sent if m.get("id") == "server-99")
    assert retry_clock.delays == []
    assert retry_clock.now == 1600
    errors = [json.loads(line) for line in (tmp_path / "run" / "events.jsonl").open()
              if json.loads(line)["kind"] == "provider_error"]
    assert errors[0]["data"]["code"] == "decisionTimeout"
    assert errors[0]["data"]["usage"] is None


@pytest.mark.parametrize("game_seconds,ceiling,turn_count", [(7200, 840, 2), (400, 400, 1)])
def test_persistent_timeout_respects_idle_and_game_deadlines(retry_clock, game_seconds, ceiling, turn_count):
    rpc = TimeoutRpc(retry_clock, failures=100)
    provider = AppServerProvider(transport=rpc)
    try:
        with pytest.raises(TimeoutError, match="recovery budget exhausted"):
            provider.next({"budget": {"seconds_left": game_seconds}}, None, 600, None)
        assert retry_clock.now == 1000 + ceiling
        assert rpc.methods.count("turn/start") == turn_count
        assert retry_clock.delays == []
        assert provider.stats()["usage_complete"] is False
    finally:
        provider.close()


def test_timeout_never_restarts_without_confirmed_interruption(retry_clock):
    rpc = TimeoutRpc(retry_clock, confirm=False)
    provider = AppServerProvider(transport=rpc)
    try:
        with pytest.raises(TimeoutError):
            provider.next({"budget": {"seconds_left": 7200}}, None, 600, None)
        assert rpc.methods.count("turn/start") == 1
        assert retry_clock.now == 1620
    finally:
        provider.close()


def test_slow_healthy_inference_uses_larger_ceiling_without_extra_turns(retry_clock):
    rpc = FakeRpc()
    receive = rpc.receive

    def slow_receive(deadline):
        message = receive(deadline)
        if message.get("method") == "item/tool/call":
            retry_clock.now += 450
            assert retry_clock.now < deadline
        return message

    rpc.receive = slow_receive
    provider = AppServerProvider(transport=rpc)
    try:
        reply = provider.next({"budget": {"seconds_left": 7200}}, None,
                              provider.decision_timeout_seconds, None)
        assert reply.calls[0].name == "act"
        assert retry_clock.delays == []
        assert rpc.methods.count("turn/start") == 1
        assert "turn/interrupt" not in rpc.methods
    finally:
        provider.close()
