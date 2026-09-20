# Gameplay replays

These recordings belong to OY1's completed run on **9 September 2026**:
25 games, 183 levels and 6,732 environment actions.

[ARC Prize scorecard](https://arcprize.org/scorecards/75d9c8e7-ade9-4a8f-a747-6acbea51bb1b) ·
[Run results](results.md) · [Replay index and recording hashes](../evidence/public-replays.json)

## Selected clips

The README shows LS20, WA30, CD82 and VC33, the same four games used in
[NVIDIA DreamTeam's examples](https://github.com/NVIDIA/dream-team#examples).
These are presentation examples, not a representative sample of the benchmark.
Each OY1 clip contains a complete level sequence through its completion transition.

| Game | Level | Actions | Animation | Still image |
|---|---:|---:|---|---|
| [LS20](https://arcprize.org/replay/0a9dfe50-1421-45c9-8041-773c58b6b85b) | 3 | 43 | [GIF](replays/ls20-level-3.gif) | [PNG](replays/ls20-level-3.png) |
| [WA30](https://arcprize.org/replay/6503caa5-73c0-4b5e-9fdf-9d5d8e6eb176) | 3 | 74 | [GIF](replays/wa30-level-3.gif) | [PNG](replays/wa30-level-3.png) |
| [CD82](https://arcprize.org/replay/20fcc634-9e4e-4c3d-a638-b577b0301cd1) | 3 | 19 | [GIF](replays/cd82-level-3.gif) | [PNG](replays/cd82-level-3.png) |
| [VC33](https://arcprize.org/replay/c8995261-2fa7-48b4-9fc6-e1624a20697f) | 2 | 7 | [GIF](replays/vc33-level-2.gif) | [PNG](replays/vc33-level-2.png) |

The clips use the recorded 64 × 64 grids and the evaluated harness's color
palette, enlarged with nearest-neighbor scaling. The initial image is the
settled board at the start of the level. Every subsequent action and its
animation frames are retained, including the transition into the next level.
Identical consecutive images share a combined display duration.

Playback uses fixed display timing: 240 ms for each action's final frame,
60 ms for intermediate animation frames, 900 ms at the start and 1,800 ms at
the end. This removes inference waiting time; it does not depict elapsed run
speed. Titles and progress labels are added outside the game grid. No model
reasoning is included in the rendered images.

## Full game replays

| Game and version | Levels completed | Actions | Replay |
|---|---:|---:|---|
| ar25-0c556536 | 8 | 258 | [Watch](https://arcprize.org/replay/74077944-f734-4895-adce-ae20e4d916fc) |
| bp35-0a0ad940 | 9 | 423 | [Watch](https://arcprize.org/replay/bcd43d66-ac98-43c2-8221-f6e872c7d1c2) |
| cd82-fb555c5d | 6 | 81 | [Watch](https://arcprize.org/replay/20fcc634-9e4e-4c3d-a638-b577b0301cd1) |
| cn04-2fe56bfb | 6 | 187 | [Watch](https://arcprize.org/replay/cd3a47ef-0a45-46a0-aae0-9f9f7b4ff8e7) |
| dc22-fdcac232 | 6 | 442 | [Watch](https://arcprize.org/replay/20d26669-51a5-4d89-9e35-9fc329abc363) |
| ft09-0d8bbf25 | 6 | 75 | [Watch](https://arcprize.org/replay/2ad74623-b639-46bc-b86a-81d14c4b5cab) |
| g50t-5849a774 | 7 | 297 | [Watch](https://arcprize.org/replay/4dbaf973-d3af-4aac-a325-0f0f8a4041e6) |
| ka59-38d34dbb | 7 | 325 | [Watch](https://arcprize.org/replay/9c9af5ce-b61a-4b87-ace9-8650e84907d6) |
| lf52-271a04aa | 10 | 710 | [Watch](https://arcprize.org/replay/79127723-14e2-4d3d-a60c-9a45e99e6575) |
| lp85-305b61c3 | 8 | 109 | [Watch](https://arcprize.org/replay/320e870c-f647-4afb-8ba6-70cd496b540c) |
| ls20-9607627b | 7 | 365 | [Watch](https://arcprize.org/replay/0a9dfe50-1421-45c9-8041-773c58b6b85b) |
| m0r0-492f87ba | 6 | 231 | [Watch](https://arcprize.org/replay/b3c4fd9b-d852-422c-9fe0-35271646bd6d) |
| r11l-495a7899 | 6 | 71 | [Watch](https://arcprize.org/replay/fcf46cc2-5c17-4726-9d64-85e56a0039f2) |
| re86-8af5384d | 8 | 728 | [Watch](https://arcprize.org/replay/e77ef5ea-f632-4b56-abdd-5d857634c408) |
| s5i5-18d95033 | 8 | 243 | [Watch](https://arcprize.org/replay/345b0563-a565-432f-90c5-084882e935ff) |
| sb26-7fbdac44 | 8 | 124 | [Watch](https://arcprize.org/replay/44be6362-a967-4e92-8595-11b82f139e42) |
| sc25-635fd71a | 6 | 137 | [Watch](https://arcprize.org/replay/e495099e-151b-41ec-b146-c1be2f71a589) |
| sk48-d8078629 | 8 | 435 | [Watch](https://arcprize.org/replay/45d858f8-5c84-4994-87dc-f4a88502bdf8) |
| sp80-589a99af | 6 | 129 | [Watch](https://arcprize.org/replay/28db70d6-cd9c-446e-bf30-9a829c12e5ba) |
| su15-1944f8ab | 9 | 114 | [Watch](https://arcprize.org/replay/f6101e88-def8-4e76-a78a-9427745a2385) |
| tn36-ef4dde99 | 7 | 148 | [Watch](https://arcprize.org/replay/22761359-7720-4a5c-acab-4432719a35c5) |
| tr87-cd924810 | 6 | 128 | [Watch](https://arcprize.org/replay/34c9120b-2214-46e2-96e3-45e78d759390) |
| tu93-0768757b | 9 | 195 | [Watch](https://arcprize.org/replay/3893f733-e1bd-4827-93b6-6ff8e64171ee) |
| vc33-5430563c | 7 | 192 | [Watch](https://arcprize.org/replay/c8995261-2fa7-48b4-9fc6-e1624a20697f) |
| wa30-ee6fef47 | 9 | 585 | [Watch](https://arcprize.org/replay/6503caa5-73c0-4b5e-9fdf-9d5d8e6eb176) |

## Reproduce the clips

Install `Pillow==11.3.0` in a separate Python environment, then run from the
repository root:

```sh
python3 -B tools/render_replay_gallery.py \
  --cache /tmp/oy1-replay-cache \
  --output-dir /tmp/oy1-replay-gallery
```

The [renderer](../tools/render_replay_gallery.py) downloads the four public
recordings (about 32 MB), verifies their pinned SHA-256 hashes, game and session
IDs, action counts, final wins and selected level boundaries. It also checks
that the exported GIFs preserve the rendered pixels and display timing.
It makes no model calls. Cached recordings contain whatever replay content
ARC Prize publishes; they are not added to this repository.
