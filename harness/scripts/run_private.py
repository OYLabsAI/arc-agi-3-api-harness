"""Load a private key file and run with a minimal child environment."""

import argparse
import json
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from bootstrap import environment

parser = argparse.ArgumentParser()
parser.add_argument("--credentials", type=Path, required=True)
parser.add_argument("--plan", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--expected-release-sha256", required=True)
args = parser.parse_args()
if args.credentials.is_symlink() or stat.S_IMODE(args.credentials.stat().st_mode) & 0o077:
    raise SystemExit("Credentials must be a private regular file (chmod 600)")
keys = json.loads(args.credentials.read_text())
if set(keys) != {"OPENAI_API_KEY", "ARC_API_KEY"}:
    raise SystemExit("Expected only the two API keys")
with tempfile.TemporaryDirectory(prefix="oy-api-home-") as home:
    result = subprocess.run([sys.executable, "-m", "arc_harness.api_run", "run", "--plan",
                             str(args.plan.resolve()), "--output", str(args.output.resolve()),
                             "--expected-release-sha256", args.expected_release_sha256],
                            cwd=Path(__file__).resolve().parent.parent, env=environment(home, keys))
raise SystemExit(result.returncode)
