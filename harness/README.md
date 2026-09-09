# OY1 AGI — private API candidate

Version 0.3.1+api2. Prepared from the audited 0.2.7+oy1.1 public subscription repeat.
This API candidate has no measured benchmark score yet. Use the API entry point below.

The full public entry point now fails its performance gate unless one correctly
attributed API attempt has raw official 100.0, all 25 exact games won and all 183 levels.
Execution completion alone cannot pass. The read-only `arc_harness.public_acceptance`
command can independently check saved score/result evidence using a separately supplied
expected source digest. This score gate does not establish full submission compliance.
The API entry point checks every manifest-listed source, plan, dependency lock, script,
test and report before launch, model requests, game actions and finalization. It saves
the complete release in each attempt. A paid launch requires the separately reviewed
release-manifest SHA-256; outputs and approved plans stay outside the frozen tree.
These are file-integrity checks, not proof of an immutable operating environment.
The separately delivered notebook has its own pinned hash in DELIVERY-MANIFEST.json.

Reports inherited from api1 describe the prior preparation; current review is in
`reports/PRELAUNCH-REVIEW.md`. This working revision still has open prelaunch requirements.

## Local checks (no secrets, inference or real scorecard)

Use Python 3.12 in a fresh virtual environment and install requirements.lock.
On Linux x86_64 use requirements-linux.lock with pip --require-hashes --only-binary=:all:.
Run from this source directory:

```sh
python -m arc_harness.api_run check --plan plans/pilot.json
python -m arc_harness.api_run fixture --plan plans/pilot.json --output /tmp/oy-fixtures
python -m pytest -q
```

The fixture uses a synthetic corridor; it is not an ARC result. Linux dependency wheels
were retrieved and hash-pinned. Actual Linux/Kaggle execution is still pending.

## Private pilot, after key and spending authorization

The proposal is at most $25, 30 paid requests, one hour including setup and cleanup,
one attempt at ar25-0c556536. Both OpenAI and ARC API keys are required. The pilot can
end before completing the game. Providing a key alone does not fill the approved budget.

1. Copy plans/pilot.json to a private location, make dataset an absolute path to
   plans/pilot-games.json, and record the approved_usd and approval_record after approval.
2. Run scripts/credential_setup.py with a private JSON destination outside this release.
   It prompts without echoing and creates a new file with mode 600. No evaluation starts.
3. Run using the candidate virtual environment:

```sh
python scripts/run_private.py --credentials /private/path/keys.json --plan /private/path/approved-pilot.json --output /private/path/api-runs --expected-release-sha256 REVIEWED_MANIFEST_SHA256
```

No Codex subscription login is loaded. The API entry point rejects missing caps,
missing keys, model changes and missing exact game versions. Ambiguous paid requests
retain their reservations and stop. Ambiguous game actions are never replayed.

## Notebook

Open the separately delivered verification.ipynb. Its default is a synthetic fixture.
Attach the private source ZIP and set source_archive to its location; the archive hash
and Linux lock hash are already pinned. Internet access and Python 3.12 are required.
For an authorized pilot, select mode=run, supply the approved cap and record, and enable
Kaggle Secrets OPENAI_API_KEY and ARC_API_KEY. Secrets are read only after installation.
Do not publish task-bearing outputs. Public immutable source/notebook URLs are pending.

The timer starts before setup. The bootstrap makes a fresh venv and empty HOME, installs
pinned dependencies, launches the same API entry point, preserves its exit status, and
bounds termination/cleanup. An interrupted evaluation gets a new identifier on any later
launch; outputs from separate attempts are never combined.

## Evidence and limitations

Each attempt saves source/configuration identity, a SQLite cost ledger, per-game event
journals, observations, opaque API output items, replays, usage, action/level exports,
a final scorecard when closure succeeds, an audit, and a file hash manifest. These
artifacts contain task content and remain private. The audit checks recorded consistency,
not hidden reasoning or a general intelligence claim. Billed totals require reconciliation
with the provider invoice.

The API transport preserves the original solver prompt plus native tool-name suffix,
perception, tools, memory and game-action logic. It changes native continuous-turn
execution to explicit Responses calls and bounded Responses compaction. Automatic model retries
are disabled. Performance parity with the subscription result is unestablished.

Organizer live mode deliberately fails pending the actual ARC task-delivery and retention
agreement. Replacement synthetic identifiers are supported for local interface tests.
No private task format, source publication, license, or ARC verification is assumed.
