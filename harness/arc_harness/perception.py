from __future__ import annotations

import base64
import io
from collections import Counter, deque

import numpy as np
from PIL import Image

# ARC-AGI-3 palette, distinct from the ARC-AGI-1/2 palette.
PALETTE = [
    "#FFFFFF",
    "#CCCCCC",
    "#999999",
    "#666666",
    "#333333",
    "#000000",
    "#E53AA3",
    "#FF7BCC",
    "#F93C31",
    "#1E93FF",
    "#88D8F1",
    "#FFDC00",
    "#FF851B",
    "#921231",
    "#4FCC30",
    "#A356D6",
]


def image_bytes(grid: np.ndarray, scale=8) -> bytes:
    colors = np.array([[int(c[i : i + 2], 16) for i in (1, 3, 5)] for c in PALETTE], dtype=np.uint8)
    im = Image.fromarray(colors[grid])
    im = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()


def image_url(grid):
    return "data:image/png;base64," + base64.b64encode(image_bytes(grid)).decode()


def components(grid: np.ndarray, limit=100):
    h, w = grid.shape
    seen = np.zeros_like(grid, dtype=bool)
    result = []
    for y in range(h):
        for x in range(w):
            if seen[y, x]:
                continue
            color = int(grid[y, x])
            queue, cells = deque([(x, y)]), []
            seen[y, x] = True
            while queue:
                cx, cy = queue.popleft()
                cells.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny, nx] and grid[ny, nx] == color:
                        seen[ny, nx] = True
                        queue.append((nx, ny))
            xs, ys = zip(*cells)
            result.append(
                {
                    "color": color,
                    "area": len(cells),
                    "bbox": [min(xs), min(ys), max(xs) + 1, max(ys) + 1],
                    "centroid": [round(sum(xs) / len(xs), 2), round(sum(ys) / len(ys), 2)],
                }
            )
    result.sort(key=lambda c: (-c["area"], c["color"], c["bbox"]))
    return {"items": result[:limit], "total": len(result), "truncated": len(result) > limit}


def describe(grid: np.ndarray, include_rows=False):
    result = {
        "width": grid.shape[1],
        "height": grid.shape[0],
        "colors": {str(k): v for k, v in sorted(Counter(map(int, grid.flat)).items())},
        "components": components(grid),
    }
    if include_rows:
        result["encoding"] = (
            "One hexadecimal digit per pixel; rows indexed by y, columns by x; 0-f = colors 0-15"
        )
        result["rows"] = ["".join(format(int(v), "x") for v in row) for row in grid]
    return result


def difference(before: np.ndarray, after: np.ndarray):
    if before.shape != after.shape:
        return {"shape_changed": True, "changed_pixels": int(after.size)}
    ys, xs = np.where(before != after)
    changes = Counter((int(before[y, x]), int(after[y, x])) for x, y in zip(xs, ys))
    return {
        "changed_pixels": len(xs),
        "bbox": [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)] if len(xs) else None,
        "color_changes": [{"from": a, "to": b, "count": n} for (a, b), n in changes.most_common()],
        "sample": [[int(x), int(y), int(before[y, x]), int(after[y, x])] for x, y in list(zip(xs, ys))[:64]],
    }


def check_prediction(action, observation):
    errors = []
    grid = observation.grid
    for p in action.expected_pixels:
        if p.y >= grid.shape[0] or p.x >= grid.shape[1]:
            errors.append(f"Predicted pixel ({p.x},{p.y}) outside observed grid")
        elif int(grid[p.y, p.x]) != p.color:
            errors.append(f"({p.x},{p.y}): expected {p.color}, observed {int(grid[p.y, p.x])}")
    if action.expected_state is not None and action.expected_state != observation.state:
        errors.append(f"Expected state {action.expected_state}, observed {observation.state}")
    if action.expected_levels is not None and action.expected_levels != observation.levels_completed:
        errors.append(
            f"Expected {action.expected_levels} completed levels, observed {observation.levels_completed}"
        )
    return {
        "tested": bool(
            action.expected_pixels or action.expected_state is not None or action.expected_levels is not None
        ),
        "matched": not errors,
        "errors": errors,
    }
