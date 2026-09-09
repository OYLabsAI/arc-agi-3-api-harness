import copy
import json
import socket

import httpx
import pytest

from arc_harness.api_budget import BudgetStop, Ledger, usage_cost
from arc_harness.api_provider import APIProvider, api_client
from arc_harness.api_run import ROOT, evaluate, load_plan, main


def usage(i=400, o=20):
    return {"input_tokens": i, "output_tokens": o, "total_tokens": i + o,
            "input_tokens_details": {"cached_tokens": 100, "cache_write_tokens": 20},
            "output_tokens_details": {"reasoning_tokens": 10}}


class Endpoint:
    def __init__(self, *, failure=None, compact=False, changes=None):
        self.requests, self.paid, self.counts = [], 0, 0
        self.failure, self.compact, self.changes = failure, compact, changes or {}

    def __call__(self, request):
        body = json.loads(request.content) if request.content else {}
        self.requests.append((request.url.path, copy.deepcopy(body)))
        assert request.url.host == "api.openai.com"
        if request.url.path.startswith("/v1/models/"):
            if self.failure == "model":
                return httpx.Response(404, json={"error": {"message": "unavailable"}})
            return httpx.Response(200, json={"id": "gpt-6-astra", "object": "model", "created": 0,
                                              "owned_by": "test"})
        if request.url.path.endswith("/input_tokens"):
            self.counts += 1
            return httpx.Response(200, json={"object": "response.input_tokens",
                                              "input_tokens": 180000 if self.compact and self.counts < 3 else 400})
        self.paid += 1
        if self.failure == "timeout":
            raise httpx.ReadTimeout("secret-example-in-error", request=request)
        if self.failure == "auth":
            return httpx.Response(401, json={"error": {"message": "secret-example-in-error"}})
        assert not request.url.path.endswith("/compact")
        if body["input"][-1].get("type") == "compaction_trigger":
            assert body["max_output_tokens"] == 20000
            assert body["truncation"] == "disabled" and body["store"] is False
            assert body["reasoning"] == {"effort": "high", "context": "all_turns"} and body["service_tier"] == "default"
            return httpx.Response(200, json={"id": "cmp_1", "object": "response", "created_at": 0,
                "model": "gpt-6-astra", "status": "completed", "reasoning": {"effort": "high", "context": "all_turns"},
                "service_tier": "default",
                "output": [{"type": "compaction", "id": "comp_1", "encrypted_content": "opaque-compact"}],
                "usage": usage()})
        assert body["store"] is False and body["background"] is False
        assert "context_management" not in body and body["service_tier"] == "default"
        assert body["max_output_tokens"] == 16000
        assert {t["name"] for t in body["tools"]} == {
            "arc_act", "arc_inspect", "arc_history", "arc_remember", "arc_plan", "arc_stop"}
        response = {"id": f"resp_{self.paid}", "object": "response", "created_at": 0, "status": "completed",
            "model": "gpt-6-astra", "reasoning": {"effort": "high", "context": "all_turns"}, "service_tier": "default",
            "usage": usage(), "output": [
                {"type": "reasoning", "id": f"rs_{self.paid}", "summary": [], "encrypted_content": "opaque"},
                {"type": "function_call", "id": f"fc_{self.paid}", "call_id": f"call_{self.paid}",
                 "name": "arc_act", "arguments": json.dumps({"experiment": "synthetic software check",
                                                               "actions": [{"name": "ACTION4"}]})}]}
        response.update(self.changes)
        return httpx.Response(200, json=response, headers={"x-request-id": f"req_{self.paid}"})


def provider(tmp_path, endpoint=None, cap=25, **kwargs):
    endpoint = endpoint or Endpoint()
    ledger = Ledger(tmp_path / "ledger.sqlite", approved_usd=cap, max_requests=30, max_seconds=3600)
    client = api_client("synthetic-key", transport=httpx.MockTransport(endpoint))
    return APIProvider(ledger, client=client, **kwargs), ledger, endpoint


def test_usage_subsets_and_missing_cache_write():
    estimate, upper = usage_cost(usage())
    assert estimate == upper == 4150
    missing = usage()
    del missing["input_tokens_details"]["cache_write_tokens"]
    assert usage_cost(missing) == (None, 6000)
    broken = usage()
    broken["input_tokens_details"]["cached_tokens"] = 401
    with pytest.raises(ValueError):
        usage_cost(broken)


def test_cap_is_reserved_before_request(tmp_path):
    p, ledger, endpoint = provider(tmp_path, cap=1)
    with pytest.raises(BudgetStop, match="global_cost"):
        p.next({}, None, 600, None)
    assert endpoint.paid == 0
    assert ledger.report()["requests"] == []


@pytest.mark.parametrize("failure", ["timeout", "auth"])
def test_ambiguous_charge_is_retained_no_retry(tmp_path, failure):
    p, ledger, endpoint = provider(tmp_path, Endpoint(failure=failure))
    with pytest.raises(RuntimeError) as error:
        p.next({}, None, 600, None)
    assert "secret-example" not in str(error.value)
    assert endpoint.paid == 1
    assert ledger.report()["charged_or_reserved_usd"] == 24.25
    assert ledger.report()["uncertain_requests"] == 1
    with pytest.raises(BudgetStop, match="unresolved"):
        ledger.reserve("response", 200000, 16000)


@pytest.mark.parametrize("changes", [{"model": "wrong"}, {"reasoning": {"effort": "low"}},
    {"service_tier": "fast"}, {"service_tier": None}, {"status": "incomplete"}, {"usage": None}])
def test_wrong_settings_and_missing_usage_stop_before_actions(tmp_path, changes):
    p, ledger, endpoint = provider(tmp_path, Endpoint(changes=changes))
    with pytest.raises(RuntimeError):
        p.next({}, None, 600, None)
    assert endpoint.paid == 1
    assert p.pending == set()


def test_model_unavailable_is_read_only(tmp_path):
    p, ledger, endpoint = provider(tmp_path, Endpoint(failure="model"))
    with pytest.raises(RuntimeError, match="preflight"):
        p.preflight()
    assert endpoint.paid == 0 and ledger.report()["requests"] == []


def test_opaque_state_and_tool_pairing(tmp_path):
    p, ledger, endpoint = provider(tmp_path)
    call = p.next({"observation": "synthetic"}, None, 600, None).calls[0]
    with pytest.raises(RuntimeError, match="Unpaired"):
        p.next({}, None, 600, None)
    p.result(call, {"ok": True})
    with pytest.raises(RuntimeError, match="duplicate"):
        p.result(call, {})
    p.next({}, None, 600, None)
    body = endpoint.requests[-1][1]
    assert any(i.get("encrypted_content") == "opaque" for i in body["input"])
    assert any(i.get("call_id") == call.call_id and i.get("type") == "function_call_output"
               for i in body["input"])
    first = endpoint.requests[0][1]
    assert body["reasoning"]["context"] == "all_turns"
    assert body["prompt_cache_key"] == first["prompt_cache_key"]
    assert body["prompt_cache_options"]["comparison_response_id"] == "resp_1"
    assert "comparison_response_id" not in first["prompt_cache_options"]
    assert "previous_response_id" not in body


def test_effective_reasoning_context_must_match_requested_history(tmp_path):
    p, ledger, endpoint = provider(tmp_path, Endpoint(changes={
        "reasoning": {"effort": "high", "context": "current_turn"}}))
    with pytest.raises(RuntimeError):
        p.next({}, None, 600, None)
    assert endpoint.paid == 1 and not p.pending
    assert ledger.report()["requests"][0]["reasoning_context"] == "current_turn"


def test_compaction_canonical_output_and_accounting(tmp_path):
    p, ledger, endpoint = provider(tmp_path, Endpoint(compact=True))
    p.context_tokens = 180000
    reply = p.next({}, None, 600, None)
    assert reply.input_tokens == 800 and reply.output_tokens == 40
    assert [r["kind"] for r in ledger.report()["requests"]] == ["compaction", "response"]
    sent = endpoint.requests[-1][1]["input"]
    assert sent[0] == {"type": "compaction", "id": "comp_1", "encrypted_content": "opaque-compact"}
    assert json.loads(sent[1]["content"][0]["text"]) == {}


def test_current_image_and_exact_past_grids_survive_rolling_cache_boundaries(tmp_path):
    import numpy as np

    from arc_harness.perception import image_bytes

    p, ledger, endpoint = provider(tmp_path)
    path = tmp_path / "current.png"
    for n in range(6):
        path.write_bytes(image_bytes(np.array([[n]], dtype=np.uint8)))
        context = {"perception": {"width": 1, "height": 1, "rows": [format(n, "x")]}}
        call = p.next(context, path, 600, None).calls[0]
        p.result(call, {"synthetic": True})
        body = endpoint.requests[-1][1]
        image_blocks = [c for i in body["input"] if isinstance(i.get("content"), list)
                        for c in i["content"] if c["type"] == "input_image"]
        assert len(image_blocks) == 1
        assert image_blocks[0]["detail"] == "original"
        import base64

        assert base64.b64decode(image_blocks[0]["image_url"].split(",", 1)[1]) == path.read_bytes()
        texts = [c for i in body["input"] if isinstance(i.get("content"), list)
                 for c in i["content"] if c["type"] == "input_text"]
        assert [json.loads(c["text"])["perception"]["rows"] for c in texts] == [[format(j, "x")] for j in range(n + 1)]
        assert sum("prompt_cache_breakpoint" in c for c in texts) == min(n + 1, 4)
        assert body["prompt_cache_options"]["mode"] == "explicit"
        assert all("prompt_cache_breakpoint" not in c and c["type"] != "input_image"
                   for i in p.items if isinstance(i.get("content"), list) for c in i["content"])


@pytest.mark.parametrize("perception", [{}, {"width": 1, "height": 2, "rows": ["0"]},
                                      {"width": 1, "height": 1, "rows": ["z"]}])
def test_screenshot_without_complete_exact_grid_is_rejected_before_billing(tmp_path, perception):
    p, ledger, endpoint = provider(tmp_path)
    with pytest.raises(ValueError, match="complete exact pixel grid"):
        p.next({"perception": perception}, tmp_path / "unused.png", 600, None)
    assert not endpoint.paid and not ledger.report()["requests"]


def test_deadline_and_request_count_are_global(tmp_path):
    now = [0]
    ledger = Ledger(tmp_path / "cost.sqlite", approved_usd=25, max_requests=1, max_seconds=1000,
                    clock=lambda: now[0])
    request = ledger.reserve("response", 1000, 100)
    ledger.settle(request, usage(), {})
    with pytest.raises(BudgetStop, match="request_limit"):
        ledger.reserve("response", 1000, 100)
    now[0] = 900
    with pytest.raises(BudgetStop, match="deadline"):
        ledger.check_time()


def test_pending_reservation_survives_process_loss(tmp_path):
    import sqlite3

    ledger = Ledger(tmp_path / "cost.sqlite", approved_usd=25, max_requests=2, max_seconds=3600)
    ledger.reserve("response", 200000, 16000)
    ledger.close()
    with sqlite3.connect(tmp_path / "cost.sqlite") as db:
        assert db.execute("SELECT charge,status FROM requests").fetchone() == (6200000, "pending")
    with pytest.raises(sqlite3.OperationalError):
        Ledger(tmp_path / "cost.sqlite", approved_usd=25, max_requests=2, max_seconds=3600)


def test_missing_credentials_and_budget_prevent_launch(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ARC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        api_client()
    assert main(["run", "--output", str(tmp_path / "runs")]) == 2
    assert not (tmp_path / "runs").exists()


def test_fixture_has_no_network(tmp_path, monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("Unexpected network")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    assert main(["fixture", "--output", str(tmp_path)]) == 0
    summary = json.loads(next(tmp_path.glob("*/summary.json")).read_text())
    assert summary["fixture"] and summary["games_won"] == 1
    assert summary["cost"]["charged_or_reserved_usd"] == 0


def test_replacement_ids_never_enter_solver_and_every_game_runs(tmp_path):
    plan, _, sha = load_plan(ROOT / "plans/pilot.json")
    games = ["unfamiliar-a91", "unfamiliar-z02"]
    endpoints = []

    def factory(ledger):
        endpoint = Endpoint()
        endpoints.append(endpoint)
        return APIProvider(ledger, client=api_client("synthetic-key", transport=httpx.MockTransport(endpoint)))

    code, directory, summary = evaluate(plan, games, sha, tmp_path, fixture=True, provider_factory=factory)
    assert code == 0 and summary["games_won"] == 2
    assert len(endpoints) == 2 and all(e.paid == 5 for e in endpoints)
    for endpoint in endpoints:
        payload = json.dumps(endpoint.requests)
        assert all(game not in payload for game in games)
        assert "OY Labs" not in payload and "scorecard" not in payload
    assert len(json.loads((directory / "cost-report.json").read_text())["requests"]) == 10


def test_organizer_selection_contract_no_public_fallback(tmp_path):
    plan = json.loads((ROOT / "plans/organizer.json").read_text())
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="dataset"):
        load_plan(path)
    plan["dataset"] = "assigned.json"
    path.write_text(json.dumps(plan))
    (tmp_path / "assigned.json").write_text(json.dumps({"schema_version": 1,
        "interface": "arc-sdk-remote-ids", "games": ["unfamiliar-new"]}))
    assert load_plan(path)[1] == ["unfamiliar-new"]
    with pytest.raises(ValueError, match="disabled pending ARC"):
        load_plan(path, paid=True)


def test_paid_plan_with_cap_accepts_only_explicit_secrets(tmp_path, monkeypatch):
    # This test isolates plan/credential validation; the frozen billing gate has its own tests.
    monkeypatch.setattr("arc_harness.api_run.require_billing_review", lambda: None)
    plan = json.loads((ROOT / "plans/pilot.json").read_text())
    plan.update(approved_usd=25, approval_record="synthetic test authorization",
                dataset=str(ROOT / "plans/pilot-games.json"))
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key")
    monkeypatch.setenv("ARC_API_KEY", "synthetic-arc")
    assert load_plan(path, paid=True)[0]["approved_usd"] == 25


def test_uncertain_action_is_not_retried_and_remaining_games_are_preserved(tmp_path, monkeypatch):
    from arc_harness import api_run
    from arc_harness.fixtures import CorridorFixture

    effects = []

    class Ambiguous(CorridorFixture):
        def step(self, action, experiment):
            effects.append(action.name)
            raise TimeoutError("uncertain action")

    monkeypatch.setattr(api_run, "CorridorFixture", Ambiguous)
    plan, _, sha = load_plan(ROOT / "plans/pilot.json")
    code, directory, summary = evaluate(plan, ["unfamiliar-1", "unfamiliar-2"], sha, tmp_path, fixture=True)
    assert code == 1 and effects == ["ACTION4"]
    assert summary["unrun_games"] == ["unfamiliar-2"]
    audit = json.loads((directory / "exports/audit.json").read_text())
    assert audit["games"][0]["checks"]["no_ambiguous_action"] is False


def test_api_tags_and_single_card_routing(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from arc_harness.attribution import NamedArcadeSession

    creates, routes = [], []

    class FakeArc:
        arc_base_url = "https://three.arcprize.org"

        def create_scorecard(self, **kwargs):
            creates.append(kwargs)
            return "card-synthetic"

        def make(self, game_id, scorecard_id):
            routes.append((game_id, scorecard_id))
            return SimpleNamespace()

    def initialize(self, *args):
        self.arc, self.mode, self.started = FakeArc(), "competition", set()

    monkeypatch.setattr("arc_harness.attribution.ArcadeSession.__init__", initialize)
    session = NamedArcadeSession("competition", tmp_path, tmp_path,
                                 attribution={"harness_name": "OY1 AGI", "team_name": "OY Labs",
                                              "provider": "openai-responses", "evaluation_scope": "pilot"})
    session.make("one")
    session.make("two")
    assert len(creates) == 1
    assert creates[0]["tags"] == ["OY1 AGI", "OY Labs", "pilot", "openai-responses"]
    assert routes == [("one", "card-synthetic"), ("two", "card-synthetic")]
    assert session.snapshot() is None


def test_bootstrap_rejects_bad_hash_traversal_and_inherited_credentials(tmp_path):
    import hashlib
    import importlib.util
    import zipfile

    spec = importlib.util.spec_from_file_location("bootstrap", ROOT / "scripts/bootstrap.py")
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("../escape.txt", "test")
    with pytest.raises(ValueError, match="hash"):
        bootstrap.extract_checked(archive, "bad", tmp_path / "extract")
    with pytest.raises(ValueError, match="Unsafe"):
        bootstrap.extract_checked(archive, hashlib.sha256(archive.read_bytes()).hexdigest(), tmp_path / "extract")
    env = bootstrap.environment(tmp_path / "home")
    assert "OPENAI_API_KEY" not in env and "ARC_API_KEY" not in env and "CODEX_HOME" not in env
    assert env["HOME"] == str(tmp_path / "home")
