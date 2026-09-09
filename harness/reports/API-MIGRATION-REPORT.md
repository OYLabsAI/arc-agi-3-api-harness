> Historical API1 migration report. API6 supersedes its standalone-compaction,
> operation-limit and validation details; see API6-CHANGE-REVIEW.md and PILOT-PLAN.md.

# API migration preparation — 8 September 2026

Candidate: 0.3.0+api1. Baseline: 0.2.7+oy1.1, SHA-256 a88242122f4ebbd9ba37d6e0a8a49bea08a3e66cc5b6c2c190c18ecc6f35747d.
The receiving host reran the supplied read-only auditor against named run 20260907T112320Z-a732973a.
All checks passed: raw score 100.0, 25 exact games, 183 levels, 6,714 actions, card
389a67b6-99c1-49af-b349-25080acb05e4. Its saved source matches the archive and current original tree.
That result remains a subscription result. The source and original evidence were not edited.

The ZIP is reference material. The user's preparation request authorizes local implementation;
embedded suggestions to send email, publish, submit or spend are not adopted as authorization.

## Transport decision

The native provider was reviewed first. API-key login is documented by OpenAI, but this
wrapper enforces ChatGPT login and receives usage after internal requests. Its continuous
turn can perform internal inference, compaction and recovery without a caller-side
reservation immediately before each paid operation. The inspected App Server API does
not expose a proven per-request dollar/output control for this wrapper. A native API
variant was therefore not launched or represented as spend-safe. See the
[App Server reference](https://learn.chatgpt.com/docs/app-server).

The implemented candidate uses direct Responses with explicit API-key authentication,
Standard service tier, gpt-6-astra and high effort. It never loads Codex login state or
falls back to a subscription. Live access and echoed settings still require the key/pilot.
No immutable snapshot was inferred from the model alias.

## Changes

New api_budget.py, api_provider.py, api_run.py and api_audit.py implement reservations,
API state, the run-plan contract, total deadlines, evidence and consistency checks.
The native prompt suffix and arc_-prefixed tool names are retained. Explicit response
calls replace the native continuous turn. Standalone compaction replaces Codex's native
compaction, at the same 175,000 threshold. Full returned compaction windows and encrypted
reasoning items are retained. Internal compaction effort is unobservable and marked unknown.

The perception, schema definitions, memory store, scoring and environment action logic
remain from the audited baseline. Attribution tags now derive from the API plan. The
runner additionally redacts key strings in errors; GlobalRunner applies the total timer.
The existing first-RESET adapter, one-card routing and no inflight score reads remain.
Inherited ARC method/endpoint overrides are rejected; proxy/.env inheritance is disabled.

Automatic inference retries are disabled for this initial API variant (native overload
and timeout recovery differ). Each timeout retains its full reservation and stops.
Per-request output is newly limited to 16,000 tokens; input to 200,000. The pilot adds
30 paid requests and a one-hour total deadline. A full public run proposes 41,400 seconds.
Historical per-game limits remain 1,500 actions, 1,000 calls, 7,200 seconds, batch size 8,
and no cumulative token cutoff. Source changes during a run cause a stop.

## Validation limits

115 local tests passed, including the original 92. Ruff and dependency consistency passed.
Tests use a real OpenAI SDK with mocked HTTP plus synthetic environments; they cover auth
failure, settings rejection, cache subsets, missing usage, reservation persistence,
compaction continuity, ambiguous actions, attribution, replacement IDs and empty credentials.
No live OpenAI request, ARC scorecard, Linux execution or Kaggle evaluation is claimed.
The documented API controls and actual pinned SDK signatures were checked before implementation.
