# API8: live pilot findings

API7 made six completed Responses calls and 16 ARC actions on ar25-0c556536,
clearing one of eight levels before its $25 global reservation stopped the attempt.
Reported usage prices to $0.980586; no uncertain calls remain. Invoice reconciliation
is separate. The immutable API7 attempt is retained, including its failing original audit.

The pilot audit assumed a one-game scorecard. The actual ARC scorecard contains the
selected game plus 24 zero-action catalog placeholders. API8 allows those extra entries
only in pilot scope after checking zero actions, resets, score, completed levels and
per-level arrays, a NOT_FINISHED state, and one placeholder run. Played, duplicate or
malformed extras still fail. The full 25-game raw-100 acceptance gate remains strict.

Only 7,000 of 80,210 input tokens were cache reads in this short pilot. The cause is
not yet established. API8 adds a stable per-game prompt cache key and provider cache
diagnostics against the previous response; it retains implicit caching at its supported
30-minute lifetime. It requests and verifies all_turns reasoning continuity, and records
the effective context and diagnostics. These are disclosed transport changes; the
solver prompt, action semantics, tools, perceptions and memory are unchanged.

Primary references: https://developers.openai.com/api/docs/guides/prompt-caching ,
https://developers.openai.com/api/docs/guides/prompt-caching/diagnostics , and
https://developers.openai.com/api/docs/guides/reasoning . The diagnostics guide states
that comparisons add no separate charge; normal Responses token charges still apply.
API7's maximum-input token reservation contract therefore remains applicable.

Live API8 continuity, caching improvement and compaction acceptance remain NOT SATISFIED.
Complete runtime identity and organizer requirements remain NOT SATISFIED.
