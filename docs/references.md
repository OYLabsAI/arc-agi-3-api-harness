# Related work

## 2026 community entries

- [Tycho](https://github.com/NIMI-research/Tycho) and
  [baseline1](https://github.com/astroseger/arc-3-agents-baseline1) describe agents
  that construct executable world models.
- [Retrodict](https://github.com/ryanbbrown/Retrodict) describes testing hypotheses
  against recorded history.
- [NVIDIA DreamTeam](https://github.com/NVIDIA/dream-team) coordinates specialized
  agents around a shared workspace and an executable world model.

OY1 gives the model tools to retrieve observations and check action predictions.
It does not expose a shell or a tool for writing and running a simulator. The
[method](method.md) describes that interface and its limits.

## Benchmark and comparison sources

- [ARC-AGI-3 benchmarking harness](https://github.com/arcprize/arc-agi-3-benchmarking):
  Standard and Provider Adapter implementations.
- [GPT-6 Astra results](https://arcprize.org/results/openai-gpt-6-astra):
  results and replays by reasoning setting and evaluation set.
- [OY1 public replay comparison](token-comparison.md): exact game versions,
  token accounting and the script used to check the published replays.
- [Community submission requirements](https://github.com/arcprize/ARC-AGI-Community-Leaderboard/blob/main/CONTRIBUTING.md).

The other community agents were not run as part of this evaluation. Their
reported scores and costs use different models and configurations.
