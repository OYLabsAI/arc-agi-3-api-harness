import hashlib
import json

import httpx
import pytest

from arc_harness import api_run
from arc_harness.api_budget import Ledger
from arc_harness.api_provider import APIProvider, api_client
from arc_harness.fixtures import CorridorFixture, demo_provider
from arc_harness.release_integrity import (
    MANIFEST,
    ReleaseIntegrityError,
    inventory,
    snapshot_release,
    verify_release,
)


def seal(root):
    data = json.dumps({"version": "test", "files": inventory(root)}, indent=2).encode()
    (root / MANIFEST).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def release(tmp_path):
    root = tmp_path / "release"
    for name in ("arc_harness/prompt.py", "plans/pilot.json", "requirements-linux.lock",
                 "scripts/bootstrap.py", "notebook.ipynb", "README.md"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic release input\n")
    return root, seal(root)


@pytest.mark.parametrize("name", ["arc_harness/prompt.py", "plans/pilot.json", "requirements-linux.lock",
                                  "scripts/bootstrap.py", "notebook.ipynb", "README.md"])
def test_content_drift_across_every_release_component(release, name):
    root, identity = release
    (root / name).write_text("modified")
    with pytest.raises(ReleaseIntegrityError, match="content changed"):
        verify_release(root, identity)


def test_updating_file_and_manifest_cannot_rebase_active_attempt(release):
    root, identity = release
    (root / "plans/pilot.json").write_text("modified")
    seal(root)
    with pytest.raises(ReleaseIntegrityError, match="identity changed"):
        verify_release(root, identity)


@pytest.mark.parametrize("change", ["extra", "missing", "file_symlink", "directory_symlink"])
def test_inventory_changes_fail(release, tmp_path, change):
    root, identity = release
    target = root / "README.md"
    if change == "extra":
        (root / "injected.py").write_text("extra")
    elif change == "missing":
        target.unlink()
    elif change == "file_symlink":
        target.unlink()
        target.symlink_to(root / "requirements-linux.lock")
    else:
        (root / "linked").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ReleaseIntegrityError):
        verify_release(root, identity)


@pytest.mark.parametrize("path", ["../escape", "/absolute", "plans/../escape", "plans//pilot.json",
                                  "./README.md", "plans\\pilot.json", MANIFEST])
def test_unsafe_manifest_paths_rejected(release, path):
    root, _ = release
    data = json.loads((root / MANIFEST).read_text())
    data["files"][0]["path"] = path
    (root / MANIFEST).write_text(json.dumps(data))
    with pytest.raises(ReleaseIntegrityError):
        verify_release(root)


def test_duplicate_entries_rejected(release):
    root, _ = release
    data = json.loads((root / MANIFEST).read_text())
    data["files"].append(data["files"][0])
    (root / MANIFEST).write_text(json.dumps(data))
    with pytest.raises(ReleaseIntegrityError, match="duplicate"):
        verify_release(root)


def test_snapshot_includes_all_files_and_stays_frozen(release, tmp_path):
    root, identity = release
    snapshot = tmp_path / "evidence/source"
    snapshot_release(root, snapshot, identity)
    assert verify_release(snapshot, identity)["files"] == inventory(root)
    (root / "scripts/bootstrap.py").write_text("later edit")
    assert verify_release(snapshot, identity)["manifest_sha256"] == identity


def test_outputs_inside_release_rejected_before_creation(release):
    root, identity = release
    with pytest.raises(ReleaseIntegrityError, match="outside"):
        snapshot_release(root, root / "evidence", identity)
    assert not (root / "evidence").exists()


def test_file_change_after_compaction_blocks_next_inference_and_reservation(release, tmp_path):
    from test_api_candidate import Endpoint

    root, identity = release
    requests = []
    response_endpoint = Endpoint(compact=True)

    def endpoint(request):
        requests.append(request.url.path)
        result = response_endpoint(request)
        (root / "plans/pilot.json").write_text("modified after compaction")
        return result

    ledger = Ledger(tmp_path / "ledger.sqlite", approved_usd=25, max_requests=5, max_seconds=3600)
    provider = APIProvider(ledger, integrity_check=lambda: verify_release(root, identity),
                           client=api_client("synthetic-key", transport=httpx.MockTransport(endpoint)))
    provider.context_tokens = 180000
    try:
        with pytest.raises(ReleaseIntegrityError):
            provider.next({}, None, 600, None)
        assert requests == ["/v1/responses"]
        assert len(ledger.report()["requests"]) == 1
        assert ledger.report()["requests"][0]["status"] == "accounted"
    finally:
        provider.close()
        ledger.close()


@pytest.mark.parametrize("when", ["model_reply", "last_action"])
def test_in_game_drift_cannot_produce_success(tmp_path, monkeypatch, when):
    frozen = verify_release(api_run.ROOT)
    copied = tmp_path / "candidate"
    snapshot_release(api_run.ROOT, copied, frozen["manifest_sha256"])
    monkeypatch.setattr(api_run, "ROOT", copied)
    plan, games, dataset_sha = api_run.load_plan(copied / "plans/pilot.json")

    def mutate():
        (copied / "requirements-linux.lock").write_text("modified during game")

    def factory(ledger):
        provider = demo_provider()
        original = provider.next

        def next_reply(*args, **kwargs):
            reply = original(*args, **kwargs)
            if when == "model_reply":
                mutate()
            return reply

        provider.next = next_reply
        return provider

    class FinalActionMutation(CorridorFixture):
        def step(self, action, experiment):
            observation = super().step(action, experiment)
            if observation.state == "WIN" and when == "last_action":
                mutate()
            return observation

    monkeypatch.setattr(api_run, "CorridorFixture", FinalActionMutation)
    code, directory, summary = api_run.evaluate(plan, games, dataset_sha, tmp_path / "runs", fixture=True,
                                               provider_factory=factory)
    assert code == 1 and not summary["complete_selected_set"]
    assert summary["release_integrity_status"] == "NOT SATISFIED"
    assert summary["actions_submitted"] == (0 if when == "model_reply" else 5)
    assert verify_release(directory / "source", frozen["manifest_sha256"])


def test_paid_run_requires_independently_supplied_identity(tmp_path):
    plan, games, dataset_sha = api_run.load_plan(api_run.ROOT / "plans/pilot.json")
    with pytest.raises(ValueError, match="reviewed release"):
        api_run.evaluate(plan, games, dataset_sha, tmp_path / "runs")
    assert not (tmp_path / "runs").exists()
