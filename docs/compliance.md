# Release and evaluation status

The public source, completed Competition Mode scorecard and reproduction
fixture are available. The [community submission](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/pull/56)
awaits maintainer review. There is no organizer-verified or held-out result.

## Available evidence

| Item | Evidence and scope |
|---|---|
| Public benchmark | [Scorecard](https://arcprize.org/scorecards/75d9c8e7-ade9-4a8f-a747-6acbea51bb1b): 100.00%, 25/25 games, 183/183 levels and 6,732 actions. The original card records Competition Mode. |
| Producing system | All 74 evaluated files, prompt, tools, configuration, locked dependencies and reproduction entry point are public. |
| Source identity | Evaluated file hashes and original source archive are retained. The reproduction wrapper is separately identified. |
| Linux fixture | [Receipt](../evidence/linux-fixture.json): 231 tests and a synthetic fixture completed in 74.90 seconds, with zero API operations and zero charged or reserved cost. |
| Cost accounting | $415.37 for the successful run; original provider exports and invoices reconciled privately. |
| License | Orca Labs sp. z o.o.; Apache-2.0 for the source, with separate third-party notices. |
| Community metadata | [Submission PR](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/pull/56) contains the method, author, version, model, cost and public scorecard URL. |

The fixture checks software behavior; it is not another benchmark run. Kaggle
reformatted notebook JSON and source arrays during the historical fixture.
Saved cell text and normalized notebook content matched the supplied wrapper;
both file hashes are recorded in the receipt.

## Known limitations

- **Development exposure:** the public games were used during development.
  Performance on unfamiliar games has not been established.
- **Attribution:** no matched comparison or component ablation isolates which
  design choices caused the result or establishes a cost advantage.
- **Public evidence:** raw action/observation logs, provider exports, invoices
  and reasoning payloads are outside this repository. The public summaries
  do not constitute an independent replication.
- **Packaging version:** frozen `pyproject.toml` says `0.3.6+api7`, while the
  evaluated manifest and run identify `0.3.8+api9`. This discrepancy is preserved
  to retain source identity; the documented bootstrap executes that frozen
  source directly. See [identity notes](reproduction.md#source-identity-and-metadata).
- **Historical runtime inventory:** a contemporaneous full interpreter,
  standard-library and installed-file inventory is unavailable. Source, locked
  wheel hashes, saved code and the pinned container are recorded.

## Community review

[PR #56](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/pull/56) is open.
The maintainers review the method for generality, openness and novelty under
their [submission requirements](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/blob/main/CONTRIBUTING.md).

## Organizer verification

ARC Prize verification is separate from community listing and has not been
completed. It requires an agreed evaluator setup, dataset interface and data
handling policy, followed by organizer evaluation. Protected execution remains
disabled in this release. See [ARC policy](https://arcprize.org/policy).

Reports in `harness/reports/` retain their status at the time they were written.
The completed result is in [public-run.json](../evidence/public-run.json).
