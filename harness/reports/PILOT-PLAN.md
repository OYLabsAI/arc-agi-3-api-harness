# Prepared pilot — requires an external per-run approval record

- Candidate: 0.3.6+api7, source frozen by the release manifest.
- Plan: plans/pilot.json; one selected version, ar25-0c556536 (first in the frozen order).
- OpenAI Responses, gpt-6-astra alias, high effort, Standard, Fast off.
- Proposed cap: $25. approved_usd and approval_record remain null.
- At most 30 generation operations total, including compaction; no automatic retries.
- 3,600 seconds end-to-end, including installation and 180 seconds reserved for cleanup.
- 922,000 maximum input tokens reserved; 16,000 maximum output tokens per inference request.
- Compaction threshold 175,000; Responses compaction_trigger with an explicit 20,000 output cap.
- Per-game comparison limits: 1,500 actions, 1,000 calls, 7,200 seconds, batch size 8.
- One Competition Mode scorecard, pilot attribution; no restart or best-of-game aggregation.

This is a diagnostic sample. It may stop before winning or reaching compaction. It does
not establish a full-game result or a statistically reliable full-run estimate.

The normal request reservation is $24.25 (922K input at $25/M + 16K output at $75/M).
The conservative compaction reservation is $24.55 (same input bound plus 20K output).
Reservations deliberately use long-context cache-write/output rates even below the
272K threshold. No token-count endpoint is invoked. Returned valid usage releases
only the known unused part; missing usage/timeouts retain the entire reservation and stop.
Unknown cache-write details use a conservative input charge, not an assumed zero.

Preflight validates the explicit cap/approval, both keys, model listing access, exact
game availability and isolation before creating a card. Actual inference access, echoed
settings, cache behavior, performance and billed charges are measured during the pilot.
No source, email or public submission action is part of this plan.

Counting charges are NOT APPLICABLE to this transport. Paid token reservations are reviewed in PROVIDER-BILLING-REVIEW.json; actual invoice reconciliation remains separate.
