# API6 change review — 9 September 2026

API5 is preserved unchanged. API6 replaces the standalone compact endpoint with
Responses generation carrying a final compaction_trigger and max_output_tokens=20000.
The existing SDK serializes this item correctly under mocked HTTP. The request uses
high reasoning, Standard, disabled truncation and storage, and no background execution.
Responses must report completed status, the requested model/effort/tier, valid usage,
and only compaction items before state replacement. Returned encrypted items remain intact.
This changes the transport and can change performance; no public result is inferred.

Input-count dispatches now have durable pending records before network access. Receipts
include the request-body hash, provider request ID and returned count. Failures persist
without raw error bodies and prevent further dispatch. Counting and generation share the
operation limit. Counting charges remain unknown, so cost coverage is explicitly incomplete;
the paid-launch guard and live acceptance remain closed. The consistency auditor pairs
counting receipts with per-game events, including count values and request identity.

The documented compaction output control is resolved. Live feature evidence, complete
billing coverage, independent full action/usage audit, full runtime identity, measured
public API score and all remaining submission requirements are NOT SATISFIED.
See PROVIDER-BILLING-REVIEW.json for official sources. No paid traffic was used for validation.
