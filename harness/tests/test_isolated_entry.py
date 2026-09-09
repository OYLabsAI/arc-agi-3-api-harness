"""Real-process checks for interpreter startup isolation."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ENTRY = Path(__file__).resolve().parents[1] / "scripts/isolated_entry.py"


@pytest.fixture
def isolated_venv(tmp_path):
    target = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(target)], check=True)
    return target


def test_startup_hooks_pth_and_environment_cannot_execute(isolated_venv, tmp_path):
    target = isolated_venv
    packages = target / "lib/python3.12/site-packages"
    marker = tmp_path / "hook-executed"
    payload = f"from pathlib import Path; Path({str(marker)!r}).write_text('executed')\n"
    (packages / "sitecustomize.py").write_text(payload)
    (packages / "usercustomize.py").write_text(payload)
    (packages / "injected.pth").write_text("import pathlib; "
        f"pathlib.Path({str(marker)!r}).write_text('pth executed')\n")
    source = tmp_path / "source"
    source.mkdir()
    (source / "sitecustomize.py").write_text(payload)
    receipt = tmp_path / "startup.json"
    result = subprocess.run([str(target / "bin/python"), "-I", "-S", "-B", str(ENTRY),
                             str(source), str(receipt), "--probe"],
                            cwd=source, env={"PYTHONPATH": str(source), "PYTHONSTARTUP": str(source / "sitecustomize.py")},
                            capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    assert not marker.exists()
    assert result.stderr == ""
    assert data["prefix"] == str(target)
    assert data["automatic_site_initialization"] is False
    assert len(data["startup_hooks_not_executed"]) >= 3
    assert len(data["pth_files_not_executed"]) == 1
    assert data["sys_path"][-2:] == [str(packages), str(source)]
    assert json.loads(receipt.read_text()) == data


@pytest.mark.parametrize("flags", [[], ["-I"], ["-I", "-S"]])
def test_required_interpreter_flags_cannot_be_omitted(isolated_venv, tmp_path, flags):
    receipt = tmp_path / "must-not-exist.json"
    result = subprocess.run([str(isolated_venv / "bin/python"), *flags, str(ENTRY),
                             str(tmp_path), str(receipt), "--probe"], capture_output=True, text=True)
    assert result.returncode != 0
    assert "requires -I -S -B" in result.stderr
    assert not receipt.exists()


def test_system_site_packages_is_rejected(isolated_venv, tmp_path):
    config = isolated_venv / "pyvenv.cfg"
    config.write_text(config.read_text().replace("include-system-site-packages = false",
                                                "include-system-site-packages = true"))
    receipt = tmp_path / "must-not-exist.json"
    result = subprocess.run([str(isolated_venv / "bin/python"), "-I", "-S", "-B", str(ENTRY),
                             str(tmp_path), str(receipt), "--probe"], capture_output=True, text=True)
    assert result.returncode != 0
    assert "exclude system site packages" in result.stderr
    assert not receipt.exists()
