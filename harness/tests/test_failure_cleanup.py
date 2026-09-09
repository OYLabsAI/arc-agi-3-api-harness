import importlib.util
import json
import signal
import sys
import time
from pathlib import Path

import pytest

from arc_harness import api_run
from arc_harness.fixtures import CorridorFixture, demo_provider
from arc_harness.runner import Runner
from arc_harness.types import Limits

spec = importlib.util.spec_from_file_location("bootstrap", api_run.ROOT / "scripts/bootstrap.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_supervisor_kills_termination_resistant_process_within_budget(tmp_path):
    script = "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(20)"
    started = time.monotonic()
    code = bootstrap.supervised([sys.executable, "-c", script], cwd=tmp_path,
                                env=bootstrap.environment(tmp_path / "home"), seconds=0.6,
                                cleanup=0.2, log=tmp_path / "worker.log")
    assert code == 124 and time.monotonic() - started < 1.5
    receipt = json.loads((tmp_path / "worker.log.supervision.json").read_text())
    assert receipt["timed_out"] and receipt["sigkill_sent"] and receipt["root_reaped"]


def test_supervisor_removes_child_left_by_successful_parent(tmp_path):
    script = """import os,signal,time
from pathlib import Path
if os.fork() == 0:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True:
        Path('heartbeat').write_text(str(time.monotonic()))
        time.sleep(0.01)
else:
    time.sleep(0.08)
"""
    code = bootstrap.supervised([sys.executable, "-c", script], cwd=tmp_path,
                                env=bootstrap.environment(tmp_path / "home"), seconds=1,
                                cleanup=0.3, log=tmp_path / "worker.log")
    assert code == 125
    receipt = json.loads((tmp_path / "worker.log.supervision.json").read_text())
    assert receipt["unexpected_descendants"] and receipt["sigkill_sent"]
    time.sleep(0.04)
    heartbeat = (tmp_path / "heartbeat").read_text()
    time.sleep(0.06)
    assert (tmp_path / "heartbeat").read_text() == heartbeat


@pytest.mark.parametrize("failure", [ValueError, KeyboardInterrupt])
def test_bootstrap_failure_receipt_and_signal_restoration(tmp_path, monkeypatch, failure):
    def failed(*a, **kw):
        raise failure("private error text must not enter receipt")

    monkeypatch.setattr(bootstrap, "_launch", failed)
    before = signal.getsignal(signal.SIGALRM), signal.getsignal(signal.SIGTERM)
    with pytest.raises(failure):
        bootstrap.launch({"output_root": str(tmp_path), "mode": "fixture", "max_elapsed_seconds": 100})
    receipt = json.loads(next(tmp_path.glob("*/notebook-execution.json")).read_text())
    assert receipt["exit_code"] != 0 and receipt["error_type"] == failure.__name__
    assert "private error" not in json.dumps(receipt)
    assert (signal.getsignal(signal.SIGALRM), signal.getsignal(signal.SIGTERM)) == before
    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0


@pytest.mark.parametrize("phase", ["finalize", "stats", "close"])
def test_provider_cleanup_failure_still_writes_failed_game_and_closes_store(tmp_path, phase):
    provider = demo_provider()
    closed = []

    def failed():
        raise RuntimeError("private-error")

    provider.close = lambda: closed.append(True)
    setattr(provider, phase, failed)
    runner = Runner(CorridorFixture(), provider, tmp_path / "game", Limits())
    result = runner.run()
    assert result["status"] == "error"
    assert result["finalization_errors"] == [{"phase": phase, "error_type": "RuntimeError"}]
    assert json.loads((tmp_path / "game/result.json").read_text())["status"] == "error"
    assert runner.store.log.closed
    if phase != "close":
        assert closed == [True]


def test_failed_final_export_restores_signals_closes_ledger_and_invalidates_success(tmp_path, monkeypatch):
    real_write = api_run.write_json
    instances = []
    original_ledger = api_run.Ledger

    def ledger(*a, **kw):
        result = original_ledger(*a, **kw)
        instances.append(result)
        return result

    def failed(path, data):
        if Path(path).name == "evidence-manifest.json":
            raise OSError("synthetic disk failure")
        real_write(path, data)

    monkeypatch.setattr(api_run, "write_json", failed)
    monkeypatch.setattr(api_run, "Ledger", ledger)
    before = signal.getsignal(signal.SIGALRM), signal.getsignal(signal.SIGTERM)
    plan, games, sha = api_run.load_plan(api_run.ROOT / "plans/pilot.json")
    with pytest.raises(OSError):
        api_run.evaluate(plan, games, sha, tmp_path / "runs", fixture=True)
    summary = json.loads(next((tmp_path / "runs").glob("*/summary.json")).read_text())
    assert summary["exit_code"] == 1 and summary["complete_selected_set"] is False
    assert summary["finalization_status"] == "failed"
    assert (signal.getsignal(signal.SIGALRM), signal.getsignal(signal.SIGTERM)) == before
    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0
    import sqlite3

    with pytest.raises(sqlite3.ProgrammingError):
        instances[0].db.execute("SELECT 1")


def test_unresolved_billing_blocks_paid_launch_before_network_or_run_directory(tmp_path, monkeypatch):
    original_review = api_run.require_billing_review
    monkeypatch.setattr(api_run, "require_billing_review", lambda: original_review({"status": "NOT SATISFIED"}))
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key")
    monkeypatch.setenv("ARC_API_KEY", "synthetic-arc")
    plan, games, sha = api_run.load_plan(api_run.ROOT / "plans/pilot.json")
    plan.update(approved_usd=25, approval_record="synthetic approval",
                dataset=str(api_run.ROOT / "plans/pilot-games.json"))
    path = tmp_path / "approved.json"
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="billing review NOT SATISFIED"):
        api_run.load_plan(path, paid=True)
    with pytest.raises(ValueError, match="billing review NOT SATISFIED"):
        api_run.evaluate(plan, games, sha, tmp_path / "runs", expected_release_sha256="synthetic")
    assert not (tmp_path / "runs").exists()
