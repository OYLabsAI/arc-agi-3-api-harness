import json
import sqlite3

import httpx
import pytest
from test_api_candidate import Endpoint, provider, usage

from arc_harness.api_budget import BudgetStop, Ledger
from arc_harness.api_provider import APIProvider, api_client


def test_no_counting_endpoint_and_full_input_reservation_before_dispatch(tmp_path):
    endpoint = Endpoint()
    ledger = Ledger(tmp_path / "cost.sqlite", approved_usd=25, max_requests=10, max_seconds=3600)

    def inspect(request):
        assert request.url.path == "/v1/responses"
        with sqlite3.connect(tmp_path / "cost.sqlite") as db:
            reserved, status, detail = db.execute("SELECT reserved,status,detail FROM requests").fetchone()
        assert status == "pending" and reserved == 24250000
        assert json.loads(detail)["input_bound"] == 922000
        return endpoint(request)

    p = APIProvider(ledger, client=api_client("synthetic", transport=httpx.MockTransport(inspect)))
    p.next({}, None, 600, None)
    report = ledger.report()
    assert report["dispatched_operations"] == 1
    assert report["input_count_operations"] == [] and report["cost_coverage_complete"] is True
    assert endpoint.counts == 0


def test_smaller_unproven_input_reservation_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="full documented"):
        provider(tmp_path, max_input_tokens=200000)


def test_compaction_uses_previous_observed_context_without_counting(tmp_path):
    p, ledger, endpoint = provider(tmp_path, Endpoint(compact=True))
    p.context_tokens = 180000
    p.next({}, None, 600, None)
    path, body = endpoint.requests[0]
    assert path == "/v1/responses" and body["input"][-1] == {"type": "compaction_trigger"}
    assert ledger.report()["requests"][0]["reservation_micro_usd"] == 24550000
    assert ledger.report()["dispatched_operations"] == 2 and endpoint.counts == 0


def test_uncertain_request_prevents_any_new_provider_traffic(tmp_path):
    p, ledger, endpoint = provider(tmp_path, Endpoint(failure="timeout"))
    with pytest.raises(RuntimeError):
        p.next({}, None, 600, None)
    with pytest.raises(BudgetStop, match="unresolved"):
        p.next({}, None, 600, None)
    assert endpoint.paid == 1 and endpoint.counts == 0


@pytest.mark.parametrize(
    "mutation",
    [
        {"status": "incomplete"},
        {"model": "other"},
        {"service_tier": "fast"},
        {"reasoning": {"effort": "low"}},
        {"output": []},
        {
            "output": [
                {"type": "function_call", "call_id": "bad", "id": "bad", "name": "arc_act", "arguments": "{}"}
            ]
        },
        {"usage": {**usage(o=20001), "output_tokens": 20001}},
    ],
)
def test_invalid_compaction_cannot_continue_or_execute_actions(tmp_path, mutation):
    endpoint = Endpoint(compact=True)

    def changed(request):
        response = endpoint(request)
        if request.url.path == "/v1/responses":
            body = response.json()
            body.update(mutation)
            return httpx.Response(200, json=body)
        return response

    p, ledger, _ = provider(tmp_path)
    p.context_tokens = 180000
    p.client.close()
    p.client = api_client("synthetic", transport=httpx.MockTransport(changed))
    with pytest.raises(RuntimeError):
        p.next({}, None, 600, None)
    assert endpoint.paid == 1 and not p.pending
    assert not any(i.get("encrypted_content") == "opaque-compact" for i in p.items)
