# Data flow and execution boundary

The evaluator supplies OPENAI_API_KEY and ARC_API_KEY through a private mode-600 file or
Kaggle Secrets. They are absent from command arguments, source, notebook outputs, manifests
and the solver input. Setup dependencies receive neither key. A fresh child HOME excludes
subscription auth, user site packages, saved memories, project instructions and plugins.

During evaluation the controller contacts https://three.arcprize.org for public discovery,
one scorecard, observations, actions and closure. It passes only observed game state through
the existing SDK interface. No game source or human baseline enters the model context.
The first RESET and later actions use the original transport; ambiguous mutations are not retried.

OpenAI traffic goes directly to https://api.openai.com/v1: model lookup,
Responses generation and bounded Responses compaction. Task text/images, tool outputs and encrypted reasoning
state are sent only to this provider. Available model tools are act, inspect, history,
remember, plan and stop. There is no solver shell, browser, network tool, MCP, OY account,
analytics or OY-hosted service. The coordinator's historical audit is outside solver inputs.

Source bootstrap can read the owner's selected HTTPS release URL or private attached ZIP.
PyPI serves pinned dependencies during setup. Linux wheels are hash-locked. Python 3.12 and
Linux x86_64 are the proposed Kaggle target; runtime availability must be checked in Kaggle.

Public-run local artifacts contain observations, replays, task-bearing encrypted response
items, request IDs, usage and action journals. They remain in the evaluator's private output
directory. Ordinary console output contains only compact status. Errors redact keys and
provider response bodies are not printed. No artifacts are uploaded automatically.

store=False, background=False and stateless Responses compaction are configured. These settings are
not a ZDR agreement. Provider abuse monitoring/caching and Kaggle output retention require
separate review. The API account's actual retention settings are unknown. See
[OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data).
Organizer live mode remains disabled until ARC confirms delivery, approved data controls
and protected evidence handling. Synthetic replacement tests do not establish that agreement.
