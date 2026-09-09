# Cost preparation — 8 September 2026

New paid inference: zero requests; new scorecards: zero. No API invoice exists for this candidate.
The source plan requires an external per-run approval record. The owner authorized use of
the existing $25 for a pilot; any additional full-run funding will be prepared separately.

[Published Astra pricing](https://developers.openai.com/api/docs/models/gpt-6-astra) was
rechecked: per million, $10 input, $1 cache reads, $12.50 cache writes, $50 output.
Long-context requests above 272K multiply input/cache rates by 2 and output by 1.5.
Fast is disabled. Cached input and reasoning output are subsets and are never added twice.

For scale only, repricing the historical named subscription usage (179,383,638 input,
175,351,552 cached input, 547,532 output) gives $243.05 at its reported cache mixture,
$1,821.21 with uncached input, $2,269.67 if every input token incurred the cache-write rate,
or $4,525.66 if that last scenario also used long-context rates. These are hypothetical
arithmetic scenarios, not quotes, measured API estimates, or invoices. The API transport
may change input volumes, caches, compaction, latency and rate-limit behavior substantially.

The ledger stores integer micro-USD, request IDs, raw usage, pending reservations and
estimated/conservative charge separately from billed_usd (null until invoice reconciliation).
It is shared across a single sequential worker and all games. Concurrent workers are not
supported. A stopped request is never retried automatically. A new run uses a new directory;
a pending ledger cannot be reopened as an empty budget.

API7 makes no remote token-counting request. It reserves the documented maximum input
of 922,000 tokens at the highest published long-context cache-write rate, plus the
configured output cap at the highest output rate: $24.25 for normal responses and
$24.55 for bounded compaction. Published token reservations are SATISFIED for this
transport. Actual usage settles each reservation; uncertain usage retains it and stops
subsequent requests. A usage bound violation is recorded and also stops further traffic.
The source for the maximum input is the official Markdown model specification:
https://developers.openai.com/api/docs/models/gpt-6-astra.md .

Counting-endpoint pricing is NOT APPLICABLE to API7 because that endpoint is never
invoked. Actual provider feature acceptance, invoice reconciliation, and full submission
acceptance remain NOT SATISFIED until supported by their own evidence. No paid external
compute or OY backend is provisioned. Kaggle quotas/charges need evaluator confirmation.

A measured full-run estimate, rate-limit plan and requested cap follow the authorized pilot.
Provider dashboard alerts are supplementary; they do not replace application reservations.
