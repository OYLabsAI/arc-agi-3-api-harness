# Reproduction and review

## Verify the source release

Clone the public OYLabsAI repository:

```sh
git clone https://github.com/OYLabsAI/arc-agi-3-api-harness.git
cd arc-agi-3-api-harness
python3 -B tools/verify_release.py
```

The verifier uses only the standard library. It checks the manifest, every
file hash, all 74 frozen source files, the source bundle and notebook syntax.
It does not install packages, use credentials, or call an API.

## Synthetic Linux fixture

The runtime requirement is **Linux x86_64, Python 3.12, CPU**, with Internet to
install the 46 hash-locked dependencies from PyPI. The original full evaluation
used Python 3.12.13 and Kaggle's image
`gcr.io/kaggle-images/python@sha256:dafd4ce5668bbf1ad422e4c109e0f18c9623c3a7c7f48b0235f13142755c40b9`.
No GPU or local model weights are required; paid inference uses a remote API.

Import `notebooks/reproduce.ipynb` into a **private** Kaggle notebook. Make an
identical copy of `assets/api9-source-and-licenses.zip` named
`api9-source-and-licenses.bin`, upload that copy as a **private** dataset and
attach it. The `.bin` suffix prevents Kaggle from automatically extracting the
archive; its bytes and required SHA-256 remain identical. For example, from the
repository root:

```sh
cp assets/api9-source-and-licenses.zip /tmp/api9-source-and-licenses.bin
```

Enable Internet, select CPU and the matching Python runtime, and Run All with
`MODE="fixture"`. The notebook discovers a single matching bundle or accepts an
explicit BUNDLE_PATH. Keep only one matching bundle attached. Do not put a GitHub
token or API key in notebook source.

On an existing Linux Jupyter host with Python 3.12 and host pip installed, open
the notebook from this checkout. It also finds the bundle in assets/ relative
to the repository root or notebook directory. Jupyter is only an interactive
host; the bootstrap creates its own fresh environment, installs locked wheels,
and invokes the evaluated entry point with isolated startup.

The default mode executes the regression suite and a synthetic fixture without
inference requests or real scorecards. Its one-hour bound includes setup. The
notebook prints the output directory; preserve its logs and execution receipt.
This wrapper's end-to-end Linux validation is **SATISFIED**: its private Kaggle
check passed 231 tests and the synthetic fixture in 74.90 seconds, with zero API
operations and zero charged/reserved cost. The [execution receipt](../evidence/linux-fixture.json)
records the wrapper and saved-code hashes. This check is separate from both the
historical fixture and the completed paid 100.0 public run.

## Separately authorized public API run

In Kaggle, attach evaluator-owned Secrets `OPENAI_API_KEY` and `ARC_API_KEY`.
The first must have access to `gpt-6-astra` with high reasoning and Standard
service. Set MODE to `run`, an explicit APPROVED_USD cap and APPROVAL_RECORD,
then Run All. Paid mode requires Kaggle Secrets; local-host secret integration
is not supplied by this review wrapper.

The frozen plan selects all 25 exact public game versions in
`harness/plans/public-games.json`, with a 41,400-second total deadline and 26,000
maximum operations. Per-game limits are 1,500 actions, 1,000 model calls, 7,200
seconds and batches of at most eight actions. The historical run used a USD 750
cap and cost USD 415.37. Those figures are not a new spending authorization or
guaranteed future price. Up to USD 24.55 of reservation headroom is required
before another operation; the run can stop before consuming its entire cap.

Keep outputs private. Every attempt must retain its original outcome, errors,
usage and evidence. Never silently resume a stopped scorecard or combine runs.
Organizer/protected execution is disabled pending the actual interface and
retention/data-flow agreement. See [compliance](compliance.md).

## Source identity and metadata

The source manifest is pinned to
`84a784778cf0a2b01d5f93380445b050b4bbee56fbb865d6e8bf4ebd9cde1053`.
The licensed bundle is pinned to
`be904f8b6e72cea0ca469d9bee1697f2fa5927fce8145a345546bc772f687f7d`.
It contains the exact historical source ZIP and its separate license notices.

Do not install the project with an unpinned editable build for reproduction.
The evaluated bootstrap uses the locked environment and direct isolated entry.
The frozen pyproject version is stale (0.3.6+api7); the run/manifest version is
0.3.8+api9. Historical pre-run reports and classification are retained as part
of that exact source identity. A cleanup of those files would create a new
release and must not be claimed as the source that produced this result.
