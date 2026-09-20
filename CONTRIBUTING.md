# Contributing

OY1 is a research release with a frozen implementation and a public evaluation
record. Issues and focused pull requests are welcome.

## Report an issue

Include the commit, operating system, Python version, command or notebook mode,
expected behavior and observed result. For benchmark questions, identify the
game version, run and metric. Share a minimal reproduction and redact API keys,
account identifiers and private model payloads from logs.

## Propose a change

Explain the problem, the resulting behavior and how you checked it. Keep each
PR focused. Documentation corrections should link to the source or recorded
result supporting the change. Check the code, claims and test results before
submitting.

The `harness/` tree, bundled archives, historical evidence and reproduction
notebook identify the evaluated release. Propose runtime experiments as a
separately versioned implementation with its own tests and manifest. Do not
silently modify evaluated files or describe a changed solver as the version
that produced the published score.

## Check a documentation change

From a clean checkout:

```sh
python3 -B tools/verify_release.py
git diff --check
```

The outer `manifest.json` inventories repository files. Update the `bytes` and
SHA-256 fields for changed documentation and add entries for new files, keeping
paths sorted. Never change the evaluated source hashes to make a runtime edit
pass. Keep generated outputs outside the checkout because the verifier checks
its complete file inventory.

For runtime verification, follow [the reproduction guide](docs/reproduction.md).
The default fixture makes no model calls. Paid evaluations need an explicit
budget and run configuration; include both successful and failed attempts in
any result report.
