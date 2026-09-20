"""Render the public token comparison from the published evidence.

Requires matplotlib==3.9.4. No network access or model calls.
Copyright 2026 Orca Labs sp. z o.o. Licensed under Apache-2.0.
"""

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
AUDIT_URL = (
    "https://github.com/OYLabsAI/arc-agi-3-api-harness/blob/main/"
    "docs/token-comparison.md"
)


def render(output_dir):
    comparison = json.loads((ROOT / "evidence/public-token-comparison.json").read_text())
    run = json.loads((ROOT / "evidence/public-run.json").read_text())
    baseline = sum(game["total_tokens"] for game in comparison["games"])
    oy1 = run["total_tokens"]
    levels = sum(game["levels_completed"] for game in comparison["games"])
    games = len(comparison["games"])
    reduction = 100 * (1 - oy1 / baseline)
    if not (
        baseline == comparison["totals"]["total_tokens"]
        and oy1 == comparison["oy1"]["reported_total_tokens"]
        and levels == run["levels_solved"]
        and games == run["games_won"] == run["games_selected"]
        and math.isclose(reduction, comparison["reduction_percent"])
    ):
        raise ValueError("Comparison and run evidence disagree")

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "svg.fonttype": "path",
        "svg.hashsalt": "oy1-public-token-comparison",
        "pdf.fonttype": 42,
    })
    ink, muted, grid = "#172D3B", "#516575", "#DCE4E8"
    teal, slate = "#007C78", "#758797"
    fig = plt.figure(figsize=(12, 7.5), facecolor="white")

    def label(x, y, value, size=11, color=ink, weight="normal", **kwargs):
        return fig.text(x, y, value, fontsize=size, color=color,
                        fontweight=weight, va="top", **kwargs)

    label(.055, .951, "OY LABS  /  RESEARCH", 10, teal, "bold")
    label(.945, .951, "20 SEPTEMBER 2026", 9, muted, ha="right")
    label(.055, .89, f"{reduction:.2f}% fewer total tokens", 31, ink, "bold")
    label(.055, .812, "ARC-AGI-3 public set · GPT-6 Astra · High reasoning", 14)
    label(.055, .765,
          f"Same {games} game versions. Both runs completed all {levels} levels.",
          12, muted)

    ax = fig.add_axes([.27, .305, .66, .365])
    values = [baseline / 1_000_000, oy1 / 1_000_000]
    ax.set_xlim(0, 1000)
    ax.set_ylim(-.65, 1.65)
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=grid, linewidth=.7)
    ax.barh([1, 0], values, height=.36, color=[slate, teal], zorder=3)
    ax.set_yticks([])
    ax.set_xticks([0, 250, 500, 750, 1000], ["0", "250", "500", "750", "1,000"])
    ax.tick_params(axis="x", length=0, pad=10, colors=muted, labelsize=10)
    ax.set_xlabel("Total tokens (millions) · Lower is better", color=muted,
                  fontsize=10, labelpad=12)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.axvline(0, color=grid, linewidth=1)
    for y, name, detail, value, color in [
        (1, "Provider Adapter", "Public replay total", values[0], ink),
        (0, "OY1", "Reported run aggregate", values[1], teal),
    ]:
        ax.text(-.045, y + .075, name, transform=ax.get_yaxis_transform(),
                ha="right", va="center", fontsize=13, fontweight="bold", color=color)
        ax.text(-.045, y - .145, detail, transform=ax.get_yaxis_transform(),
                ha="right", va="center", fontsize=9, color=muted)
        ax.text(value, y + .27, f"{value:,.2f}M", ha="right", va="bottom",
                fontsize=15, fontweight="bold", color=color)

    fig.add_artist(Line2D([.055, .945], [.207, .207], transform=fig.transFigure,
                         color=grid, linewidth=.8))
    label(.055, .184,
          "Accounting: input + output, including cached input. OY1 includes compaction.",
          10, muted)
    label(.055, .147,
          "Published runs; public games used during OY1 development. No controlled ablation or cost claim.",
          9, muted)
    label(.055, .113,
          "Sources: ARC Prize public replays; OY1 published aggregate (9 Sep 2026). OY1 usage ledger is private.",
          9, muted)
    label(.055, .068, "Data, replay hashes and reproduction: OYLabsAI/arc-agi-3-api-harness",
          9, teal, url=AUDIT_URL)
    label(.945, .068, "PUBLIC TOKEN COMPARISON", 8, muted, ha="right")

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_dir / "public-token-comparison"
    title = "OY1: ARC-AGI-3 public replay token comparison"
    description = (
        f"Provider Adapter: {baseline:,} total tokens. OY1: {oy1:,}. "
        f"{reduction:.2f}% fewer; same {games} game versions and {levels} completed levels. "
        f"Published-run comparison. Full accounting: {AUDIT_URL}"
    )
    fig.savefig(stem.with_suffix(".png"), dpi=200,
                metadata={"Title": title, "Description": description, "Author": "OY Labs"})
    fig.savefig(stem.with_suffix(".svg"),
                metadata={"Title": title, "Description": description,
                          "Creator": "OY Labs", "Date": None})
    svg = stem.with_suffix(".svg")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    fig.savefig(stem.with_suffix(".pdf"),
                metadata={"Title": title, "Subject": description, "Author": "OY Labs",
                          "CreationDate": None, "ModDate": None})
    plt.close(fig)
    print(json.dumps({"provider_tokens": baseline, "oy1_tokens": oy1,
                      "reduction_percent": reduction, "output": str(stem)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/figures")
    render(parser.parse_args().output_dir)
