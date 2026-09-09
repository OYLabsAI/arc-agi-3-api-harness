# Repository documentation references

Reviewed 2026-09-09 to decide which information reviewers need. No solver code,
prompts, datasets or solutions were copied from these projects.

## 2026 community entries

The [current community page](https://arcprize.org/leaderboard/community) and its
[submission instructions](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/blob/main/CONTRIBUTING.md)
were reviewed on 2026-09-09. Community acceptance is distinct from competition
placement or ARC Prize verification.

| Primary source | Information reviewed | Applied here |
|---|---|---|
| [Tycho](https://github.com/NIMI-research/Tycho) | Architecture, scorecards, configurations, reproduction and credential-free checks | Direct scorecard link, method description and bounded fixture instructions |
| [Retrodict](https://github.com/ryanbbrown/Retrodict) | Run selection, development exposure, replay method, cost basis and trace availability | Explicit live API provenance, all attempts and reconciled cost disclosure |
| [baseline1](https://github.com/astroseger/arc-3-agents-baseline1) | General-agent assumptions and limits of public-set saturation | Shared solver interface, per-game memory boundaries and unseen-game limitations |

These were documentation reviews; the other agents were not executed or audited.
Their models, cost methods and run selection differ. This repository makes no
matched cost-efficiency or superiority claim from the community table.

## Additional documentation examples

| Primary source | Information it exposes | Applied here |
|---|---|---|
| [Official ARC-AGI-3 harness](https://github.com/arcprize/arc-agi-3-benchmarking) | Setup commands, credentials, game/config selection, scorecards, harness distinctions and license | Explicit reproduction steps, provider configuration and scope |
| [ARChitects 2024 solution](https://github.com/da-fr/arc-prize-2024) | Paper, dependencies, model/data access, hardware, module guide, original and updated notebooks, license | Method/module guide, frozen notebook plus review wrapper, dependencies and hardware |
| [ARChitects 2025 report](https://lambdalabsml.github.io/ARC2025_Solution_by_the_ARChitects/) | Approach, unsuccessful experiments, compute budget, results and limitations | Complete attempt history, reconciled cost and remaining requirements |
| [Official Astra result](https://arcprize.org/results/openai-gpt-6-astra) | Model/reasoning variants and per-environment results, separated by harness and benchmark split | Exact model configuration and per-game result table with split clearly labelled |

ARC lists the ARChitects as the [2024 high-score winner](https://arcprize.org/competitions/2024)
and [2025 second-place team](https://arcprize.org/competitions/2025). Those are
earlier ARC benchmarks with different evaluation conditions; these documentation
examples do not establish a comparable score or winner status for this project.
NVARC's official 2025 code link points to a Kaggle notebook; its content was not
available in the web text retrieval, so no content claims are made about it.
