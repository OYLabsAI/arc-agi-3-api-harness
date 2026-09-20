# Method

OY1 wraps a language model in a loop for observing a game, testing an action,
and keeping evidence for the next decision. The evaluated API9 configuration
uses OpenAI gpt-6-astra through the Responses API, high reasoning effort and
Standard service.

## Contribution and generality

The proposed contribution is the combination of exact visual recall,
evidence-linked memory and action batches that stop when a checked prediction
fails. The model can retrieve an earlier observation instead of relying only
on a summary, and a failed expectation returns control before the rest of the
sequence executes.

The same solver prompt, tools and provider configuration serve every selected
game. Game IDs select environments, not solution branches. History and memory
start fresh for each game. The solver receives no game source, historical
solutions, human action baselines, shell, browser or arbitrary Python tool.
See the shared [prompt](../harness/arc_harness/prompt.py).

History and hypothesis checking are not individually new ideas. Tycho and
baseline1 describe executable world-model construction; Retrodict describes
hypothesis checks over recorded history. OY1's model-facing interface retrieves
observations and checks action predictions without exposing a tool for writing
or executing a simulator. Its optional planner searches observed transitions.
These are architectural distinctions, not evidence of superiority. See
[related work](references.md#2026-community-entries).

The public games were used during development. No controlled cross-harness
comparison or component ablation establishes which choices caused the result.
The [follow-up evaluation plan](evaluation-plan.md) describes how to test those
questions on unfamiliar games.

## Observation and context

Each decision includes the current screenshot and an exact pixel grid.
Earlier images are represented as complete hexadecimal grids in retained text
history. Full observations, animation frames and transitions remain in the
per-game store for retrieval.

The API9 provider layout puts up to four rolling text-cache boundaries before
the current image. It retains opaque provider reasoning items across decisions
and uses bounded Responses compaction. Compaction is lossy: the latest exact
observation is restored afterward, and older observations remain accessible
through `inspect`; they are not guaranteed to stay in model context forever.

The adapter requests a 30-minute minimum cache TTL. This is not a maximum
retention promise. The synthetic probes motivating the layout are preserved in
[API9-CHANGE-REVIEW.md](../harness/reports/API9-CHANGE-REVIEW.md), which predates
the completed run.

## Model-facing tools

| Tool | Behavior |
|---|---|
| `inspect` | Retrieve the current or an earlier observed frame, optionally cropped, as an exact grid. |
| `history` | Search recorded transitions and memory notes. |
| `remember` | Store a hypothesis, supported claim or refuted claim; supported notes require valid observed transition references. |
| `act` | Explore with one action, or execute up to eight actions with predictions for each step. |
| `plan` | Search paths through transitions already observed in this game. Contradictory transitions and RESET edges are excluded. |
| `stop` | End when the environment is won or a budget is exhausted; early stops are rejected while the game is unfinished and budget remains. |

Memory validation checks that the cited transitions exist. It does not prove
the meaning of a claim. The planner is an empirical graph search, not a simulator
of unseen outcomes or a proof that visually identical states are equivalent.
The completed run did not call `plan`.

## Prediction checks

A single action may explore without a prediction. Every step of a multi-action
batch must predict at least one observable: selected pixels, game state or the
number of completed levels. After each action, the runner records the actual
observation and compares it with the prediction.

The remaining batch is interrupted on a prediction mismatch, no observable
change, a level transition or terminal state. Legality and remaining budget are
also checked before executing actions. An uncertain remote action is recorded
as an error rather than silently retried.

For example, imagine a batch of three moves with an expected pixel position
for each step. If the first position differs, the other two moves are not
executed. The model receives the actual result and can retrieve earlier frames
or change its hypothesis. This is an illustrative example, not a benchmark trace.
A matching prediction only validates the fields the model selected; it is not
a guarantee that its whole interpretation of the game is correct.

## Implementation map

| Module | Responsibility |
|---|---|
| [`runner.py`](../harness/arc_harness/runner.py) | Tool dispatch, action loop, predictions and batch interruption |
| [`store.py`](../harness/arc_harness/store.py) | Observations, evidence-linked memory and empirical planning |
| [`perception.py`](../harness/arc_harness/perception.py) | Grid descriptions, differences and prediction checks |
| [`api_provider.py`](../harness/arc_harness/api_provider.py) | Provider requests, reasoning items, caching, compaction and usage |
| [`api_budget.py`](../harness/arc_harness/api_budget.py) | Cost reservations, accounting and stop bounds |
| [`bootstrap.py`](../harness/scripts/bootstrap.py) | Fresh environment, installation and supervision |
| [`independent_audit.py`](../harness/scripts/independent_audit.py) | Result and evidence consistency checks |

## Attempt history

| Attempt | API operations | Recorded USD | Outcome |
|---|---:|---:|---|
| API7 pilot | 6 | 0.980586 | Budget stop, 1/8 levels |
| API8 pilot | 49 | 51.284389 | Budget stop, 7/8 levels |
| Four synthetic cache probes | 23 | 0.497276 | Compared cache layouts; no public benchmark score |
| API9 pilot | 48 | 11.083319 | First public game solved, 8/8 levels |
| First full API9 run | 1310 | 300.862333 | Budget stop; raw 79.2, 19 wins, game 20 at 8/9, five unrun |
| Second full API9 run | 1773 | 415.367944 | Raw 100.0, 25 wins, all 183 levels; 37,704 evidence consistency checks passed |

Nine historical Linux fixtures were attempted: the first two failed during setup
and versions 3–9 passed their applicable checks. The final API9 fixture ran 231
tests. One later full-notebook setup failed before inference because the Secrets
path was unavailable. Version 12 was a preparation save, not an evaluation. The
completed full run was saved version 13, run 20260909T110238Z-ce055081. No scores
were combined. The earlier subscription run is a separate historical reference;
its repriced usage was not an API invoice or a reliable budget prediction.

After the benchmark, the community-release wrapper passed a separate Linux
fixture: 231 regression tests, no API operations and no inference cost. Its
[receipt](../evidence/linux-fixture.json) identifies that packaging check; it
does not add another benchmark attempt or alter the campaign cost below.

The campaign totals 3,209 API operations. Provider consumption was USD 780.075046;
the conservative per-request ledger totals USD 780.075847. The USD 0.000801
difference is fully explained by rounding each request upward to micro-USD.
The successful run's unrounded usage calculation is USD 415.3674960. Original
provider exports, paid credit invoices, raw scorecard and action/usage evidence
are retained privately. Credit purchases and VAT are separate from token costs.

The review wrapper changes source retrieval and requires a fresh evaluator
approval record for paid runs. The source manifest and all 74 evaluated files
are unchanged. Review wrapper checks are software validation, not another paid
100-point run. The public result does not establish ARC Prize verification.

## Data handling

Original action and usage evidence is retained privately. `store=False`,
`background=False` and a requested cache TTL do not establish a protected-data
retention agreement. Organizer live mode remains disabled pending the actual
dataset interface and agreed handling policy. See the preserved
[data-flow report](../harness/reports/DATA-FLOW.md) and
[current status](compliance.md).
