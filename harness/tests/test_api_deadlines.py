import signal
import time

import httpx
import pytest
from test_api_candidate import Endpoint

from arc_harness.api_budget import BudgetStop, Ledger
from arc_harness.api_provider import APIProvider, api_client
from arc_harness.deadline import DeadlineExpired, wall_timeout


def test_compaction_chain_consumes_one_decision_deadline(tmp_path):
    now, timeouts = [0], []
    durations = iter([120, 100])
    endpoint = Endpoint(compact=True)

    def timed(request):
        timeouts.append(request.extensions["timeout"]["read"])
        now[0] += next(durations)
        return endpoint(request)

    ledger = Ledger(tmp_path / "cost.sqlite", approved_usd=25, max_requests=30,
                    max_seconds=1000, clock=lambda: now[0])
    p = APIProvider(ledger, client=api_client("synthetic", transport=httpx.MockTransport(timed)))
    p.context_tokens = 180000
    assert len(p.next({}, None, 300, None).calls) == 1
    assert timeouts == [300, 180]
    assert now[0] == 220


@pytest.mark.parametrize("slow_stage", ["response"])
def test_late_return_cannot_launch_next_call_or_action(tmp_path, slow_stage):
    now = [0]
    endpoint = Endpoint()

    def timed(request):
        counted = request.url.path.endswith("input_tokens")
        result = endpoint(request)
        if counted == (slow_stage == "count"):
            now[0] += 301
        return result

    ledger = Ledger(tmp_path / "cost.sqlite", approved_usd=25, max_requests=30,
                    max_seconds=1000, clock=lambda: now[0])
    p = APIProvider(ledger, client=api_client("synthetic", transport=httpx.MockTransport(timed)))
    with pytest.raises(BudgetStop, match="decision_deadline"):
        p.next({}, None, 300, None)
    assert endpoint.counts == 0
    assert endpoint.paid == (slow_stage == "response")
    assert p.pending == set()
    if slow_stage == "response":
        assert ledger.report()["requests"][0]["status"] == "accounted"


def test_wall_deadline_interrupts_blocking_transport_and_keeps_reservation(tmp_path):
    endpoint = Endpoint()

    def stalled(request):
        if not request.url.path.endswith("input_tokens"):
            time.sleep(10)
        return endpoint(request)

    ledger = Ledger(tmp_path / "cost.sqlite", approved_usd=25, max_requests=30, max_seconds=1000)
    p = APIProvider(ledger, client=api_client("synthetic", transport=httpx.MockTransport(stalled)))
    before = time.monotonic()
    with pytest.raises(DeadlineExpired):
        p.next({}, None, 0.15, None)
    assert time.monotonic() - before < 1
    assert ledger.report()["charged_or_reserved_usd"] == 24.25
    assert ledger.report()["uncertain_requests"] == 1
    assert p.pending == set()


def test_nested_timeout_does_not_extend_outer_alarm():
    previous = signal.getsignal(signal.SIGALRM)
    before = time.monotonic()
    with pytest.raises(DeadlineExpired, match="outer"):
        with wall_timeout(0.08, "outer"), wall_timeout(5, "inner"):
            time.sleep(10)
    assert time.monotonic() - before < 1
    assert signal.getsignal(signal.SIGALRM) == previous
    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0
