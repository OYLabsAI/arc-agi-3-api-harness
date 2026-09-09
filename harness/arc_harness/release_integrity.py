"""Whole-release file checks against an externally pinned manifest identity."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path, PurePosixPath

MANIFEST = "RELEASE-MANIFEST.json"
IGNORED_DIRECTORIES = {"__pycache__", ".pytest_cache", ".ruff_cache", ".git", ".venv"}


class ReleaseIntegrityError(RuntimeError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    """Exclude only named local tooling directories; outputs must live elsewhere."""
    root = Path(root)
    files = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            if (Path(directory) / name).is_symlink():
                raise ReleaseIntegrityError("Release contains a symlink")
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRECTORIES)
        for name in sorted(names):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if relative == MANIFEST:
                continue
            if not path.is_file():
                raise ReleaseIntegrityError("Release contains a non-regular file")
            data = path.read_bytes()
            files.append({"path": relative, "bytes": len(data), "sha256": digest(data)})
    return sorted(files, key=lambda item: item["path"])


def verify_release(root, expected_sha256=None):
    root = Path(root)
    manifest_path = root / MANIFEST
    if root.is_symlink() or manifest_path.is_symlink():
        raise ReleaseIntegrityError("Release or manifest is a symlink")
    try:
        raw = manifest_path.read_bytes()
        identity = digest(raw)
        if expected_sha256 is not None and identity != expected_sha256:
            raise ReleaseIntegrityError("Release manifest identity changed")
        manifest = json.loads(raw)
        entries = manifest["files"]
        if not isinstance(entries, list) or not entries:
            raise ReleaseIntegrityError("Release inventory is empty or invalid")
        seen = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"path", "bytes", "sha256"}:
                raise ReleaseIntegrityError("Invalid release entry")
            name = entry["path"]
            if not isinstance(name, str) or not name or "\\" in name:
                raise ReleaseIntegrityError("Invalid release path")
            path = PurePosixPath(name)
            if (path.is_absolute() or path.as_posix() != name or ".." in path.parts
                    or name == MANIFEST or any(p in IGNORED_DIRECTORIES for p in path.parts)
                    or name in seen):
                raise ReleaseIntegrityError("Unsafe or duplicate release path")
            seen.add(name)
            if (type(entry["bytes"]) is not int or entry["bytes"] < 0
                    or not isinstance(entry["sha256"], str)
                    or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])):
                raise ReleaseIntegrityError("Invalid release hash or size")
        if inventory(root) != sorted(entries, key=lambda item: item["path"]):
            raise ReleaseIntegrityError("Release file inventory or content changed")
        # Also reject replacement of the manifest while the tree was being read.
        if manifest_path.read_bytes() != raw:
            raise ReleaseIntegrityError("Release manifest changed during verification")
        return {"manifest_sha256": identity, "files": entries, "version": manifest["version"]}
    except ReleaseIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ReleaseIntegrityError(f"Release verification failed ({type(exc).__name__})") from None


def snapshot_release(root, destination, expected_sha256):
    root, destination = Path(root), Path(destination)
    verified = verify_release(root, expected_sha256)
    if destination.resolve().is_relative_to(root.resolve()):
        raise ReleaseIntegrityError("Evidence must be outside the release")
    destination.mkdir(parents=True, exist_ok=False)
    for name in [MANIFEST] + [entry["path"] for entry in verified["files"]]:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    verify_release(root, expected_sha256)
    verify_release(destination, expected_sha256)
    return verified
