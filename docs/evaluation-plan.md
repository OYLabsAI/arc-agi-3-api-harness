# Proposed evaluation on unfamiliar games

**Status: planned, not executed.** The existing result is on public games used
during development. This protocol would test transfer to unfamiliar games and
whether OY1's mechanisms explain any improvement. No new score or spending
authorization is implied.

## Questions

1. Can the frozen harness solve games that were not used to develop it?
2. How do completion, actions, time and inference cost compare with a matched
   baseline?
3. Which mechanisms matter: exact visual recall, evidence-linked memory or
   checks during action batches?

## Freeze before selecting the evaluation set

Record source commits, dependencies, model/provider version, reasoning effort,
service tier, prompt, tool schemas, context/compaction settings and limits.
Use an independent evaluator to select and withhold the games until these
choices are fixed. Keep separate development and evaluation sets; any tuning
on evaluation feedback requires a new untouched set for the next claim.

Game source and solutions must remain inaccessible to the solver. Record exact
game versions, selection criteria and any known prior exposure. Third-party
synthetic games can test transfer but are not automatically equivalent to the
ARC protected set or proof of absence from model training data. Organizer data
requires the separate integration and handling agreement described in
[release status](compliance.md#organizer-verification).

## Comparisons

| Condition | Purpose |
|---|---|
| Full OY1 | Measure the frozen system on the new set |
| Declared reference harness | Compare systems with the same model, game versions, observations, permitted actions and budget ceilings |
| OY1 without earlier-observation retrieval | Test the contribution of exact visual recall |
| OY1 without persistent memory notes | Test the contribution of evidence-linked memory |
| OY1 without prediction-mismatch interruption | Test that stop condition while preserving legality, budget and terminal-state controls |

The ablations are proposed variants, not existing validated modes. Implement
and test them separately, record their commits, and document all differences,
including resulting prompt and token-usage changes. Keep the evaluated
source intact. Do not assume ablation effects add together.

## Pre-register the run

Complete this record before any paid execution:

| Field | Required decision |
|---|---|
| Evaluator and dataset | Owner, game/version list, selection process, exposure audit |
| Systems | Full OY1 commit, reference harness commit, ablation commits |
| Inference settings | Exact model/provider, reasoning effort, service tier and pricing basis |
| Repeats | Number of independent repeats per game and condition, seeds where supported, execution order |
| Limits | Per-game actions, model calls, wall time and cost; total campaign cap |
| Stop and error rules | Treatment of API failures, uncertain actions, budget exhaustion and incomplete games |
| Primary metric | Predeclared completion metric; separate definition of any action-efficiency score |
| Evidence | Storage, access policy and publishable summaries |

The current release's public-game limits are 1,500 actions, 1,000 model calls,
7,200 seconds and batches of at most eight actions per game. These are a
reference, not a recommendation for an unselected dataset. Choose limits and
reserve enough budget for all conditions and repeats before starting.

## Report every attempt

Publish per-game and aggregate completion, levels solved, action counts,
runtime, inference cost, cache usage and failure reasons. Distinguish decision
calls from compaction and other billed operations. Include stopped and failed
runs, setup overhead, all campaign spending and successful-run cost separately.

Report repeat-to-repeat variation and paired comparisons on the same games.
A single successful run is not enough to attribute an improvement to one
component. Retain original outcomes and never combine several attempts into a
single scorecard. Describe withheld evidence explicitly.

The current [231-test Linux fixture](../evidence/linux-fixture.json) checks
software behavior. It is not this evaluation, and no execution date or result
is claimed for the proposed study.
