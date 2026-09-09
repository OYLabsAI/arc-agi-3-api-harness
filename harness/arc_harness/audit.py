"""Offline exports from recorded evidence; never imported into the solver context."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

FIELDS = {
    "input_tokens": "inputTokens",
    "cached_tokens": "cachedInputTokens",
    "cache_write_tokens": "cacheWriteInputTokens",
    "output_tokens": "outputTokens",
    "reasoning_tokens": "reasoningOutputTokens",
    "total_tokens": "totalTokens",
}


def seconds(start, end):
    return round((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds(), 6)


def usage_rows(events, game_id, manifest):
    """Preserve notifications; do not invent request IDs for historical counters."""
    started = next((e["data"] for e in events if e["kind"] == "provider_started"), {})
    raw = [e for e in events if e["kind"] == "provider_model_call"]
    rows, previous, seen = [], {}, set()
    duplicate_count = 0
    for e in raw or [e for e in events if e["kind"] == "provider_usage"]:
        data = e["data"]
        if raw:
            identity = data["response_id"]
            if identity in seen:
                duplicate_count += 1
                continue
            seen.add(identity)
            usage = data.get("usage") or {}
        else:
            total = data["total"]
            if total == previous:
                duplicate_count += 1
                continue
            usage = {key: total.get(key, 0) - previous.get(key, 0) for key in total}
            if any(value < 0 for value in usage.values()):
                raise ValueError("Usage counters decreased; cannot infer incremental usage")
            if usage != data["last"]:
                raise ValueError("Usage increment does not equal reported last request")
            previous = total
        rows.append({
            "game_id": game_id,
            "record_index": len(rows) + 1,
            "response_id": data.get("response_id") if raw else None,
            "recorded_at": data.get("received_at", e["at"]),
            "model_id": started.get("effective_model", manifest["model"]),
            "reasoning_effort": started.get("effective_effort", manifest["effort"]),
            "fast_mode": started.get("fast_mode"),
            "service_tier": started.get("service_tier"),
            "record_type": "completed_model_response" if raw else "distinct_usage_update",
            **{name: usage.get(key) for name, key in FIELDS.items()},
        })
    return rows, duplicate_count


def level_rows(events, game_id, baselines):
    """Partition time at observed completion; include resets and failed experiments."""
    started = next(e["at"] for e in events if e["kind"] == "run_started")
    boundary, current, actions, resets = started, 0, 0, 0
    rows = []
    for e in events:
        d = e["data"]
        if e["kind"] == "action_submitted":
            actions += 1
            resets += d["action"]["name"] == "RESET"
        elif e["kind"] == "observation" and d["levels_completed"] != current:
            if d["levels_completed"] != current + 1:
                raise ValueError("Nonsequential level transition requires explicit accounting")
            baseline = baselines[current] if baselines else None
            if actions <= 0:
                raise ValueError("A completed level has no recorded actions")
            rows.append({
                "game_id": game_id, "level": current + 1,
                "actions_taken": actions, "resets": resets,
                "human_baseline": baseline,
                "rhae_percent": min(115.0, 100 * (baseline / actions) ** 2) if baseline else None,
                "rhae_source": "local calculation from recorded actions and post-run public baselines",
                "started_at": boundary, "completed_at": e["at"],
                "wall_clock_seconds": seconds(boundary, e["at"]),
            })
            current += 1
            boundary, actions, resets = e["at"], 0, 0
    return rows


def write_exports(directory, name, rows):
    (directory / f"{name}.json").write_text(json.dumps(rows, indent=2) + "\n")
    (directory / f"{name}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    if rows:
        with (directory / f"{name}.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def export_run(root: Path, output: Path, baseline_file: Path | None = None):
    manifest = json.loads((root / "manifest.json").read_text())
    card_path = root / "scorecard.json"
    card_export = json.loads(card_path.read_text()) if card_path.exists() else {}
    card = card_export.get("sdk_scorecard")
    baseline_path = baseline_file or root / "reconstructed-score.json"
    baselines = {}
    if baseline_path.exists():
        baseline_document = json.loads(baseline_path.read_text())
        baselines = {g["game_id"]: g["human_baseline_actions"] for g in baseline_document["games"]}
    official_runs = {}
    if card:
        for environment in card.get("environments", []):
            if len(environment.get("runs", [])) == 1:
                official_runs[environment["id"]] = environment["runs"][0]
                baselines[environment["id"]] = environment["runs"][0]["level_baseline_actions"]
    calls, levels, games = [], [], []
    totals = Counter()
    cumulative_totals = Counter()
    discrepancies = []
    failures = []
    duplicates = 0
    sources = {}
    usage_finalized = []
    for game in manifest["selected_games"]:
        result_path = root / game / "result.json"
        if not result_path.exists():
            continue
        result = json.loads(result_path.read_text())
        event_path = result_path.with_name("events.jsonl")
        events = list(map(json.loads, event_path.open()))
        failures.extend({"game_id": game, **e} for e in events
                        if e["kind"] in ("error", "provider_error", "provider_recovery"))
        source_bytes = event_path.read_bytes()
        sources[str(event_path.relative_to(root))] = hashlib.sha256(source_bytes).hexdigest()
        call_rows, dup = usage_rows(events, game, manifest)
        game_levels = level_rows(events, game, baselines.get(game))
        if game in official_runs:
            official = official_runs[game]
            for row in game_levels:
                index = row["level"] - 1
                if row["actions_taken"] != official["level_actions"][index]:
                    raise ValueError(f"{game}: local and official level actions differ")
                row["rhae_percent"] = official["level_scores"][index]
                row["rhae_source"] = "official scorecard"
        calls.extend(call_rows)
        levels.extend(game_levels)
        duplicates += dup
        usage = result["provider_stats"]["total_usage"]
        usage_finalized.append(result["provider_stats"].get("usage_complete", False)
                               and result.get("error") is None)
        for name, key in FIELDS.items():
            value = usage.get(key, 0)
            recorded = sum(row[name] or 0 for row in call_rows)
            if recorded != value:
                discrepancies.append({"game_id": game, "metric": name,
                                      "completed_response_sum": recorded, "cumulative_counter": value,
                                      "difference": recorded - value})
            totals[name] += recorded
            cumulative_totals[name] += value
        if result["won"] and sum(row["actions_taken"] for row in game_levels) != result["actions_submitted"]:
            raise ValueError(f"{game}: actions do not reconcile")
        if len(game_levels) != result["levels_completed"]:
            raise ValueError(f"{game}: levels do not reconcile")
        if result["model"] != manifest["model"] or result["effort"] != manifest["effort"]:
            raise ValueError(f"{game}: configuration differs")
        if result["limits"] != manifest["limits_per_game"]:
            raise ValueError(f"{game}: limits differ")
        score = None
        if game_levels and len(game_levels) == result["win_levels"] and game in baselines:
            score = min(100., sum(r["level"] * r["rhae_percent"] for r in game_levels)
                        / sum(r["level"] for r in game_levels))
        games.append({
            "game_id": game, "won": result["won"],
            "levels_completed": result["levels_completed"], "total_levels": result["win_levels"],
            "actions_taken": result["actions_submitted"], "reconstructed_rhae_percent": score,
            "wall_clock_seconds": result["elapsed_seconds"],
            "level_time_seconds": round(sum(r["wall_clock_seconds"] for r in game_levels), 6),
            "tool_decisions": result["model_calls"], "usage_records": len(call_rows),
            "tokens": {name: sum(row[name] or 0 for row in call_rows) for name in FIELDS},
            "cumulative_usage_counters": {name: usage.get(key, 0) for name, key in FIELDS.items()},
        })
    source_root = root / manifest["source_snapshot"]
    source_digest = hashlib.sha256(b"".join(
        p.name.encode() + p.read_bytes() for p in sorted(source_root.glob("*.py"))
    )).hexdigest()
    if source_digest != manifest["source_sha256"]:
        raise ValueError("Frozen source digest differs from manifest")
    literals = []
    for path in source_root.glob("*.py"):
        text = path.read_text().lower()
        for game in manifest["selected_games"]:
            # Report occurrences, including CLI examples; these are not automatically policy leaks.
            if game in text or game.split("-")[0] in text:
                literals.append({"file": path.name, "game": game})
    summary = {
        "run_id": root.name, "mode": manifest["mode"], "provider": manifest["provider"],
        "model": manifest["model"], "reasoning_effort": manifest["effort"],
        "fast_mode": manifest.get("fast_mode"),
        "games_selected": len(manifest["selected_games"]), "games_finished": len(games),
        "games_won": sum(g["won"] for g in games), "levels_completed": len(levels),
        "actions_taken": sum(g["actions_taken"] for g in games),
        "tokens": dict(totals), "token_accounting_reconciled": not discrepancies,
        "token_source": "sum of exported usage records; response IDs used when recorded",
        "cumulative_usage_counters": dict(cumulative_totals),
        "usage_discrepancies": discrepancies,
        "provider_failures": failures,
        "token_definition": "Total = input + output. Cached tokens are included in input; reasoning tokens in output.",
        "usage_records": len(calls), "duplicate_usage_notifications_removed": duplicates,
        "per_call_evidence_scope": "finished_games_only",
        "per_call_evidence_complete": bool(calls) and all(usage_finalized) and all(
            r["response_id"] and r["fast_mode"] is not None for r in calls),
        "historical_logging_limit": (
            "Distinct usage updates are not independently identified requests. Historical Fast mode is unknown."
            if any(r["response_id"] is None or r["fast_mode"] is None for r in calls) else None),
        "wall_clock_seconds_sum_games": round(sum(g["wall_clock_seconds"] for g in games), 3),
        "timing_definition": "Level 1 starts at run_started; each later level starts at the prior completion observation. Includes thinking, actions, resets and local processing; excludes SDK initial make and finalization after WIN. Reconstructed from UTC event timestamps.",
        "source_sha256": source_digest, "source_digest_matches": True,
        "declared_config_identical_across_finished_games": True,
        "source_game_literal_occurrences": literals,
        "generalization_claim": "Source/config audit only; no private-set generalization result or independent sandbox attestation.",
        "competition_scorecard_available": False,
        "competition_scorecard_url": None,
    }
    if card and manifest["mode"] == "competition" and card.get("competition_mode"):
        summary["competition_scorecard_available"] = True
        summary["official_score_percent"] = card.get("score")
        summary["official_levels_completed"] = card.get("total_levels_completed")
        summary["official_total_levels"] = card.get("total_levels")
        summary["official_card_id"] = card.get("card_id")
        summary["competition_scorecard_url"] = "https://arcprize.org/scorecards/" + card["card_id"]
    output.mkdir(parents=True, exist_ok=True)
    if card:
        (output / "official-scorecard.json").write_text(json.dumps(card, indent=2) + "\n")
    for name, rows in [("usage-records", calls), ("levels", levels), ("games", games)]:
        write_exports(output, name, rows)
    write_exports(output, "provider-recovery", failures)
    (output / "audit.json").write_text(json.dumps(summary, indent=2) + "\n")
    (output / "evidence-sha256.json").write_text(json.dumps(sources, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baselines", type=Path)
    args = parser.parse_args()
    print(json.dumps(export_run(args.directory, args.output, args.baselines), indent=2))


if __name__ == "__main__":
    main()
