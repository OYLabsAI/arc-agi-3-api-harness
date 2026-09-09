"""Hash-checked notebook bootstrap and supervised execution; stdlib only."""

from __future__ import annotations

import hashlib
import json
import math
import os
import signal
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path


class StageFailed(RuntimeError):
    def __init__(self, message, exit_code):
        super().__init__(message)
        self.exit_code = exit_code


def extract_checked(archive, digest, destination):
    archive, destination = Path(archive), Path(destination)
    if not digest or hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
        raise ValueError("Source archive hash mismatch")
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or len(names) > 1000:
            raise ValueError("Invalid source archive inventory")
        if sum(i.file_size for i in z.infolist()) > 100_000_000:
            raise ValueError("Source archive exceeds size limit")
        for i in z.infolist():
            p = Path(i.filename)
            if p.is_absolute() or ".." in p.parts or stat.S_ISLNK(i.external_attr >> 16):
                raise ValueError("Unsafe source archive path")
        if z.testzip() is not None:
            raise ValueError("Source archive CRC failed")
        destination.mkdir(parents=True, exist_ok=False)
        z.extractall(destination)
    return destination


def environment(directory, secrets=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = {"PATH": os.defpath, "HOME": str(directory), "LANG": "C.UTF-8",
           "MPLCONFIGDIR": str(directory / "matplotlib"), "PYTHONNOUSERSITE": "1",
           "PYTHON_DOTENV_DISABLED": "1", "PYTHONUNBUFFERED": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    for k, v in (secrets or {}).items():
        if k not in ("OPENAI_API_KEY", "ARC_API_KEY") or not isinstance(v, str) or not v.strip():
            raise ValueError("Only explicit nonempty evaluator API secrets are accepted")
        env[k] = v
    return env


def supervised(command, *, cwd, env, seconds, log, cleanup=180):
    if not math.isfinite(seconds) or not math.isfinite(cleanup) or not 0 < cleanup < seconds:
        raise TimeoutError("Insufficient notebook time for execution and cleanup")
    started = time.monotonic()
    deadline = started + seconds
    process = None
    record = {"status": "starting", "exit_code": None, "timed_out": False,
              "interrupted": False, "sigterm_sent": False, "sigkill_sent": False,
              "root_reaped": False, "unexpected_descendants": False}

    def terminate(sig):
        if process is None:
            return False
        try:
            os.killpg(process.pid, sig)
            return True
        except ProcessLookupError:
            return False

    def stop():
        record["sigterm_sent"] = terminate(signal.SIGTERM)
        if process is None:
            return
        try:
            process.wait(timeout=max(0, min(cleanup * 0.8, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            pass
        # A child can outlive its root; always signal the entire session's group.
        record["sigkill_sent"] = terminate(signal.SIGKILL)
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
            record["root_reaped"] = True
        except subprocess.TimeoutExpired:
            record["root_reaped"] = False

    receipt = Path(log).with_suffix(Path(log).suffix + ".supervision.json")
    receipt.write_text(json.dumps(record, indent=2) + "\n")
    with Path(log).open("w") as stream:
        try:
            process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream, stderr=stream,
                                       start_new_session=True)
            code = process.wait(timeout=max(0, deadline - cleanup - time.monotonic()))
            record["root_reaped"] = True
            # A nominally successful root must not leave worker processes running.
            record["unexpected_descendants"] = terminate(0)
            if record["unexpected_descendants"]:
                stop()
                code = code or 125
            record["status"], record["exit_code"] = "finished", code
            return code
        except subprocess.TimeoutExpired:
            record.update(status="deadline", exit_code=124, timed_out=True)
            stop()
            return 124
        except BaseException as exc:
            record.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                          exit_code=130 if isinstance(exc, KeyboardInterrupt) else 1,
                          interrupted=isinstance(exc, KeyboardInterrupt), error_type=type(exc).__name__)
            stop()
            raise
        finally:
            record["elapsed_seconds"] = time.monotonic() - started
            record["completed_within_deadline"] = record["elapsed_seconds"] <= seconds
            temp = receipt.with_suffix(receipt.suffix + ".tmp")
            temp.write_text(json.dumps(record, indent=2) + "\n")
            temp.replace(receipt)


def prepare_environment(venv, lock, *, cwd, env, started, total):
    """Install locked wheels into a fresh environment without invoking ensurepip."""
    venv, lock, cwd = Path(venv), Path(lock), Path(cwd)
    code = supervised([sys.executable, "-m", "venv", "--without-pip", str(venv)],
                      cwd=cwd, env=env, seconds=total - (time.monotonic() - started),
                      log=cwd / "setup.log")
    if code:
        raise StageFailed("Fresh environment creation failed; inspect setup.log", code)
    python = venv / "bin/python"
    # Host pip manages the isolated target; no host packages enter its runtime.
    # This avoids ensurepip, which fails in the pinned Kaggle image.
    command = [sys.executable, "-m", "pip", "--python", str(python), "install",
               "--no-input", "--only-binary=:all:", "-r", str(lock)]
    if sys.platform.startswith("linux"):
        command += ["--require-hashes"]
    code = supervised(command, cwd=cwd, env=env,
                      seconds=total - (time.monotonic() - started), log=cwd / "install.log")
    if code:
        raise StageFailed("Pinned dependency installation failed; inspect install.log", code)
    return python


def isolated_command(python, source, receipt, module, *arguments):
    return [str(python), "-I", "-S", "-B", str(source / "scripts/isolated_entry.py"),
            str(source), str(receipt), module, *map(str, arguments)]


def launch(config, secrets=None, *, started=None):
    started = time.monotonic() if started is None else started
    base = Path(config["output_root"]).resolve()
    base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="oy-api-", dir=base))
    result = {"exit_code": 1, "status": "running", "mode": config.get("mode"),
              "archive_sha256": config.get("archive_sha256"), "work_directory": str(work),
              "platform": sys.platform, "note": "A fixture execution is software validation only"}
    receipt = work / "notebook-execution.json"
    receipt.write_text(json.dumps(result, indent=2) + "\n")
    old_alarm = signal.getsignal(signal.SIGALRM)
    old_term = signal.getsignal(signal.SIGTERM)
    old_seconds, interval = signal.getitimer(signal.ITIMER_REAL)
    guard_started = time.monotonic()

    def interrupted(signum, frame):
        raise KeyboardInterrupt("bootstrap_deadline" if signum == signal.SIGALRM else "bootstrap_interrupted")

    try:
        remaining = config["max_elapsed_seconds"] - (time.monotonic() - started) - 5
        if not math.isfinite(remaining) or remaining <= 0:
            raise TimeoutError("Notebook deadline exhausted before bootstrap")
        if not old_seconds or remaining < old_seconds:
            signal.signal(signal.SIGALRM, interrupted)
            signal.setitimer(signal.ITIMER_REAL, remaining)
        signal.signal(signal.SIGTERM, interrupted)
        result.update(_launch(config, secrets, started=started, work=work))
        result["status"] = "passed" if result["exit_code"] == 0 else "failed"
        return result
    except BaseException as exc:
        result.update(exit_code=getattr(exc, "exit_code", 130 if isinstance(exc, KeyboardInterrupt) else 1),
                      status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                      error_type=type(exc).__name__)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        try:
            result["elapsed_seconds"] = time.monotonic() - started
            temp = receipt.with_suffix(".json.tmp")
            temp.write_text(json.dumps(result, indent=2) + "\n")
            temp.replace(receipt)
        finally:
            signal.signal(signal.SIGALRM, old_alarm)
            signal.signal(signal.SIGTERM, old_term)
            previous_left = old_seconds - (time.monotonic() - guard_started)
            if old_seconds and previous_left > 0:
                signal.setitimer(signal.ITIMER_REAL, previous_left, interval)


def _launch(config, secrets, *, started, work):
    if sys.version_info[:2] != (3, 12):
        raise ValueError("This frozen release requires Python 3.12; select a matching notebook runtime")
    if config["mode"] not in ("fixture", "run"):
        raise ValueError("Select fixture or run explicitly")
    env = environment(work / "empty-home")
    archive = config["source_archive"]
    if str(archive).startswith("https://"):
        destination = work / "source.zip"
        with urllib.request.urlopen(archive, timeout=60) as source, destination.open("wb") as target:
            if not source.url.startswith("https://"):
                raise ValueError("Source download redirected away from HTTPS")
            count = 0
            while chunk := source.read(65536):
                count += len(chunk)
                if count > 100_000_000 or time.monotonic() - started >= config["max_elapsed_seconds"]:
                    raise ValueError("Source download exceeded size/time budget")
                target.write(chunk)
        archive = destination
    source = extract_checked(archive, config["archive_sha256"], work / "source")
    release_sha256 = config["release_manifest_sha256"]
    if hashlib.sha256((source / "RELEASE-MANIFEST.json").read_bytes()).hexdigest() != release_sha256:
        raise ValueError("Release manifest hash mismatch")
    lock_name = "requirements-linux.lock" if sys.platform.startswith("linux") else "requirements.lock"
    lock = source / lock_name
    if hashlib.sha256(lock.read_bytes()).hexdigest() != config["lock_sha256"]:
        raise ValueError("Dependency lock hash mismatch")
    total = config["max_elapsed_seconds"]
    python = prepare_environment(work / "venv", lock, cwd=work, env=env,
                                 started=started, total=total)
    if config["mode"] == "fixture":
        code = supervised(isolated_command(python, source, work / "regression-startup.json", "pytest", "-q"),
                          cwd=source, env=env,
                          seconds=total - (time.monotonic() - started), log=work / "regression-tests.log")
        if code:
            raise StageFailed("Fixture regression checks failed; inspect regression-tests.log", code)
    plan = Path(config["plan"])
    if not plan.is_absolute():
        plan = source / plan
    document = json.loads(plan.read_text())
    if total != document["max_elapsed_seconds"]:
        raise ValueError("Notebook and run plan deadlines must match")
    if config["mode"] == "run":
        if callable(secrets):
            secrets = secrets()
        if not secrets or set(secrets) != {"OPENAI_API_KEY", "ARC_API_KEY"}:
            raise ValueError("Both evaluator-owned secrets are required")
        env = environment(work / "empty-home", secrets)
        document["approved_usd"] = config.get("approved_usd")
        document["approval_record"] = config.get("approval_record")
        document["dataset"] = str((plan.parent / document["dataset"]).resolve()) if document["dataset"] else None
        plan = work / "approved-plan.json"
        plan.write_text(json.dumps(document, indent=2) + "\n")
    else:
        if secrets:
            raise ValueError("Synthetic notebook must not receive live credentials")
    code = supervised(isolated_command(python, source, work / "execution-startup.json",
                       "arc_harness.api_run", config["mode"], "--plan", plan,
                       "--expected-release-sha256", release_sha256,
                       "--output", work / "runs", "--started-monotonic", started),
                      cwd=source, env=env, seconds=total - (time.monotonic() - started),
                      log=work / "execution.log", cleanup=document["cleanup_seconds"])
    result = {"exit_code": code, "elapsed_seconds": time.monotonic() - started,
              "mode": config["mode"], "archive_sha256": config["archive_sha256"],
              "work_directory": str(work), "platform": sys.platform,
              "note": "A fixture execution is software validation only"}
    return result
