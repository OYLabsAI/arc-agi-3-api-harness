# Evaluation history

| Attempt | Provider operations | Recorded USD | Outcome |
|---|---:|---:|---|
| First pilot | 6 | 0.980586 | Budget stop, 1/8 levels |
| Second pilot | 49 | 51.284389 | Budget stop, 7/8 levels |
| Four synthetic cache probes | 23 | 0.497276 | Compared cache layouts; no public benchmark score |
| Final-configuration pilot | 48 | 11.083319 | First public game solved, 8/8 levels |
| First full run | 1310 | 300.862333 | Budget stop; raw 79.2, 19 wins, game 20 at 8/9, five unrun |
| Completed full run | 1773 | 415.367944 | Raw 100.0, 25 wins, all 183 levels; 37,704 evidence consistency checks passed |

Nine historical Linux fixtures were attempted: the first two failed during setup
and versions 3–9 passed their applicable checks. The final fixture ran 231
tests. One later full-notebook setup failed before inference because the Secrets
path was unavailable. Version 12 was a preparation save, not an evaluation. The
completed full run was saved version 13, run 20260909T110238Z-ce055081. No scores
were combined. The earlier subscription run is a separate historical reference;
its repriced usage was not an inference invoice or a reliable budget prediction.

After the benchmark, the community-release wrapper passed a separate Linux
fixture: 231 regression tests, no Provider operations and no inference cost. Its
[receipt](../evidence/linux-fixture.json) identifies that packaging check; it
does not add another benchmark attempt or alter the campaign cost below.

The campaign totals 3,209 Provider operations. Provider consumption was USD 780.075046;
the conservative per-request ledger totals USD 780.075847. The USD 0.000801
difference is fully explained by rounding each request upward to micro-USD.
The successful run's unrounded usage calculation is USD 415.3674960. Original
provider exports, paid credit invoices, raw scorecard and action/usage evidence
are retained privately. Credit purchases and VAT are separate from token costs.

The review wrapper changes source retrieval and requires a fresh evaluator
approval record for paid runs. The source manifest and all 74 evaluated files
are unchanged. Review wrapper checks are software validation, not another paid
100-point run. The public result does not establish ARC Prize verification.

These records distinguish successful-run inference cost from the cost of the
full evaluation campaign. They do not change the published scorecard.
