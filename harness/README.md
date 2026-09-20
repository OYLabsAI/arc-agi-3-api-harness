# OY1 source

The completed run on 9 September 2026 scored **100.0** on the ARC-AGI-3 public
set: **25/25 games and 183/183 levels** with GPT-6 Astra at high reasoning.
[Results and replays](../docs/results.md).

| Module | Purpose |
|---|---|
| `arc_harness/runner.py` | Tool calls, action batches and prediction checks |
| `arc_harness/store.py` | Game observations, transitions and memory |
| `arc_harness/perception.py` | Grid rendering and differences |
| `arc_harness/api_provider.py` | Model requests, context and compaction |
| `arc_harness/api_run.py` | Run configuration and execution |
| `config/billing.json` | Token-cost reservation settings |
| `plans/public-repeat.json` | Public benchmark configuration |
| `tests/` | Unit tests |

Use the [reproduction notebook](../notebooks/reproduce.ipynb) to run the exact
evaluated snapshot. The maintained checkout has updated documentation, package
metadata and diagnostic wording; the [source identity](../docs/reproduction.md#source-identity-and-metadata)
records the distinction.

For local development with Python 3.12, install `requirements.lock` in a separate
virtual environment and run `python -B -m pytest -q -p no:cacheprovider` from this
directory. On Linux x86_64, use `requirements-linux.lock` with `--require-hashes`.
Keep run outputs outside this directory so its source manifest stays valid.
