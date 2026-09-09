"""Verify the review package without installing or executing the harness.

Copyright 2026 Orca Labs sp. z o.o. Licensed under Apache-2.0.
"""

import ast
import hashlib
import io
import json
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = "84a784778cf0a2b01d5f93380445b050b4bbee56fbb865d6e8bf4ebd9cde1053"
ARCHIVE_SHA256 = "53cc83d5680ff47633d00f2f4f6ace8d9b10e1484779a810faad5247bcd5d009"
BUNDLE_SHA256 = "be904f8b6e72cea0ca469d9bee1697f2fa5927fce8145a345546bc772f687f7d"


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def checked_file(root, name):
    path = PurePosixPath(name)
    check(not path.is_absolute() and ".." not in path.parts and "\\" not in name, "Unsafe manifest path")
    file = root / name
    check(file.resolve().is_relative_to(root.resolve()), "Path escapes package")
    check(file.is_file() and not file.is_symlink(), f"Missing or linked file: {name}")
    return file


def verify(root=ROOT):
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    records = manifest["files"]
    names = [row["path"] for row in records]
    check(len(names) == len(set(names)), "Duplicate manifest paths")
    actual = set()
    for file in root.rglob("*"):
        relative = file.relative_to(root)
        if ".git" in relative.parts or "__pycache__" in relative.parts:
            continue
        check(not file.is_symlink(), f"Symlink in package: {relative}")
        if file.is_file():
            actual.add(relative.as_posix())
    check(actual == set(names) | {"manifest.json"}, "Package inventory changed")
    for row in records:
        data = checked_file(root, row["path"]).read_bytes()
        check(
            len(data) == row["bytes"] and sha256(data) == row["sha256"],
            f"File hash/size mismatch: {row['path']}",
        )

    source_bytes = (root / "harness/RELEASE-MANIFEST.json").read_bytes()
    check(sha256(source_bytes) == SOURCE_SHA256, "Evaluated manifest changed")
    source_manifest = json.loads(source_bytes)
    for row in source_manifest["files"]:
        check(
            sha256(checked_file(root / "harness", row["path"]).read_bytes()) == row["sha256"],
            f"Evaluated source changed: {row['path']}",
        )

    bundle = (root / "assets/api9-source-and-licenses.zip").read_bytes()
    check(sha256(bundle) == BUNDLE_SHA256, "Licensed bundle changed")
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        source_zip = archive.read("source.zip")
    check(sha256(source_zip) == ARCHIVE_SHA256, "Evaluated source ZIP changed")
    with zipfile.ZipFile(io.BytesIO(source_zip)) as archive:
        expected = {r["path"] for r in source_manifest["files"]} | {"RELEASE-MANIFEST.json"}
        check(
            len(archive.namelist()) == len(expected) and set(archive.namelist()) == expected,
            "Source archive inventory changed",
        )
        for row in source_manifest["files"]:
            check(sha256(archive.read(row["path"])) == row["sha256"], "Source ZIP member changed")

    for file in (root / "notebooks").glob("*.ipynb"):
        notebook = json.loads(file.read_text())
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                check(not cell.get("outputs"), "Notebook contains execution output")
                ast.parse("".join(cell["source"]))
    return {
        "status": "SATISFIED",
        "scope": "Package identity and notebook syntax only",
        "files": len(actual),
        "evaluated_source_files": len(source_manifest["files"]),
        "paid_requests": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
