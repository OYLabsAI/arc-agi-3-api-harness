"""Verify checkout integrity and the source identity used for reproduction.

Copyright 2026 Orca Labs sp. z o.o. Licensed under Apache-2.0.
"""

import argparse
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


def check_records(root, records):
    names = [row["path"] for row in records]
    check(len(names) == len(set(names)), "Duplicate manifest paths")
    for row in records:
        data = checked_file(root, row["path"]).read_bytes()
        check(len(data) == row["bytes"] and sha256(data) == row["sha256"],
              f"File hash/size mismatch: {row['path']}")
    return set(names)


def verify(root=ROOT, evaluated_bundle=None):
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    actual = set()
    for file in root.rglob("*"):
        relative = file.relative_to(root)
        if ".git" in relative.parts or "__pycache__" in relative.parts:
            continue
        check(not file.is_symlink(), f"Symlink in package: {relative}")
        if file.is_file():
            actual.add(relative.as_posix())
    names = check_records(root, manifest["files"])
    check(actual == names | {"manifest.json"}, "Package inventory changed")

    source_bytes = (root / "harness/RELEASE-MANIFEST.json").read_bytes()
    check(sha256(source_bytes) == manifest["maintained_source_manifest_sha256"],
          "Maintained source manifest changed")
    source = json.loads(source_bytes)
    source_names = check_records(root / "harness", source["files"])
    expected = {"harness/" + name for name in source_names} | {"harness/RELEASE-MANIFEST.json"}
    check({name for name in actual if name.startswith("harness/")} == expected,
          "Maintained source inventory changed")

    identity = json.loads((root / "evidence/evaluated-source.json").read_text())
    check(identity["bundle_sha256"] == BUNDLE_SHA256, "Evaluated bundle identity changed")
    check(identity["source_archive_sha256"] == ARCHIVE_SHA256, "Evaluated archive identity changed")
    check(identity["source_manifest_sha256"] == SOURCE_SHA256, "Evaluated manifest identity changed")
    unchanged = identity["unchanged_source_files"]
    check({"arc_harness/prompt.py", "arc_harness/runner.py", "arc_harness/store.py",
           "arc_harness/api_provider.py", "arc_harness/perception.py"} <= set(unchanged),
          "Missing evaluated solver identity")
    for name, digest in unchanged.items():
        check(sha256(checked_file(root / "harness", name).read_bytes()) == digest,
              f"Evaluated file changed: {name}")

    if evaluated_bundle is not None:
        bundle = Path(evaluated_bundle).read_bytes()
        check(sha256(bundle) == BUNDLE_SHA256, "Evaluated bundle bytes changed")
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            source_zip = archive.read("source.zip")
        check(sha256(source_zip) == ARCHIVE_SHA256, "Evaluated source ZIP changed")
        with zipfile.ZipFile(io.BytesIO(source_zip)) as archive:
            original_manifest = archive.read("RELEASE-MANIFEST.json")
            check(sha256(original_manifest) == SOURCE_SHA256, "Evaluated manifest bytes changed")
            records = json.loads(original_manifest)["files"]
            expected = {r["path"] for r in records} | {"RELEASE-MANIFEST.json"}
            check(len(archive.namelist()) == len(expected) and set(archive.namelist()) == expected,
                  "Evaluated archive inventory changed")
            for row in records:
                check(sha256(archive.read(row["path"])) == row["sha256"], "Evaluated archive member changed")
            for name, digest in unchanged.items():
                check(sha256(archive.read(name)) == digest, "Evaluated source comparison differs")

    for file in (root / "notebooks").glob("*.ipynb"):
        notebook = json.loads(file.read_text())
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                check(not cell.get("outputs"), "Notebook contains execution output")
                ast.parse("".join(cell["source"]))
    return {
        "status": "passed",
        "scope": "Checkout integrity, source identity and notebook syntax",
        "files": len(actual),
        "maintained_source_files": len(source_names),
        "unchanged_evaluated_files": len(unchanged),
        "evaluated_bundle_checked": evaluated_bundle is not None,
        "paid_requests": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluated-bundle", type=Path,
                        help="Also verify a downloaded copy of the exact evaluated bundle")
    print(json.dumps(verify(evaluated_bundle=parser.parse_args().evaluated_bundle), indent=2))
