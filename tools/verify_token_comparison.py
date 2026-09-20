"""Recompute token usage from the pinned public replay recordings.

Copyright 2026 Orca Labs sp. z o.o. Licensed under Apache-2.0.
"""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens",
          "total_tokens", "levels_completed", "usage_records", "reasoning_records_without_usage")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_recording(record, content):
    require(hashlib.sha256(content).hexdigest() == record["sha256"],
            f"Recording changed: {record['game_id']}")
    totals = dict.fromkeys(FIELDS, 0)
    final = None
    for line in content.splitlines():
        data = json.loads(line)["data"]
        require(data["game_id"] == record["game_id"], "Game version mismatch")
        final = data
        reasoning = data["action_input"].get("reasoning")
        if not reasoning:
            continue
        payload = json.loads(reasoning) if isinstance(reasoning, str) else reasoning
        usage = payload.get("usage") or {}
        if "total_tokens" not in usage:
            totals["reasoning_records_without_usage"] += 1
            continue
        require(usage["total_tokens"] == usage["input_tokens"] + usage["output_tokens"],
                "Inconsistent token accounting")
        for name in ("input_tokens", "output_tokens", "total_tokens"):
            totals[name] += usage[name]
        totals["cached_input_tokens"] += (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
        totals["reasoning_tokens"] += (usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
        totals["usage_records"] += 1
    require(final is not None and final["state"] == "WIN", "Replay did not end in WIN")
    totals["levels_completed"] = final["levels_completed"]
    for name in FIELDS:
        require(totals[name] == record[name], f"Unexpected {name}: {record['game_id']}")
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path, help="Directory for public replay downloads")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    audit = json.loads((ROOT / "evidence/public-token-comparison.json").read_text())
    oy1 = json.loads((ROOT / "evidence/public-run.json").read_text())
    games = json.loads((ROOT / "evidence/per-game-results.json").read_text())["games"]
    expected = {g["game_id"]: g["levels_completed"] for g in games}
    require(len(audit["games"]) == len(expected) == 25, "Expected exactly 25 games")
    require({g["game_id"] for g in audit["games"]} == set(expected), "Game selection differs")
    totals = dict.fromkeys(FIELDS, 0)
    for record in audit["games"]:
        require(record["config"] == "openai-gpt-6-astra-high-provider-adapter", "Unexpected configuration")
        require(record["levels_completed"] == expected[record["game_id"]], "Level counts differ")
        guid = record["replay_url"].rsplit("/", 1)[1]
        url = f"https://arcprize.org/api/recordings/{record['game_id']}/{guid}"
        require(url == record["recording_url"], "Unexpected recording URL")
        cache = args.cache / f"public-{guid}.jsonl"
        content = cache.read_bytes() if cache.exists() else urlopen(url, timeout=120).read()
        result = check_recording(record, content)
        if not cache.exists():
            cache.write_bytes(content)
        for name in FIELDS:
            totals[name] += result[name]
    require(totals == audit["totals"], "Aggregate differs")
    require(oy1["total_tokens"] == audit["oy1"]["reported_total_tokens"], "OY1 aggregate differs")
    reduction = 100 * (1 - oy1["total_tokens"] / totals["total_tokens"])
    require(abs(reduction - audit["reduction_percent"]) < 1e-9, "Reduction differs")
    print(json.dumps({"status": "passed", "scope": "Pinned public replays versus reported OY1 aggregate",
                      "games": 25, "provider_adapter": totals, "oy1_reported_tokens": oy1["total_tokens"],
                      "reduction_percent": reduction, "paid_requests": 0}, indent=2))


if __name__ == "__main__":
    main()
