# OY1 AGI · ARC-AGI-3 API harness

An observation-driven controller for ARC-AGI-3 using **OpenAI gpt-6-astra**,
high reasoning effort and the Responses API.

| Completed public run · 2026-09-09 | Result |
|---|---:|
| Raw public score | **100.0** |
| Games won / levels solved | **25/25 · 183/183** |
| Recorded inference cost | **USD 415.37** |
| Notebook runtime | **6 h 48 min** |
| Standalone evidence consistency checks | **37,704 passed** |

The [published Competition Mode scorecard](https://arcprize.org/scorecards/75d9c8e7-ade9-4a8f-a747-6acbea51bb1b)
records this single live API run. The public games were used during development.
The consistency checks are a separate software audit of the retained evidence;
they are not an ARC Prize verification or a protected/held-out evaluation.

**Community listing: NOT SATISFIED.** This source release is prepared for
community submission; maintainer acceptance is pending. See
[submission status](docs/compliance.md).

## Approach

The controller combines the current screenshot with exact earlier pixel grids,
evidence-linked memory and a graph of transitions observed within the current
game. It checks predictions while executing short action batches. API9 places
the text history before the current image and maintains bounded cache markers
and provider reasoning continuity across decisions.

The released system includes the shared prompt, tool implementations, provider
adapter, budget controller and evidence checks. There is no per-game solution
table or generated-solution archive required to run it. Read the
[method and contribution](docs/method.md#contribution-and-generality) and
[2026 community references](docs/references.md#2026-community-entries).

## Start here

```sh
git clone https://github.com/OYLabsAI/arc-agi-3-api-harness.git
cd arc-agi-3-api-harness
python3 -B tools/verify_release.py
```

The command checks the release locally without credentials, installation or
API calls.

For the synthetic fixture or a separately authorized benchmark run, follow
[reproduction instructions](docs/reproduction.md) and use
[reproduce.ipynb](notebooks/reproduce.ipynb). The default fixture needs no API
keys. The licensed source bundle is included, so review does not depend on a
public GitHub release.

## Contents

| Path | Purpose |
|---|---|
| [harness/](harness/) | Exact evaluated source, configuration, tests and original manifest |
| [notebooks/](notebooks/) | Reproduction wrapper with explicit fixture/paid modes |
| [docs/method.md](docs/method.md) | Controller design, configuration and all prior attempts |
| [docs/results.md](docs/results.md) | Per-game scores, runtime, actions and cost accounting |
| [docs/compliance.md](docs/compliance.md) | Every remaining requirement marked NOT SATISFIED |
| [docs/community-submission.md](docs/community-submission.md) | Community entry fields and review process |
| [evidence/](evidence/) | Shareable result summaries and exact historical notebook |
| [assets/](assets/) | Hash-pinned evaluated source plus license bundle |
| [licenses/](licenses/) | Original notices from all 46 locked dependency wheels |

All 74 evaluated source files are preserved byte-for-byte. The source's stale
packaging version and historical pre-run reports are explained in the
[identity notes](docs/reproduction.md#source-identity-and-metadata). The review
wrapper is separately identified and has not produced another benchmark score.

Original credentials, invoices, account exports, action/observation logs and
reasoning payloads remain outside this repository. The earlier incomplete
79.2 result is disclosed separately; scores were not merged.

## License and attribution

Copyright 2026 **Orca Labs sp. z o.o.** Licensed under [Apache-2.0](LICENSE).
See [NOTICE](NOTICE) and [third-party notices](THIRD-PARTY-NOTICES.md).
Historical controller/team names are OY1 AGI / OY Labs. See [CITATION.cff](CITATION.cff)
for software attribution and [documentation references](docs/references.md).
