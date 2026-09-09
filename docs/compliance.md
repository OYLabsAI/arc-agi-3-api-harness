# Submission status

**Community listing: NOT SATISFIED.** The public Competition Mode result and
Linux fixture are complete and the source is released publicly. Maintainer
acceptance of the community entry is pending.

## Community submission

| Requirement | Status and evidence |
|---|---|
| Published Competition Mode scorecard | **SATISFIED**: the [ARC page](https://arcprize.org/scorecards/75d9c8e7-ade9-4a8f-a747-6acbea51bb1b) records 100.00%, 25/25 games, 183/183 levels and 6,732 actions; the original card records Competition Mode. |
| Complete producing system in the package | **SATISFIED**: all 74 evaluated source files, prompt, tools, configuration, locked dependencies, license notices and reproduction entry point are included. |
| Public source availability | **SATISFIED**: complete producing system is published in this repository under Apache-2.0 with third-party notices. |
| Submission metadata | **SATISFIED**: fields, unique method name, benchmark/set and Competition Mode scorecard link are prepared under the official schema. Public URLs are checked again as part of publication. |
| Generality and novel-contribution acceptance | **NOT SATISFIED**: the [method](method.md#contribution-and-generality) and development exposure are disclosed; no maintainer decision exists. |
| Maintainer review and merge | **NOT SATISFIED**: a prepared entry is not an acceptance decision. Upstream checks and maintainer feedback are tracked in the submission PR. |

The [community instructions](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/blob/main/CONTRIBUTING.md)
describe a method review and require public reproducible source. A paper is
optional. Organizer-run protected evaluation is a separate path.

## Release checks

| Check | Status and evidence |
|---|---|
| Reproduction wrapper on Linux | **SATISFIED**: private Kaggle version 1 completed 231 tests and the synthetic fixture in 74.90 seconds, with zero API operations and zero charged/reserved cost. See [receipt](../evidence/linux-fixture.json). |
| Evaluated source identity | **SATISFIED**: all 74 evaluated files and the original source archive retain their recorded hashes. The reproduction wrapper is separately identified. |
| Successful public-run cost reconciliation | **SATISFIED**: USD 415.37; original provider exports and invoices reconciled privately. |
| Rights holder and license | **SATISFIED**: Orca Labs sp. z o.o., Apache-2.0, with separate third-party notices. |
| Packaging metadata consistency | **NOT SATISFIED**: frozen pyproject.toml says 0.3.6+api7; evaluated manifest/run says 0.3.8+api9. This defect is preserved and disclosed to retain evaluated source identity. The documented bootstrap executes the frozen source directly. |

The fixture is a software check, not another public benchmark result. Kaggle
reformatted the notebook JSON and source arrays; saved cell text and normalized
notebook content match the supplied wrapper. Both file hashes are recorded.

## Separate official verification path

**Full official verified submission compliance: NOT SATISFIED.** The following
items remain open for that path; they are not all community-entry prerequisites.

| Remaining requirement | Concrete gap |
|---|---|
| Evaluator setup and provider acceptance | **NOT SATISFIED**: evaluator-owned account access and organizer execution acceptance are missing. |
| Organizer consultation | **NOT SATISFIED**: private draft has not been sent. |
| Actual organizer dataset replacement | **NOT SATISFIED**: only synthetic replacement checks; no agreed live organizer interface. |
| Protected retention and data flow | **NOT SATISFIED**: no agreement for the exact project, model, Responses/compaction/cache features or logging destinations. |
| Complete historical runtime identity | **NOT SATISFIED**: contemporaneous full interpreter, stdlib and installed-file inventory is missing. This is an additional engineering control; source, locked wheel hashes, saved code and pinned container are recorded. |
| Organizer audit, selection and protected score agreement | **NOT SATISFIED**: no organizer audit disposition, selection decision, protected result or agreement. |

The frozen reports describe their historical pre-run state. The later completed
result is recorded in [public-run.json](../evidence/public-run.json). No missing
historical attestation is reconstructed as contemporaneous evidence.
[ARC policy](https://arcprize.org/policy) governs organizer verification.
