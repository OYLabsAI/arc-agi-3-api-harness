# Contributing

Issues and focused pull requests are welcome.

For a bug report, include the commit, operating system, Python version, command,
expected behavior and actual result. For a benchmark question, identify the game
version, run and metric. Remove credentials and private model payloads from logs.

A pull request should explain the problem, the change and how it was checked.
Documentation claims should link to the source or recorded result.

## Checks

```sh
python3 -B tools/verify_release.py
git diff --check
```

For source changes, install the locked dependencies in a separate Python 3.12
environment and run the tests from `harness/`:

```sh
python -B -m pytest -q -p no:cacheprovider
```

Update `harness/RELEASE-MANIFEST.json` when maintained source files change, then
update the outer `manifest.json`. Keep paths sorted and record file sizes and
SHA-256 hashes. Generated outputs belong outside the checkout.

The evaluated snapshot in `evidence/evaluated-source.json` stays pinned to the
published run. If a solver file changes, it must no longer be listed as unchanged
from that snapshot. Report new benchmark results separately and include the exact
source commit, model configuration, game versions and cost accounting.

See the [reproduction guide](docs/reproduction.md) for running the evaluated
snapshot. Paid runs require credentials and an explicit spending cap.
