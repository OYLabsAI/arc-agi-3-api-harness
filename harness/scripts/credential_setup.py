"""Prompt privately; store only in the user's chosen private directory."""

import argparse
import getpass
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser(description="Save API credentials without echoing them")
parser.add_argument("path", type=Path, help="Private JSON path outside the source release")
args = parser.parse_args()
args.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
keys = {name: getpass.getpass(name + ": ").strip() for name in ("OPENAI_API_KEY", "ARC_API_KEY")}
if not all(keys.values()):
    raise SystemExit("Both keys are required; no file written")
descriptor = os.open(args.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "w") as file:
    json.dump(keys, file)
print("Credentials saved privately. No evaluation started.")
