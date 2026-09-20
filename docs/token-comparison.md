# Public replay token comparison

On the same 25 public game versions, the published GPT-6 Astra **high-reasoning**
Provider Adapter replays contain **901,970,049 total tokens**. The completed OY1
run reports **153,058,391**, including compaction: **83.03% fewer total tokens**.
Both completed all **183 levels**. This compares recorded token usage across
published runs; it is not a controlled ablation or a dollar-cost comparison.

| Measure | Provider Adapter public replays | OY1 completed public run |
|---|---:|---:|
| Model / reasoning | GPT-6 Astra / high | GPT-6 Astra / high |
| Matching game versions | 25 | 25 |
| Completed levels | 183 | 183 |
| Total tokens | 901,970,049 | 153,058,391 |

## Sources and calculation

- [ARC Prize GPT-6 Astra results](https://arcprize.org/results/openai-gpt-6-astra):
  the **Public Demo / Provider Adapter / High** replay links, retrieved 20 September 2026.
- [OY1 aggregate](../evidence/public-run.json) and [run accounting](results.md):
  run `20260909T110238Z-ce055081`, with 1,728 decisions and 45 compaction operations.
- [Machine-readable comparison](../evidence/public-token-comparison.json):
  all 25 replay URLs, exact game versions, recording hashes and per-game totals.

The replay audit checked the model and configuration on each public session,
matched every exact game version to OY1's [per-game results](../evidence/per-game-results.json),
and checked each recording's final `WIN` state and completed-level count.
It summed `usage.total_tokens` in the JSON stored in
`data.action_input.reasoning` for every replay row containing usage: **7,078 records**.
No nonempty reasoning record lacked usage.

```text
100 × (1 − 153,058,391 / 901,970,049) = 83.030657…%
```

The Provider Adapter sum contains 901,138,267 input tokens and 831,782 output
tokens. Cached input (447,253,876) is already part of input; reasoning tokens
(772,857) are already part of output. Adding these subsets again would double-count them.

The OY1 total is the published run aggregate; its inclusion of compaction is
reported by the creator and consistent with the documented operation counts.
The original OY1 usage ledger remains private, so this replay audit independently
recomputes the Provider Adapter side and checks OY1 against its public aggregate.
Any Provider Adapter requests absent from the public replay records are outside
this comparison; the replay sum is not a billing reconciliation.

## Reproduce the replay sum

With Python 3.9 or newer, run from the repository root:

```sh
python3 tools/verify_token_comparison.py --cache /tmp/oy1-public-replays
```

This downloads public recordings, checks their recorded SHA-256 hashes and
recalculates the totals. It needs internet access and several hundred MB of
scratch space. It does not run a model or incur inference charges. The cache
contains public replay content, including any model reasoning published there.

## Per-game Provider Adapter totals

| Exact game version and replay | Total tokens | Completed levels |
|---|---:|---:|
| [`ar25-0c556536`](https://arcprize.org/replay/1550f0c9-c286-4e15-84f9-178c5c9f97ff) | 32,278,517 | 8 |
| [`bp35-0a0ad940`](https://arcprize.org/replay/fbab92cd-0b28-4d8d-88f6-83a54b7aacfb) | 73,649,373 | 9 |
| [`cd82-fb555c5d`](https://arcprize.org/replay/fdc50b7b-de6f-4838-9e05-10ee63bf9725) | 9,401,378 | 6 |
| [`cn04-2fe56bfb`](https://arcprize.org/replay/561e2291-8cb7-45e1-ab12-97989ca03b0a) | 26,461,276 | 6 |
| [`dc22-fdcac232`](https://arcprize.org/replay/b436a14c-e9c5-43f3-b41d-721ccf59519a) | 54,489,282 | 6 |
| [`ft09-0d8bbf25`](https://arcprize.org/replay/2c5fd75d-92c9-4f37-80d9-bc6004885c9a) | 9,262,783 | 6 |
| [`g50t-5849a774`](https://arcprize.org/replay/9ab081d6-34d8-4769-bdce-968b829f1091) | 48,113,067 | 7 |
| [`ka59-38d34dbb`](https://arcprize.org/replay/a6e15bfa-590a-4053-b5dc-b11e7b8b1cb4) | 38,809,422 | 7 |
| [`lf52-271a04aa`](https://arcprize.org/replay/e1ef8feb-5393-4a69-9780-b6f7ef48ba93) | 102,442,124 | 10 |
| [`lp85-305b61c3`](https://arcprize.org/replay/a478cd77-33fa-4289-a05b-7391809359a8) | 11,462,982 | 8 |
| [`ls20-9607627b`](https://arcprize.org/replay/27b4461a-7bdb-45f6-9bb0-f1487d6ce662) | 54,710,027 | 7 |
| [`m0r0-492f87ba`](https://arcprize.org/replay/50d61a09-c2b8-4354-9312-de22c65eb9b7) | 28,394,350 | 6 |
| [`r11l-495a7899`](https://arcprize.org/replay/a204250e-2b46-4474-bcc3-ff13c220d271) | 9,090,904 | 6 |
| [`re86-8af5384d`](https://arcprize.org/replay/d846db33-73ea-4066-b3be-0befc6c2dbc5) | 73,810,786 | 8 |
| [`s5i5-18d95033`](https://arcprize.org/replay/0945e840-474f-4f1f-9e47-bbcf7aa05639) | 30,975,584 | 8 |
| [`sb26-7fbdac44`](https://arcprize.org/replay/95542d79-8533-445b-91b0-68adfa026db8) | 13,367,550 | 8 |
| [`sc25-635fd71a`](https://arcprize.org/replay/6eaaa941-433c-41a3-b69a-a70be93c6a08) | 16,294,807 | 6 |
| [`sk48-d8078629`](https://arcprize.org/replay/5bcc0575-b75b-41eb-8361-909e886fb5b9) | 57,278,630 | 8 |
| [`sp80-589a99af`](https://arcprize.org/replay/f37ae900-fd49-4d08-aee4-ca124ca44392) | 15,859,456 | 6 |
| [`su15-1944f8ab`](https://arcprize.org/replay/bffe1ccd-c92c-44ee-abe3-d13d4185d862) | 15,951,927 | 9 |
| [`tn36-ef4dde99`](https://arcprize.org/replay/8d408961-f16e-419c-ad6b-12e0e697f2ca) | 36,515,788 | 7 |
| [`tr87-cd924810`](https://arcprize.org/replay/a1e55710-322c-46ce-8969-02d8063168d7) | 16,259,207 | 6 |
| [`tu93-0768757b`](https://arcprize.org/replay/2ae60daf-4f2e-48bc-830a-e3e37e15b881) | 35,217,252 | 9 |
| [`vc33-5430563c`](https://arcprize.org/replay/ec8082e6-fafd-4598-92f5-aa12ee7ecf09) | 18,165,257 | 7 |
| [`wa30-ee6fef47`](https://arcprize.org/replay/6f55299f-71ce-4d33-97a6-7043e44bce70) | 73,708,320 | 9 |

## Interpretation

This is evidence of lower recorded token usage for the completed OY1 run on
this public selection. It does not identify which harness component accounts
for the difference. The public games were used during OY1 development; no
unseen-game result is established here. The same model name and reasoning
setting do not control prompts, context management, sampling, run dates or
other harness settings. Completion of all levels also does not imply identical
action-efficiency scores.

Token reduction is not a dollar-cost reduction: cached input, uncached input
and output have different prices. This comparison does not use the semi-private
$18,817 figure or NVIDIA DreamTeam's separate $18,000 result. A matched evaluation
and component ablations are described in the [evaluation plan](evaluation-plan.md).
