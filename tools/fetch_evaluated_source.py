"""Download the hash-pinned source bundle used for OY1's completed public run.

Copyright 2026 Orca Labs sp. z o.o. Licensed under Apache-2.0.
"""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA256 = "be904f8b6e72cea0ca469d9bee1697f2fa5927fce8145a345546bc772f687f7d"


def fetch(output):
    identity = json.loads((ROOT / "evidence/evaluated-source.json").read_text())
    if output.exists():
        data = output.read_bytes()
    else:
        with urlopen(identity["bundle_url"], timeout=60) as response:
            if not response.url.startswith("https://"):
                raise ValueError("Source redirect must remain HTTPS")
            data = response.read(10_000_001)
    if len(data) > 10_000_000 or hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Evaluated source bundle size/hash mismatch")
    if not output.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(data)
    print(json.dumps({"path": str(output.resolve()), "sha256": EXPECTED_SHA256,
                      "bytes": len(data), "paid_requests": 0}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    fetch(parser.parse_args().output)
