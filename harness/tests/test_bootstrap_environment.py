"""Exercise pip-less environment setup with a local, hash-locked wheel."""

import hashlib
import importlib.util
import json
import subprocess
import time
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bootstrap", ROOT / "scripts/bootstrap.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


@pytest.mark.parametrize("corrupt_hash", [False, True])
def test_pipless_environment_isolated_and_hash_enforced(tmp_path, corrupt_hash):
    wheel = tmp_path / "fixture_probe-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as z:
        z.writestr("fixture_probe.py", "VALUE = 'fresh-environment'\n")
        z.writestr("fixture_probe-1.0.dist-info/METADATA",
                   "Metadata-Version: 2.1\nName: fixture-probe\nVersion: 1.0\n")
        z.writestr("fixture_probe-1.0.dist-info/WHEEL",
                   "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        z.writestr("fixture_probe-1.0.dist-info/RECORD", "")
    digest = "0" * 64 if corrupt_hash else hashlib.sha256(wheel.read_bytes()).hexdigest()
    lock = tmp_path / "requirements.lock"
    lock.write_text(f"fixture-probe @ {wheel.as_uri()} --hash=sha256:{digest}\n")
    env = bootstrap.environment(tmp_path / "empty-home")
    kwargs = dict(cwd=tmp_path, env=env, started=time.monotonic(), total=300)
    if corrupt_hash:
        with pytest.raises(RuntimeError, match="Pinned dependency"):
            bootstrap.prepare_environment(tmp_path / "venv", lock, **kwargs)
        assert "DO NOT MATCH THE HASHES" in (tmp_path / "install.log").read_text()
        return
    python = bootstrap.prepare_environment(tmp_path / "venv", lock, **kwargs)
    probe = subprocess.run([str(python), "-c",
                            "import fixture_probe, importlib.util, json, sys; "
                            "print(json.dumps({'value': fixture_probe.VALUE, "
                            "'isolated': sys.prefix != sys.base_prefix, "
                            "'pip': importlib.util.find_spec('pip') is not None, "
                            "'pytest': importlib.util.find_spec('pytest') is not None}))"],
                           cwd=tmp_path, env=env, capture_output=True, text=True, check=True)
    assert json.loads(probe.stdout) == {"value": "fresh-environment", "isolated": True,
                                      "pip": False, "pytest": False}
