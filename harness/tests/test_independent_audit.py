import importlib.util
import json
import sqlite3

import httpx
import pytest
from test_api_candidate import Endpoint

from arc_harness.api_provider import APIProvider, api_client
from arc_harness.api_run import ROOT, evaluate, files_manifest, load_plan

spec = importlib.util.spec_from_file_location("independent_checker", ROOT / "scripts/independent_audit.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def make_run(tmp_path):
    plan, _, sha = load_plan(ROOT / "plans/pilot.json")

    def factory(ledger):
        return APIProvider(ledger, client=api_client("synthetic", transport=httpx.MockTransport(Endpoint())))

    code, run, _ = evaluate(plan, ["synthetic"], sha, tmp_path, fixture=True, provider_factory=factory)
    assert code == 0
    return run


def audit(run):
    return checker.audit_run(
        run, checker.sha(ROOT / "RELEASE-MANIFEST.json"), checker.sha(run / "evidence-manifest.json")
    )


def repin(run):
    (run / "evidence-manifest.json").write_text(json.dumps({"files": files_manifest(run)}))


def test_independent_checker_accepts_reconciled_fixture_without_importing_candidate(tmp_path):
    run = make_run(tmp_path)
    report = audit(run)
    assert report["passed"], report["failures"]
    import ast

    tree = ast.parse((ROOT / "scripts/independent_audit.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0 and not node.module.startswith("arc_harness")
        if isinstance(node, ast.Import):
            assert all(not n.name.startswith("arc_harness") for n in node.names)


@pytest.mark.parametrize(
    "change",
    ["pixel", "command", "tool_args", "usage", "reported_cost", "database", "duplicate_json", "source"],
)
def test_independent_checker_rejects_semantic_tampering_after_file_rehash(tmp_path, change):
    run = make_run(tmp_path)
    events_file = run / "synthetic/events.jsonl"
    events = [json.loads(s) for s in events_file.read_text().splitlines()]
    if change in ("pixel", "command", "tool_args", "usage"):
        kind = {
            "pixel": "observation",
            "command": "action_submitted",
            "tool_args": "api_response_items",
            "usage": "api_request_completed",
        }[change]
        item = next(e["data"] for e in events if e["kind"] == kind)
        if change == "pixel":
            item["frames"][0][0][0] = (item["frames"][0][0][0] + 1) % 16
        if change == "command":
            item["action"]["name"] = "ACTION1"
        if change == "tool_args":
            call = next(o for o in item["output"] if o["type"] == "function_call")
            args = json.loads(call["arguments"])
            args["actions"][0]["name"] = "ACTION1"
            call["arguments"] = json.dumps(args)
        if change == "usage":
            item["usage"]["input_tokens"] += 1
        events_file.write_text("".join(json.dumps(e) + "\n" for e in events))
        # Also change SQLite; the independent cross-links must still detect the corruption.
        with sqlite3.connect(run / "synthetic/evidence.sqlite") as db:
            for index, e in enumerate(events, 1):
                db.execute("UPDATE events SET payload=? WHERE id=?", (json.dumps(e), index))
    elif change == "reported_cost":
        p = run / "cost-report.json"
        data = json.loads(p.read_text())
        data["requests"][0]["charge_micro_usd"] -= 1
        p.write_text(json.dumps(data))
    elif change == "database":
        with sqlite3.connect(run / "cost-ledger.sqlite") as db:
            db.execute("UPDATE requests SET charge=0 WHERE id=1")
    elif change == "duplicate_json":
        p = run / "summary.json"
        p.write_text(p.read_text().replace('"exit_code": 0', '"exit_code": 1,"exit_code": 0'))
    elif change == "source":
        p = run / "source/arc_harness/prompt.py"
        p.write_text(p.read_text() + "\n# tampered\n")
    repin(run)
    report = audit(run)
    assert not report["passed"]


def test_pinned_evidence_identity_cannot_be_replaced(tmp_path):
    run = make_run(tmp_path)
    report = checker.audit_run(run, checker.sha(ROOT / "RELEASE-MANIFEST.json"), "0" * 64)
    assert report["checks"]["externally_pinned_evidence"] is False
