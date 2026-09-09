# API7: remove the counting dependency and verify saved evidence independently

The solver prompt, tool schemas, perception, memory, action dispatcher and scoring are
preserved. No game solutions or historical action sequences are injected. The official
Markdown model reference gives a 922,000 maximum input-token count, separately from
its 1,050,000 total context. API7 reserves this entire input limit at the highest listed
long-context cache-write rate before each request. With 16,000 output tokens, the
reservation is $24.25; compaction with 20,000 output tokens reserves $24.55.
Valid reported usage releases unused reservation. Actual cost may be much smaller.

No separate token-count request is sent. The former unknown endpoint price is therefore
not applicable. Compaction cadence uses the previous response's input-plus-output usage,
with a 175,000 threshold; it is a context-management decision, not the billing bound.
This is a disclosed transport change, and API score comparability still needs a real run.

scripts/independent_audit.py uses only the Python standard library. It never imports
candidate modules or sends network requests. It checks externally pinned source/evidence
identities, frame hashes, action-to-tool links, action/transition/observation consistency,
SQLite/JSONL agreement, request/usage/ledger reconciliation, token-cost arithmetic,
per-request bounds and official scorecard consistency. Mutation tests change pixels,
actions, tool arguments, usage, cost, database rows, duplicate JSON and frozen source.

The candidate's stale __version__ value is corrected to agree with its release manifest.
Full runtime identity, live inference, public API 100.0 and organizer requirements remain
NOT SATISFIED. All older source releases and validation attempts are preserved unchanged.
