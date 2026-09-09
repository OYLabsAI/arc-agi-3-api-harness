"""Launch only reviewed source and venv packages, without automatic site startup.

Run with the target venv interpreter and -I -S -B. Python 3.12 normally establishes
venv prefixes in site.py; set those prefixes explicitly without importing site.
This is process-startup isolation, not a security boundary against the host OS.
"""

from __future__ import annotations

import hashlib
import json
import runpy
import sys
import sysconfig
from pathlib import Path


def configure(source):
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Isolated entry requires Python 3.12")
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise RuntimeError("Isolated entry requires -I -S -B")
    if any(name in sys.modules for name in ("site", "sitecustomize", "usercustomize")):
        raise RuntimeError("Automatic site initialization already occurred")
    source = Path(source).resolve(strict=True)
    # Resolve the directory, not the python symlink that points at the base binary.
    venv = Path(sys.executable).absolute().parent.parent.resolve(strict=True)
    config = dict(line.split("=", 1) for line in (venv / "pyvenv.cfg").read_text().splitlines()
                  if "=" in line)
    config = {key.strip(): value.strip() for key, value in config.items()}
    if config.get("include-system-site-packages", "").lower() != "false":
        raise RuntimeError("Fresh venv must exclude system site packages")
    site_packages = venv / "lib/python3.12/site-packages"
    if not site_packages.is_dir() or site_packages.is_symlink():
        raise RuntimeError("Expected a real venv site-packages directory")
    stdlib = Path(sysconfig.get_path("stdlib")).resolve(strict=True)
    expected_paths = {stdlib, stdlib / "lib-dynload", stdlib.parent / "python312.zip"}
    initial_paths = [Path(path).resolve() for path in sys.path]
    if not initial_paths or any(path not in expected_paths for path in initial_paths):
        raise RuntimeError("Unexpected base interpreter import path")
    # Record hook files without importing or evaluating any of them.
    hooks = []
    for directory in [*initial_paths, site_packages, source]:
        if not directory.is_dir():
            continue
        for name in ("sitecustomize.py", "usercustomize.py"):
            path = directory / name
            if path.is_file():
                hooks.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                              "executed": False})
    pth = [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "executed": False}
           for path in sorted(site_packages.glob("*.pth"))]
    # Keep stdlib first; neither working-directory modules nor packages may shadow it.
    sys.prefix = sys.exec_prefix = str(venv)
    sys.path[:] = [str(path) for path in initial_paths] + [str(site_packages), str(source)]
    return {"python": sys.version, "executable": sys.executable,
            "executable_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
            "prefix": sys.prefix, "base_prefix": sys.base_prefix,
            "sys_path": list(sys.path), "isolated": True, "automatic_site_initialization": False,
            "startup_hooks_not_executed": hooks, "pth_files_not_executed": pth,
            "scope": "interpreter startup and explicit import paths; full runtime compliance NOT SATISFIED"}


def main():
    source, receipt, module, *arguments = sys.argv[1:]
    record = configure(source)
    receipt = Path(receipt)
    receipt.write_text(json.dumps(record, indent=2) + "\n")
    if module == "--probe":
        print(json.dumps(record, sort_keys=True))
        return
    if module not in {"pytest", "arc_harness.api_run"}:
        raise RuntimeError("Entry module is not allowlisted")
    sys.argv = [module, *arguments]
    runpy.run_module(module, run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
