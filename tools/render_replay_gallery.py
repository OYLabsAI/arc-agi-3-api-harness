"""Render selected OY1 levels from pinned public ARC Prize recordings.

Requires Pillow==11.3.0. Downloads public recordings; makes no model calls.
Copyright 2026 Orca Labs sp. z o.o. Licensed under Apache-2.0.
"""

import argparse
import ast
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def palette():
    # Read the evaluated palette as data, without importing the harness.
    tree = ast.parse((ROOT / "harness/arc_harness/perception.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "PALETTE" for t in node.targets
        ):
            colors = ast.literal_eval(node.value)
            break
    else:
        raise ValueError("ARC palette not found")
    colors += ["#172D3B", "#516575", "#007C78"]
    values = [int(c[i:i + 2], 16) for c in colors for i in (1, 3, 5)]
    return values + [0] * (768 - len(values))


def render(record, clip, cache, output_dir, colors):
    cached = cache / (record["game_id"] + ".jsonl")
    data = cached.read_bytes() if cached.exists() else urlopen(
        record["recording_url"], timeout=120
    ).read()
    require(hashlib.sha256(data).hexdigest() == record["sha256"], "Recording hash mismatch")
    rows = [json.loads(line)["data"] for line in data.splitlines()]
    require(all(r["game_id"] == record["game_id"] and r["guid"] == record["guid"]
                for r in rows), "Recording identity mismatch")
    require(rows[-1]["state"] == "WIN", "Recording does not end in WIN")
    require(rows[-1]["levels_completed"] == record["levels_completed"], "Level count mismatch")
    require(len(rows) - 1 == record["actions"], "Action count mismatch")
    if not cached.exists():
        cached.write_bytes(data)

    level = clip["level"]
    start = next(i for i, r in enumerate(rows) if r["levels_completed"] == level - 1)
    end = next(i for i, r in enumerate(rows) if r["levels_completed"] == level)
    require([start, end] == clip["observation_rows_inclusive"], "Clip boundaries changed")
    require(end - start == clip["actions"], "Clip action count mismatch")
    require(all(r["levels_completed"] == level - 1 for r in rows[start:end]),
            "Noncontiguous level sequence")
    require(not any(r.get("full_reset") for r in rows[start + 1:end + 1]),
            "Clip contains a full game reset")

    frames, durations = [], []
    title_font = ImageFont.load_default(size=19)
    small_font = ImageFont.load_default(size=14)
    for i in range(start, end + 1):
        # Start with the settled initial board, then retain every animation frame
        # of every action through the level-completion transition.
        grids = rows[i]["frame"][-1:] if i == start else rows[i]["frame"]
        for j, grid in enumerate(grids):
            require(len(grid) == 64 and all(len(row) == 64 for row in grid), "Unexpected grid size")
            require(all(isinstance(v, int) and 0 <= v < 16 for row in grid for v in row),
                    "Unexpected palette value")
            frame = Image.new("P", (416, 544), 0)
            frame.putpalette(colors)
            board = Image.new("P", (64, 64))
            board.putpalette(colors)
            board.putdata([v for row in grid for v in row])
            frame.paste(board.resize((384, 384), Image.Resampling.NEAREST), (16, 64))
            draw = ImageDraw.Draw(frame)
            draw.text((16, 12), "OY1", font=title_font, fill=18)
            draw.text((400, 12), record["game_id"][:4].upper(),
                      anchor="ra", font=title_font, fill=16)
            draw.text((16, 38), f"Level {level}  /  {end - start} actions", font=small_font, fill=17)
            last = i == end and j == len(grids) - 1
            status = f"Level {level} complete" if last else f"Step {i - start} of {end - start}"
            draw.text((16, 461), status, font=small_font, fill=18 if last else 16)
            draw.text((16, 487), f"Provider Adapter {clip['provider_adapter_actions']} · OY1 {clip['actions']}",
                      font=small_font, fill=17)
            reduction = 100 * (1 - clip['actions'] / clip['provider_adapter_actions'])
            draw.text((16, 513), f"{reduction:.1f}% fewer actions", font=small_font, fill=18)
            frames.append(frame)
            durations.append(1800 if last else 900 if i == start else 240 if j == len(grids) - 1 else 60)

    source_frames = len(frames)
    merged_frames, merged_durations = [], []
    for frame, duration in zip(frames, durations):
        if merged_frames and frame.tobytes() == merged_frames[-1].tobytes():
            merged_durations[-1] += duration
        else:
            merged_frames.append(frame)
            merged_durations.append(duration)
    frames, durations = merged_frames, merged_durations
    target = output_dir / Path(clip["gif"]).name
    frames[0].save(target, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, disposal=2, optimize=False,
                   comment=(record["replay_url"] + " | " + record["sha256"]).encode("ascii"))
    frames[0].convert("RGB").save(output_dir / Path(clip["poster"]).name)
    with Image.open(target) as saved:
        require(saved.n_frames == len(frames), "Export dropped frames")
        for i, expected in enumerate(frames):
            saved.seek(i)
            require(saved.info["duration"] == durations[i], "Playback timing changed")
            require(saved.convert("RGB").tobytes() == expected.convert("RGB").tobytes(),
                    "Export changed pixels")
    return {"game": record["game_id"], "level": level, "actions": end - start,
            "source_frames": source_frames, "gif_frames": len(frames),
            "duration_seconds": sum(durations) / 1000,
            "bytes": target.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/replays")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    index = json.loads((ROOT / "evidence/public-replays.json").read_text())
    result = [render(r, clip, args.cache, args.output_dir, palette())
              for r in index["games"] for clip in r.get("clips", [])]
    print(json.dumps({"clips": result, "paid_requests": 0}, indent=2))


if __name__ == "__main__":
    main()
