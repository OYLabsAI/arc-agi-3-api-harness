# Method and scope

OY1 AGI wraps a general-purpose reasoning model with an observation-only ARC action loop.
Perception summarizes observed colors/components and exact grid rows. Actions can batch
up to eight with explicit predictions; batches stop on prediction failure, no visual change,
level transitions or terminal states. Memory and history are limited to the current game.
The empirical planner searches previously observed transitions only. Only the environment
can establish a win; an unsupported early stop is rejected while game budgets remain.

The API candidate uses the same solver prompt and native tool-name suffix. It preserves
opaque reasoning and complete tool-call/output pairing. API7 requests compaction with a final compaction_trigger through Responses and
an explicit 20,000-token output cap. Only a completed response containing compaction
items can replace the next context; all returned items are retained unchanged. API timeouts stop with reserved
cost instead of the native provider's recovery loop. Budgeting and evidence exports are
controller functions, outside the solver's observations.

The public games have been used in previous development and subscription runs. They are
not claimed to be unseen. Historical runs belong to their own versions and scorecards.
There is no game-ID-specific solver branch or solution lookup. Synthetic fixtures test
software plumbing and are never reported as intelligence or benchmark performance.
The API variant's benchmark performance and comparability remain to be measured.

API8 explicitly requests all_turns reasoning continuity and checks the effective response
field before executing a tool. A stable per-game cache key and best-effort cache diagnostics
measure reuse without changing solver-visible inputs. See API8-CHANGE-REVIEW.md.

API9 retains past observations as exact pixel grids and supplies the current screenshot
on each decision. Earlier raster copies are not replayed. It uses up to four explicit
cache boundaries in the text history. This representation change is disclosed in
API9-CHANGE-REVIEW.md and requires a fresh performance measurement.
