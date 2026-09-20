# Reproduction

The notebook uses the exact source snapshot from OY1's completed run on
**9 September 2026**. The maintained source is available under `harness/`.

## Check the checkout

Python 3.9 or newer is sufficient for release verification:

```sh
python3 -B tools/verify_release.py
```

This checks the file inventory, source manifests, unchanged solver files and
notebook syntax. It makes no network or model calls.

## Run the notebook

Open [reproduce.ipynb](../notebooks/reproduce.ipynb) in a private Kaggle notebook
or a Linux Jupyter environment. Use **Linux x86_64, Python 3.12, CPU**, with
internet access. No GPU or local model weights are needed.

The notebook downloads a pinned source bundle and verifies its SHA-256 before
executing it. Its default `MODE="fixture"` installs the locked dependencies and
runs a synthetic check without credentials or inference charges.

For a new public benchmark run:

1. Set `MODE="run"`.
2. Set `APPROVED_USD` to your spending cap and `APPROVAL_RECORD` to its authorization record.
3. Add evaluator-owned `OPENAI_API_KEY` and `ARC_API_KEY` through Kaggle Secrets.
4. Run all cells and retain the output directory printed by the notebook.

Paid mode uses GPT-6 Astra, high reasoning and Standard service. The plan selects
the same 25 exact game versions and allows up to 11.5 hours and 26,000 model
operations. Per-game limits are 1,500 actions, 1,000 calls and two hours.
The completed run cost $415.37; a new run may cost a different amount. Cost
reservations can stop a run before it reaches the cap.

Paid mode currently uses Kaggle Secrets. Never put credentials in notebook source.
Keep original logs and model payloads private; publish result summaries and replay
links. Each execution creates a separate run and scorecard.

## Use a local source bundle

To download and verify the evaluated bundle separately:

```sh
python3 -B tools/fetch_evaluated_source.py --output /tmp/oy1-evaluated-source.zip
python3 -B tools/verify_release.py --evaluated-bundle /tmp/oy1-evaluated-source.zip
```

Set `BUNDLE_PATH` in the notebook to the downloaded file. For a Kaggle dataset
attachment, rename the file to `oy1-evaluated-source.bin` before uploading to
prevent automatic ZIP extraction. Renaming does not change its bytes or hash.

## Source identity and metadata

The [source record](../evidence/evaluated-source.json) pins the evaluated bundle,
its source archive, manifest and original notebook to an immutable repository
commit. The reproduction notebook always runs that snapshot.

The maintained checkout updates documentation, package metadata and diagnostic
messages. The prompt,
model adapter, perception, memory and action loop retain their evaluated bytes.
The source record lists unchanged files and their hashes. These maintenance
changes are not a new benchmark run.

The source manifest used for the reported result is:

```text
84a784778cf0a2b01d5f93380445b050b4bbee56fbb865d6e8bf4ebd9cde1053
```

The [recorded Linux installation check](../evidence/linux-fixture.json) identifies
the evaluated wrapper and runtime used for that check. It is separate from the
benchmark result. The original full run used Kaggle's image
`gcr.io/kaggle-images/python@sha256:dafd4ce5668bbf1ad422e4c109e0f18c9623c3a7c7f48b0235f13142755c40b9`.

## Troubleshooting

| Issue | Resolution |
|---|---|
| Inventory or hash mismatch | Use a clean checkout. Keep generated files and run outputs outside it. |
| Unsupported notebook platform | Select Linux x86_64 with Python 3.12. |
| Source download unavailable | Download the pinned bundle separately and set `BUNDLE_PATH`. |
| Paid mode cannot find credentials | Add both keys through Kaggle Secrets. |
| Run stops below its spending cap | Check the cost reservations and remaining budget in the output. |

Protected organizer evaluation requires a separate dataset interface and data
handling arrangement. [Evaluation scope](compliance.md).
