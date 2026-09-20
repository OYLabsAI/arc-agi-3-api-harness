# Method

OY1 wraps a language model in a loop for observing a game, testing an action,
and keeping evidence for the next decision. The evaluated configuration
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

The provider layout puts up to four rolling text-cache boundaries before
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

The published scorecard represents one completed run. Earlier pilots and a run
stopped by its budget are recorded separately in the
[evaluation history](evaluation-history.md), together with full campaign costs.
Scores were not combined.

## Data handling

Original action and usage evidence is retained privately. `store=False`,
`background=False` and a requested cache TTL do not establish a protected-data
retention agreement. Organizer live mode remains disabled pending the actual
dataset interface and agreed handling policy. See the preserved
[data-flow report](../harness/reports/DATA-FLOW.md) and
[current status](compliance.md).
