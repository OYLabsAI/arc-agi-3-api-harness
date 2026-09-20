# Level action comparison

OY1 used **6,732 environment actions** across the 183 public levels, compared
with **7,085** in the published OpenAI Provider Adapter run: **4.98% fewer overall**.
Both used GPT-6 Astra at high reasoning and completed all 25 games.
OY1 used fewer actions on 59 levels, the same number on 81, and more on 43.

The README highlights the **four largest percentage reductions**, ranked below.
Ties are ordered by actions saved, then game ID and level. These selected levels
show where the action advantage was largest. Token usage is a separate measure;
see the [token comparison](token-comparison.md).

Counts include every action between the start of a level and its completion,
including retries and the completion transition. The initial game reset is
excluded. Neither run contains a later full game reset. Negative reductions
mean OY1 used more actions. Playback timing does not measure inference speed.

Source: [ARC Prize's GPT-6 Astra results](https://arcprize.org/results/openai-gpt-6-astra)
and the [OY1 scorecard](https://arcprize.org/scorecards/75d9c8e7-ade9-4a8f-a747-6acbea51bb1b).
Both runs cover the same exact game versions; the public games were used during
OY1 development. This compares published runs, not a controlled ablation.

| Game version | Level | OY1 actions | Provider Adapter actions | Reduction | Replays |
|---|---:|---:|---:|---:|---|
| tn36-ef4dde99 | 6 | 32 | 214 | 85.05% | [OY1](https://arcprize.org/replay/22761359-7720-4a5c-acab-4432719a35c5) · [Provider Adapter](https://arcprize.org/replay/8d408961-f16e-419c-ad6b-12e0e697f2ca) |
| lf52-271a04aa | 10 | 50 | 110 | 54.55% | [OY1](https://arcprize.org/replay/79127723-14e2-4d3d-a60c-9a45e99e6575) · [Provider Adapter](https://arcprize.org/replay/e1ef8feb-5393-4a69-9780-b6f7ef48ba93) |
| ls20-9607627b | 2 | 45 | 99 | 54.55% | [OY1](https://arcprize.org/replay/0a9dfe50-1421-45c9-8041-773c58b6b85b) · [Provider Adapter](https://arcprize.org/replay/27b4461a-7bdb-45f6-9bb0-f1487d6ce662) |
| ls20-9607627b | 5 | 48 | 98 | 51.02% | [OY1](https://arcprize.org/replay/0a9dfe50-1421-45c9-8041-773c58b6b85b) · [Provider Adapter](https://arcprize.org/replay/27b4461a-7bdb-45f6-9bb0-f1487d6ce662) |
| tr87-cd924810 | 5 | 14 | 25 | 44.00% | [OY1](https://arcprize.org/replay/34c9120b-2214-46e2-96e3-45e78d759390) · [Provider Adapter](https://arcprize.org/replay/a1e55710-322c-46ce-8969-02d8063168d7) |
| tu93-0768757b | 9 | 29 | 51 | 43.14% | [OY1](https://arcprize.org/replay/3893f733-e1bd-4827-93b6-6ff8e64171ee) · [Provider Adapter](https://arcprize.org/replay/2ae60daf-4f2e-48bc-830a-e3e37e15b881) |
| bp35-0a0ad940 | 8 | 42 | 71 | 40.85% | [OY1](https://arcprize.org/replay/bcd43d66-ac98-43c2-8221-f6e872c7d1c2) · [Provider Adapter](https://arcprize.org/replay/fbab92cd-0b28-4d8d-88f6-83a54b7aacfb) |
| sp80-589a99af | 6 | 36 | 57 | 36.84% | [OY1](https://arcprize.org/replay/28db70d6-cd9c-446e-bf30-9a829c12e5ba) · [Provider Adapter](https://arcprize.org/replay/f37ae900-fd49-4d08-aee4-ca124ca44392) |
| su15-1944f8ab | 6 | 9 | 14 | 35.71% | [OY1](https://arcprize.org/replay/f6101e88-def8-4e76-a78a-9427745a2385) · [Provider Adapter](https://arcprize.org/replay/bffe1ccd-c92c-44ee-abe3-d13d4185d862) |
| ka59-38d34dbb | 6 | 47 | 70 | 32.86% | [OY1](https://arcprize.org/replay/9c9af5ce-b61a-4b87-ace9-8650e84907d6) · [Provider Adapter](https://arcprize.org/replay/a6e15bfa-590a-4053-b5dc-b11e7b8b1cb4) |
| sk48-d8078629 | 8 | 47 | 69 | 31.88% | [OY1](https://arcprize.org/replay/45d858f8-5c84-4994-87dc-f4a88502bdf8) · [Provider Adapter](https://arcprize.org/replay/5bcc0575-b75b-41eb-8361-909e886fb5b9) |
| sk48-d8078629 | 7 | 53 | 77 | 31.17% | [OY1](https://arcprize.org/replay/45d858f8-5c84-4994-87dc-f4a88502bdf8) · [Provider Adapter](https://arcprize.org/replay/5bcc0575-b75b-41eb-8361-909e886fb5b9) |
| bp35-0a0ad940 | 9 | 80 | 114 | 29.82% | [OY1](https://arcprize.org/replay/bcd43d66-ac98-43c2-8221-f6e872c7d1c2) · [Provider Adapter](https://arcprize.org/replay/fbab92cd-0b28-4d8d-88f6-83a54b7aacfb) |
| cn04-2fe56bfb | 5 | 48 | 68 | 29.41% | [OY1](https://arcprize.org/replay/cd3a47ef-0a45-46a0-aae0-9f9f7b4ff8e7) · [Provider Adapter](https://arcprize.org/replay/561e2291-8cb7-45e1-ab12-97989ca03b0a) |
| sc25-635fd71a | 2 | 5 | 7 | 28.57% | [OY1](https://arcprize.org/replay/e495099e-151b-41ec-b146-c1be2f71a589) · [Provider Adapter](https://arcprize.org/replay/6eaaa941-433c-41a3-b69a-a70be93c6a08) |
| ls20-9607627b | 1 | 15 | 20 | 25.00% | [OY1](https://arcprize.org/replay/0a9dfe50-1421-45c9-8041-773c58b6b85b) · [Provider Adapter](https://arcprize.org/replay/27b4461a-7bdb-45f6-9bb0-f1487d6ce662) |
| cd82-fb555c5d | 1 | 13 | 17 | 23.53% | [OY1](https://arcprize.org/replay/20fcc634-9e4e-4c3d-a638-b577b0301cd1) · [Provider Adapter](https://arcprize.org/replay/fdc50b7b-de6f-4838-9e05-10ee63bf9725) |
| lp85-305b61c3 | 1 | 7 | 9 | 22.22% | [OY1](https://arcprize.org/replay/320e870c-f647-4afb-8ba6-70cd496b540c) · [Provider Adapter](https://arcprize.org/replay/a478cd77-33fa-4289-a05b-7391809359a8) |
| m0r0-492f87ba | 3 | 65 | 82 | 20.73% | [OY1](https://arcprize.org/replay/b3c4fd9b-d852-422c-9fe0-35271646bd6d) · [Provider Adapter](https://arcprize.org/replay/50d61a09-c2b8-4354-9312-de22c65eb9b7) |
| su15-1944f8ab | 9 | 12 | 15 | 20.00% | [OY1](https://arcprize.org/replay/f6101e88-def8-4e76-a78a-9427745a2385) · [Provider Adapter](https://arcprize.org/replay/bffe1ccd-c92c-44ee-abe3-d13d4185d862) |
| tr87-cd924810 | 2 | 26 | 32 | 18.75% | [OY1](https://arcprize.org/replay/34c9120b-2214-46e2-96e3-45e78d759390) · [Provider Adapter](https://arcprize.org/replay/a1e55710-322c-46ce-8969-02d8063168d7) |
| r11l-495a7899 | 2 | 9 | 11 | 18.18% | [OY1](https://arcprize.org/replay/fcf46cc2-5c17-4726-9d64-85e56a0039f2) · [Provider Adapter](https://arcprize.org/replay/a204250e-2b46-4474-bcc3-ff13c220d271) |
| lp85-305b61c3 | 4 | 14 | 17 | 17.65% | [OY1](https://arcprize.org/replay/320e870c-f647-4afb-8ba6-70cd496b540c) · [Provider Adapter](https://arcprize.org/replay/a478cd77-33fa-4289-a05b-7391809359a8) |
| tu93-0768757b | 6 | 30 | 36 | 16.67% | [OY1](https://arcprize.org/replay/3893f733-e1bd-4827-93b6-6ff8e64171ee) · [Provider Adapter](https://arcprize.org/replay/2ae60daf-4f2e-48bc-830a-e3e37e15b881) |
| r11l-495a7899 | 6 | 16 | 19 | 15.79% | [OY1](https://arcprize.org/replay/fcf46cc2-5c17-4726-9d64-85e56a0039f2) · [Provider Adapter](https://arcprize.org/replay/a204250e-2b46-4474-bcc3-ff13c220d271) |
| sp80-589a99af | 3 | 11 | 13 | 15.38% | [OY1](https://arcprize.org/replay/28db70d6-cd9c-446e-bf30-9a829c12e5ba) · [Provider Adapter](https://arcprize.org/replay/f37ae900-fd49-4d08-aee4-ca124ca44392) |
| su15-1944f8ab | 8 | 11 | 13 | 15.38% | [OY1](https://arcprize.org/replay/f6101e88-def8-4e76-a78a-9427745a2385) · [Provider Adapter](https://arcprize.org/replay/bffe1ccd-c92c-44ee-abe3-d13d4185d862) |
| tr87-cd924810 | 1 | 17 | 20 | 15.00% | [OY1](https://arcprize.org/replay/34c9120b-2214-46e2-96e3-45e78d759390) · [Provider Adapter](https://arcprize.org/replay/a1e55710-322c-46ce-8969-02d8063168d7) |
| cn04-2fe56bfb | 4 | 33 | 38 | 13.16% | [OY1](https://arcprize.org/replay/cd3a47ef-0a45-46a0-aae0-9f9f7b4ff8e7) · [Provider Adapter](https://arcprize.org/replay/561e2291-8cb7-45e1-ab12-97989ca03b0a) |
| wa30-ee6fef47 | 1 | 27 | 31 | 12.90% | [OY1](https://arcprize.org/replay/6503caa5-73c0-4b5e-9fdf-9d5d8e6eb176) · [Provider Adapter](https://arcprize.org/replay/6f55299f-71ce-4d33-97a6-7043e44bce70) |
| re86-8af5384d | 8 | 183 | 209 | 12.44% | [OY1](https://arcprize.org/replay/e77ef5ea-f632-4b56-abdd-5d857634c408) · [Provider Adapter](https://arcprize.org/replay/d846db33-73ea-4066-b3be-0befc6c2dbc5) |
| lf52-271a04aa | 4 | 50 | 56 | 10.71% | [OY1](https://arcprize.org/replay/79127723-14e2-4d3d-a60c-9a45e99e6575) · [Provider Adapter](https://arcprize.org/replay/e1ef8feb-5393-4a69-9780-b6f7ef48ba93) |
| r11l-495a7899 | 5 | 17 | 19 | 10.53% | [OY1](https://arcprize.org/replay/fcf46cc2-5c17-4726-9d64-85e56a0039f2) · [Provider Adapter](https://arcprize.org/replay/a204250e-2b46-4474-bcc3-ff13c220d271) |
| lp85-305b61c3 | 6 | 19 | 21 | 9.52% | [OY1](https://arcprize.org/replay/320e870c-f647-4afb-8ba6-70cd496b540c) · [Provider Adapter](https://arcprize.org/replay/a478cd77-33fa-4289-a05b-7391809359a8) |
| dc22-fdcac232 | 1 | 22 | 24 | 8.33% | [OY1](https://arcprize.org/replay/20d26669-51a5-4d89-9e35-9fc329abc363) · [Provider Adapter](https://arcprize.org/replay/b436a14c-e9c5-43f3-b41d-721ccf59519a) |
| ka59-38d34dbb | 2 | 48 | 52 | 7.69% | [OY1](https://arcprize.org/replay/9c9af5ce-b61a-4b87-ace9-8650e84907d6) · [Provider Adapter](https://arcprize.org/replay/a6e15bfa-590a-4053-b5dc-b11e7b8b1cb4) |
| wa30-ee6fef47 | 2 | 48 | 52 | 7.69% | [OY1](https://arcprize.org/replay/6503caa5-73c0-4b5e-9fdf-9d5d8e6eb176) · [Provider Adapter](https://arcprize.org/replay/6f55299f-71ce-4d33-97a6-7043e44bce70) |
| wa30-ee6fef47 | 5 | 103 | 111 | 7.21% | [OY1](https://arcprize.org/replay/6503caa5-73c0-4b5e-9fdf-9d5d8e6eb176) · [Provider Adapter](https://arcprize.org/replay/6f55299f-71ce-4d33-97a6-7043e44bce70) |
| r11l-495a7899 | 4 | 13 | 14 | 7.14% | [OY1](https://arcprize.org/replay/fcf46cc2-5c17-4726-9d64-85e56a0039f2) · [Provider Adapter](https://arcprize.org/replay/a204250e-2b46-4474-bcc3-ff13c220d271) |
| cn04-2fe56bfb | 1 | 14 | 15 | 6.67% | [OY1](https://arcprize.org/replay/cd3a47ef-0a45-46a0-aae0-9f9f7b4ff8e7) · [Provider Adapter](https://arcprize.org/replay/561e2291-8cb7-45e1-ab12-97989ca03b0a) |
| tn36-ef4dde99 | 4 | 14 | 15 | 6.67% | [OY1](https://arcprize.org/replay/22761359-7720-4a5c-acab-4432719a35c5) · [Provider Adapter](https://arcprize.org/replay/8d408961-f16e-419c-ad6b-12e0e697f2ca) |
| g50t-5849a774 | 7 | 43 | 46 | 6.52% | [OY1](https://arcprize.org/replay/4dbaf973-d3af-4aac-a325-0f0f8a4041e6) · [Provider Adapter](https://arcprize.org/replay/9ab081d6-34d8-4769-bdce-968b829f1091) |
| sc25-635fd71a | 6 | 35 | 37 | 5.41% | [OY1](https://arcprize.org/replay/e495099e-151b-41ec-b146-c1be2f71a589) · [Provider Adapter](https://arcprize.org/replay/6eaaa941-433c-41a3-b69a-a70be93c6a08) |
| ar25-0c556536 | 7 | 37 | 39 | 5.13% | [OY1](https://arcprize.org/replay/74077944-f734-4895-adce-ae20e4d916fc) · [Provider Adapter](https://arcprize.org/replay/1550f0c9-c286-4e15-84f9-178c5c9f97ff) |
| s5i5-18d95033 | 3 | 37 | 39 | 5.13% | [OY1](https://arcprize.org/replay/345b0563-a565-432f-90c5-084882e935ff) · [Provider Adapter](https://arcprize.org/replay/0945e840-474f-4f1f-9e47-bbcf7aa05639) |
| cn04-2fe56bfb | 6 | 39 | 41 | 4.88% | [OY1](https://arcprize.org/replay/cd3a47ef-0a45-46a0-aae0-9f9f7b4ff8e7) · [Provider Adapter](https://arcprize.org/replay/561e2291-8cb7-45e1-ab12-97989ca03b0a) |
| s5i5-18d95033 | 7 | 46 | 48 | 4.17% | [OY1](https://arcprize.org/replay/345b0563-a565-432f-90c5-084882e935ff) · [Provider Adapter](https://arcprize.org/replay/0945e840-474f-4f1f-9e47-bbcf7aa05639) |
| vc33-5430563c | 7 | 49 | 51 | 3.92% | [OY1](https://arcprize.org/replay/c8995261-2fa7-48b4-9fc6-e1624a20697f) · [Provider Adapter](https://arcprize.org/replay/ec8082e6-fafd-4598-92f5-aa12ee7ecf09) |
| bp35-0a0ad940 | 7 | 55 | 57 | 3.51% | [OY1](https://arcprize.org/replay/bcd43d66-ac98-43c2-8221-f6e872c7d1c2) · [Provider Adapter](https://arcprize.org/replay/fbab92cd-0b28-4d8d-88f6-83a54b7aacfb) |
| re86-8af5384d | 7 | 125 | 129 | 3.10% | [OY1](https://arcprize.org/replay/e77ef5ea-f632-4b56-abdd-5d857634c408) · [Provider Adapter](https://arcprize.org/replay/d846db33-73ea-4066-b3be-0befc6c2dbc5) |
| bp35-0a0ad940 | 6 | 100 | 103 | 2.91% | [OY1](https://arcprize.org/replay/bcd43d66-ac98-43c2-8221-f6e872c7d1c2) · [Provider Adapter](https://arcprize.org/replay/fbab92cd-0b28-4d8d-88f6-83a54b7aacfb) |
| wa30-ee6fef47 | 3 | 74 | 76 | 2.63% | [OY1](https://arcprize.org/replay/6503caa5-73c0-4b5e-9fdf-9d5d8e6eb176) · [Provider Adapter](https://arcprize.org/replay/6f55299f-71ce-4d33-97a6-7043e44bce70) |
| ls20-9607627b | 6 | 82 | 84 | 2.38% | [OY1](https://arcprize.org/replay/0a9dfe50-1421-45c9-8041-773c58b6b85b) · [Provider Adapter](https://arcprize.org/replay/27b4461a-7bdb-45f6-9bb0-f1487d6ce662) |
| wa30-ee6fef47 | 7 | 44 | 45 | 2.22% | [OY1](https://arcprize.org/replay/6503caa5-73c0-4b5e-9fdf-9d5d8e6eb176) · [Provider Adapter](https://arcprize.org/replay/6f55299f-71ce-4d33-97a6-7043e44bce70) |
| lf52-271a04aa | 5 | 90 | 92 | 2.17% | [OY1](https://arcprize.org/replay/79127723-14e2-4d3d-a60c-9a45e99e6575) · [Provider Adapter](https://arcprize.org/replay/e1ef8feb-5393-4a69-9780-b6f7ef48ba93) |
| wa30-ee6fef47 | 9 | 62 | 63 | 1.59% | [OY1](https://arcprize.org/replay/6503caa5-73c0-4b5e-9fdf-9d5d8e6eb176) · [Provider Adapter](https://arcprize.org/replay/6f55299f-71ce-4d33-97a6-7043e44bce70) |
| lf52-271a04aa | 9 | 116 | 117 | 0.85% | [OY1](https://arcprize.org/replay/79127723-14e2-4d3d-a60c-9a45e99e6575) · [Provider Adapter](https://arcprize.org/replay/e1ef8feb-5393-4a69-9780-b6f7ef48ba93) |
| dc22-fdcac232 | 5 | 118 | 119 | 0.84% | [OY1](https://arcprize.org/replay/20d26669-51a5-4d89-9e35-9fc329abc363) · [Provider Adapter](https://arcprize.org/replay/b436a14c-e9c5-43f3-b41d-721ccf59519a) |
| lf52-271a04aa | 7 | 144 | 145 | 0.69% | [OY1](https://arcprize.org/replay/79127723-14e2-4d3d-a60c-9a45e99e6575) · [Provider Adapter](https://arcprize.org/replay/e1ef8feb-5393-4a69-9780-b6f7ef48ba93) |
| ar25-0c556536 | 2 | 11 | 11 | 0.00% | [OY1](https://arcprize.org/replay/74077944-f734-4895-adce-ae20e4d916fc) · [Provider Adapter](https://arcprize.org/replay/1550f0c9-c286-4e15-84f9-178c5c9f97ff) |
| ar25-0c556536 | 3 | 40 | 40 | 0.00% | [OY1](https://arcprize.org/replay/74077944-f734-4895-adce-ae20e4d916fc) · [Provider Adapter](https://arcprize.org/replay/1550f0c9-c286-4e15-84f9-178c5c9f97ff) |
| ar25-0c556536 | 4 | 22 | 22 | 0.00% | [OY1](https://arcprize.org/replay/74077944-f734-4895-adce-ae20e4d916fc) · [Provider Adapter](https://arcprize.org/replay/1550f0c9-c286-4e15-84f9-178c5c9f97ff) |
| ar25-0c556536 | 6 | 53 | 53 | 0.00% | [OY1](https://arcprize.org/replay/74077944-f734-4895-adce-ae20e4d916fc) · [Provider Adapter](https://arcprize.org/replay/1550f0c9-c286-4e15-84f9-178c5c9f97ff) |
| ar25-0c556536 | 8 | 47 | 47 | 0.00% | [OY1](https://arcprize.org/replay/74077944-f734-4895-adce-ae20e4d916fc) · [Provider Adapter](https://arcprize.org/replay/1550f0c9-c286-4e15-84f9-178c5c9f97ff) |
| bp35-0a0ad940 | 1 | 15 | 15 | 0.00% | [OY1](https://arcprize.org/replay/bcd43d66-ac98-43c2-8221-f6e872c7d1c2) · [Provider Adapter](https://arcprize.org/replay/fbab92cd-0b28-4d8d-88f6-83a54b7aacfb) |
| bp35-0a0ad940 | 3 | 34 | 34 | 0.00% | [OY1](https://arcprize.org/replay/bcd43d66-ac98-43c2-8221-f6e872c7d1c2) · [Provider Adapter](https://arcprize.org/replay/fbab92cd-0b28-4d8d-88f6-83a54b7aacfb) |
| bp35-0a0ad940 | 4 | 23 | 23 | 0.00% | [OY1](https://arcprize.org/replay/bcd43d66-ac98-43c2-8221-f6e872c7d1c2) · [Provider Adapter](https://arcprize.org/replay/fbab92cd-0b28-4d8d-88f6-83a54b7aacfb) |
| bp35-0a0ad940 | 5 | 31 | 31 | 0.00% | [OY1](https://arcprize.org/replay/bcd43d66-ac98-43c2-8221-f6e872c7d1c2) · [Provider Adapter](https://arcprize.org/replay/fbab92cd-0b28-4d8d-88f6-83a54b7aacfb) |
| cd82-fb555c5d | 2 | 6 | 6 | 0.00% | [OY1](https://arcprize.org/replay/20fcc634-9e4e-4c3d-a638-b577b0301cd1) · [Provider Adapter](https://arcprize.org/replay/fdc50b7b-de6f-4838-9e05-10ee63bf9725) |
| cd82-fb555c5d | 4 | 14 | 14 | 0.00% | [OY1](https://arcprize.org/replay/20fcc634-9e4e-4c3d-a638-b577b0301cd1) · [Provider Adapter](https://arcprize.org/replay/fdc50b7b-de6f-4838-9e05-10ee63bf9725) |
| cd82-fb555c5d | 5 | 13 | 13 | 0.00% | [OY1](https://arcprize.org/replay/20fcc634-9e4e-4c3d-a638-b577b0301cd1) · [Provider Adapter](https://arcprize.org/replay/fdc50b7b-de6f-4838-9e05-10ee63bf9725) |
| cd82-fb555c5d | 6 | 16 | 16 | 0.00% | [OY1](https://arcprize.org/replay/20fcc634-9e4e-4c3d-a638-b577b0301cd1) · [Provider Adapter](https://arcprize.org/replay/fdc50b7b-de6f-4838-9e05-10ee63bf9725) |
| cn04-2fe56bfb | 2 | 29 | 29 | 0.00% | [OY1](https://arcprize.org/replay/cd3a47ef-0a45-46a0-aae0-9f9f7b4ff8e7) · [Provider Adapter](https://arcprize.org/replay/561e2291-8cb7-45e1-ab12-97989ca03b0a) |
| cn04-2fe56bfb | 3 | 24 | 24 | 0.00% | [OY1](https://arcprize.org/replay/cd3a47ef-0a45-46a0-aae0-9f9f7b4ff8e7) · [Provider Adapter](https://arcprize.org/replay/561e2291-8cb7-45e1-ab12-97989ca03b0a) |
| dc22-fdcac232 | 3 | 45 | 45 | 0.00% | [OY1](https://arcprize.org/replay/20d26669-51a5-4d89-9e35-9fc329abc363) · [Provider Adapter](https://arcprize.org/replay/b436a14c-e9c5-43f3-b41d-721ccf59519a) |
| ft09-0d8bbf25 | 1 | 4 | 4 | 0.00% | [OY1](https://arcprize.org/replay/2ad74623-b639-46bc-b86a-81d14c4b5cab) · [Provider Adapter](https://arcprize.org/replay/2c5fd75d-92c9-4f37-80d9-bc6004885c9a) |
| ft09-0d8bbf25 | 2 | 7 | 7 | 0.00% | [OY1](https://arcprize.org/replay/2ad74623-b639-46bc-b86a-81d14c4b5cab) · [Provider Adapter](https://arcprize.org/replay/2c5fd75d-92c9-4f37-80d9-bc6004885c9a) |
| ft09-0d8bbf25 | 3 | 14 | 14 | 0.00% | [OY1](https://arcprize.org/replay/2ad74623-b639-46bc-b86a-81d14c4b5cab) · [Provider Adapter](https://arcprize.org/replay/2c5fd75d-92c9-4f37-80d9-bc6004885c9a) |
| ft09-0d8bbf25 | 4 | 16 | 16 | 0.00% | [OY1](https://arcprize.org/replay/2ad74623-b639-46bc-b86a-81d14c4b5cab) · [Provider Adapter](https://arcprize.org/replay/2c5fd75d-92c9-4f37-80d9-bc6004885c9a) |
| ft09-0d8bbf25 | 5 | 21 | 21 | 0.00% | [OY1](https://arcprize.org/replay/2ad74623-b639-46bc-b86a-81d14c4b5cab) · [Provider Adapter](https://arcprize.org/replay/2c5fd75d-92c9-4f37-80d9-bc6004885c9a) |
| ft09-0d8bbf25 | 6 | 13 | 13 | 0.00% | [OY1](https://arcprize.org/replay/2ad74623-b639-46bc-b86a-81d14c4b5cab) · [Provider Adapter](https://arcprize.org/replay/2c5fd75d-92c9-4f37-80d9-bc6004885c9a) |
| g50t-5849a774 | 2 | 31 | 31 | 0.00% | [OY1](https://arcprize.org/replay/4dbaf973-d3af-4aac-a325-0f0f8a4041e6) · [Provider Adapter](https://arcprize.org/replay/9ab081d6-34d8-4769-bdce-968b829f1091) |
| g50t-5849a774 | 3 | 64 | 64 | 0.00% | [OY1](https://arcprize.org/replay/4dbaf973-d3af-4aac-a325-0f0f8a4041e6) · [Provider Adapter](https://arcprize.org/replay/9ab081d6-34d8-4769-bdce-968b829f1091) |
| g50t-5849a774 | 4 | 31 | 31 | 0.00% | [OY1](https://arcprize.org/replay/4dbaf973-d3af-4aac-a325-0f0f8a4041e6) · [Provider Adapter](https://arcprize.org/replay/9ab081d6-34d8-4769-bdce-968b829f1091) |
| g50t-5849a774 | 5 | 50 | 50 | 0.00% | [OY1](https://arcprize.org/replay/4dbaf973-d3af-4aac-a325-0f0f8a4041e6) · [Provider Adapter](https://arcprize.org/replay/9ab081d6-34d8-4769-bdce-968b829f1091) |
| g50t-5849a774 | 6 | 50 | 50 | 0.00% | [OY1](https://arcprize.org/replay/4dbaf973-d3af-4aac-a325-0f0f8a4041e6) · [Provider Adapter](https://arcprize.org/replay/9ab081d6-34d8-4769-bdce-968b829f1091) |
| ka59-38d34dbb | 5 | 20 | 20 | 0.00% | [OY1](https://arcprize.org/replay/9c9af5ce-b61a-4b87-ace9-8650e84907d6) · [Provider Adapter](https://arcprize.org/replay/a6e15bfa-590a-4053-b5dc-b11e7b8b1cb4) |
| lf52-271a04aa | 3 | 46 | 46 | 0.00% | [OY1](https://arcprize.org/replay/79127723-14e2-4d3d-a60c-9a45e99e6575) · [Provider Adapter](https://arcprize.org/replay/e1ef8feb-5393-4a69-9780-b6f7ef48ba93) |
| lf52-271a04aa | 6 | 91 | 91 | 0.00% | [OY1](https://arcprize.org/replay/79127723-14e2-4d3d-a60c-9a45e99e6575) · [Provider Adapter](https://arcprize.org/replay/e1ef8feb-5393-4a69-9780-b6f7ef48ba93) |
| lp85-305b61c3 | 2 | 8 | 8 | 0.00% | [OY1](https://arcprize.org/replay/320e870c-f647-4afb-8ba6-70cd496b540c) · [Provider Adapter](https://arcprize.org/replay/a478cd77-33fa-4289-a05b-7391809359a8) |
| lp85-305b61c3 | 3 | 16 | 16 | 0.00% | [OY1](https://arcprize.org/replay/320e870c-f647-4afb-8ba6-70cd496b540c) · [Provider Adapter](https://arcprize.org/replay/a478cd77-33fa-4289-a05b-7391809359a8) |
| lp85-305b61c3 | 5 | 11 | 11 | 0.00% | [OY1](https://arcprize.org/replay/320e870c-f647-4afb-8ba6-70cd496b540c) · [Provider Adapter](https://arcprize.org/replay/a478cd77-33fa-4289-a05b-7391809359a8) |
| m0r0-492f87ba | 1 | 15 | 15 | 0.00% | [OY1](https://arcprize.org/replay/b3c4fd9b-d852-422c-9fe0-35271646bd6d) · [Provider Adapter](https://arcprize.org/replay/50d61a09-c2b8-4354-9312-de22c65eb9b7) |
| m0r0-492f87ba | 2 | 23 | 23 | 0.00% | [OY1](https://arcprize.org/replay/b3c4fd9b-d852-422c-9fe0-35271646bd6d) · [Provider Adapter](https://arcprize.org/replay/50d61a09-c2b8-4354-9312-de22c65eb9b7) |
| m0r0-492f87ba | 4 | 13 | 13 | 0.00% | [OY1](https://arcprize.org/replay/b3c4fd9b-d852-422c-9fe0-35271646bd6d) · [Provider Adapter](https://arcprize.org/replay/50d61a09-c2b8-4354-9312-de22c65eb9b7) |
| m0r0-492f87ba | 6 | 51 | 51 | 0.00% | [OY1](https://arcprize.org/replay/b3c4fd9b-d852-422c-9fe0-35271646bd6d) · [Provider Adapter](https://arcprize.org/replay/50d61a09-c2b8-4354-9312-de22c65eb9b7) |
| r11l-495a7899 | 1 | 4 | 4 | 0.00% | [OY1](https://arcprize.org/replay/fcf46cc2-5c17-4726-9d64-85e56a0039f2) · [Provider Adapter](https://arcprize.org/replay/a204250e-2b46-4474-bcc3-ff13c220d271) |
| r11l-495a7899 | 3 | 12 | 12 | 0.00% | [OY1](https://arcprize.org/replay/fcf46cc2-5c17-4726-9d64-85e56a0039f2) · [Provider Adapter](https://arcprize.org/replay/a204250e-2b46-4474-bcc3-ff13c220d271) |
| re86-8af5384d | 1 | 20 | 20 | 0.00% | [OY1](https://arcprize.org/replay/e77ef5ea-f632-4b56-abdd-5d857634c408) · [Provider Adapter](https://arcprize.org/replay/d846db33-73ea-4066-b3be-0befc6c2dbc5) |
| re86-8af5384d | 2 | 36 | 36 | 0.00% | [OY1](https://arcprize.org/replay/e77ef5ea-f632-4b56-abdd-5d857634c408) · [Provider Adapter](https://arcprize.org/replay/d846db33-73ea-4066-b3be-0befc6c2dbc5) |
| re86-8af5384d | 4 | 44 | 44 | 0.00% | [OY1](https://arcprize.org/replay/e77ef5ea-f632-4b56-abdd-5d857634c408) · [Provider Adapter](https://arcprize.org/replay/d846db33-73ea-4066-b3be-0befc6c2dbc5) |
| re86-8af5384d | 5 | 63 | 63 | 0.00% | [OY1](https://arcprize.org/replay/e77ef5ea-f632-4b56-abdd-5d857634c408) · [Provider Adapter](https://arcprize.org/replay/d846db33-73ea-4066-b3be-0befc6c2dbc5) |
| re86-8af5384d | 6 | 68 | 68 | 0.00% | [OY1](https://arcprize.org/replay/e77ef5ea-f632-4b56-abdd-5d857634c408) · [Provider Adapter](https://arcprize.org/replay/d846db33-73ea-4066-b3be-0befc6c2dbc5) |
| s5i5-18d95033 | 1 | 13 | 13 | 0.00% | [OY1](https://arcprize.org/replay/345b0563-a565-432f-90c5-084882e935ff) · [Provider Adapter](https://arcprize.org/replay/0945e840-474f-4f1f-9e47-bbcf7aa05639) |
| s5i5-18d95033 | 2 | 26 | 26 | 0.00% | [OY1](https://arcprize.org/replay/345b0563-a565-432f-90c5-084882e935ff) · [Provider Adapter](https://arcprize.org/replay/0945e840-474f-4f1f-9e47-bbcf7aa05639) |
| s5i5-18d95033 | 4 | 30 | 30 | 0.00% | [OY1](https://arcprize.org/replay/345b0563-a565-432f-90c5-084882e935ff) · [Provider Adapter](https://arcprize.org/replay/0945e840-474f-4f1f-9e47-bbcf7aa05639) |
| s5i5-18d95033 | 5 | 30 | 30 | 0.00% | [OY1](https://arcprize.org/replay/345b0563-a565-432f-90c5-084882e935ff) · [Provider Adapter](https://arcprize.org/replay/0945e840-474f-4f1f-9e47-bbcf7aa05639) |
| s5i5-18d95033 | 6 | 25 | 25 | 0.00% | [OY1](https://arcprize.org/replay/345b0563-a565-432f-90c5-084882e935ff) · [Provider Adapter](https://arcprize.org/replay/0945e840-474f-4f1f-9e47-bbcf7aa05639) |
| s5i5-18d95033 | 8 | 36 | 36 | 0.00% | [OY1](https://arcprize.org/replay/345b0563-a565-432f-90c5-084882e935ff) · [Provider Adapter](https://arcprize.org/replay/0945e840-474f-4f1f-9e47-bbcf7aa05639) |
| sb26-7fbdac44 | 1 | 9 | 9 | 0.00% | [OY1](https://arcprize.org/replay/44be6362-a967-4e92-8595-11b82f139e42) · [Provider Adapter](https://arcprize.org/replay/95542d79-8533-445b-91b0-68adfa026db8) |
| sb26-7fbdac44 | 2 | 15 | 15 | 0.00% | [OY1](https://arcprize.org/replay/44be6362-a967-4e92-8595-11b82f139e42) · [Provider Adapter](https://arcprize.org/replay/95542d79-8533-445b-91b0-68adfa026db8) |
| sb26-7fbdac44 | 3 | 15 | 15 | 0.00% | [OY1](https://arcprize.org/replay/44be6362-a967-4e92-8595-11b82f139e42) · [Provider Adapter](https://arcprize.org/replay/95542d79-8533-445b-91b0-68adfa026db8) |
| sb26-7fbdac44 | 4 | 15 | 15 | 0.00% | [OY1](https://arcprize.org/replay/44be6362-a967-4e92-8595-11b82f139e42) · [Provider Adapter](https://arcprize.org/replay/95542d79-8533-445b-91b0-68adfa026db8) |
| sb26-7fbdac44 | 5 | 17 | 17 | 0.00% | [OY1](https://arcprize.org/replay/44be6362-a967-4e92-8595-11b82f139e42) · [Provider Adapter](https://arcprize.org/replay/95542d79-8533-445b-91b0-68adfa026db8) |
| sb26-7fbdac44 | 6 | 19 | 19 | 0.00% | [OY1](https://arcprize.org/replay/44be6362-a967-4e92-8595-11b82f139e42) · [Provider Adapter](https://arcprize.org/replay/95542d79-8533-445b-91b0-68adfa026db8) |
| sb26-7fbdac44 | 7 | 17 | 17 | 0.00% | [OY1](https://arcprize.org/replay/44be6362-a967-4e92-8595-11b82f139e42) · [Provider Adapter](https://arcprize.org/replay/95542d79-8533-445b-91b0-68adfa026db8) |
| sb26-7fbdac44 | 8 | 17 | 17 | 0.00% | [OY1](https://arcprize.org/replay/44be6362-a967-4e92-8595-11b82f139e42) · [Provider Adapter](https://arcprize.org/replay/95542d79-8533-445b-91b0-68adfa026db8) |
| sc25-635fd71a | 1 | 23 | 23 | 0.00% | [OY1](https://arcprize.org/replay/e495099e-151b-41ec-b146-c1be2f71a589) · [Provider Adapter](https://arcprize.org/replay/6eaaa941-433c-41a3-b69a-a70be93c6a08) |
| sc25-635fd71a | 3 | 12 | 12 | 0.00% | [OY1](https://arcprize.org/replay/e495099e-151b-41ec-b146-c1be2f71a589) · [Provider Adapter](https://arcprize.org/replay/6eaaa941-433c-41a3-b69a-a70be93c6a08) |
| sc25-635fd71a | 4 | 23 | 23 | 0.00% | [OY1](https://arcprize.org/replay/e495099e-151b-41ec-b146-c1be2f71a589) · [Provider Adapter](https://arcprize.org/replay/6eaaa941-433c-41a3-b69a-a70be93c6a08) |
| sk48-d8078629 | 1 | 14 | 14 | 0.00% | [OY1](https://arcprize.org/replay/45d858f8-5c84-4994-87dc-f4a88502bdf8) · [Provider Adapter](https://arcprize.org/replay/5bcc0575-b75b-41eb-8361-909e886fb5b9) |
| sk48-d8078629 | 3 | 38 | 38 | 0.00% | [OY1](https://arcprize.org/replay/45d858f8-5c84-4994-87dc-f4a88502bdf8) · [Provider Adapter](https://arcprize.org/replay/5bcc0575-b75b-41eb-8361-909e886fb5b9) |
| sp80-589a99af | 5 | 33 | 33 | 0.00% | [OY1](https://arcprize.org/replay/28db70d6-cd9c-446e-bf30-9a829c12e5ba) · [Provider Adapter](https://arcprize.org/replay/f37ae900-fd49-4d08-aee4-ca124ca44392) |
| su15-1944f8ab | 4 | 9 | 9 | 0.00% | [OY1](https://arcprize.org/replay/f6101e88-def8-4e76-a78a-9427745a2385) · [Provider Adapter](https://arcprize.org/replay/bffe1ccd-c92c-44ee-abe3-d13d4185d862) |
| tn36-ef4dde99 | 3 | 10 | 10 | 0.00% | [OY1](https://arcprize.org/replay/22761359-7720-4a5c-acab-4432719a35c5) · [Provider Adapter](https://arcprize.org/replay/8d408961-f16e-419c-ad6b-12e0e697f2ca) |
| tn36-ef4dde99 | 5 | 19 | 19 | 0.00% | [OY1](https://arcprize.org/replay/22761359-7720-4a5c-acab-4432719a35c5) · [Provider Adapter](https://arcprize.org/replay/8d408961-f16e-419c-ad6b-12e0e697f2ca) |
| tr87-cd924810 | 3 | 26 | 26 | 0.00% | [OY1](https://arcprize.org/replay/34c9120b-2214-46e2-96e3-45e78d759390) · [Provider Adapter](https://arcprize.org/replay/a1e55710-322c-46ce-8969-02d8063168d7) |
| tr87-cd924810 | 4 | 21 | 21 | 0.00% | [OY1](https://arcprize.org/replay/34c9120b-2214-46e2-96e3-45e78d759390) · [Provider Adapter](https://arcprize.org/replay/a1e55710-322c-46ce-8969-02d8063168d7) |
| tr87-cd924810 | 6 | 24 | 24 | 0.00% | [OY1](https://arcprize.org/replay/34c9120b-2214-46e2-96e3-45e78d759390) · [Provider Adapter](https://arcprize.org/replay/a1e55710-322c-46ce-8969-02d8063168d7) |
| tu93-0768757b | 1 | 18 | 18 | 0.00% | [OY1](https://arcprize.org/replay/3893f733-e1bd-4827-93b6-6ff8e64171ee) · [Provider Adapter](https://arcprize.org/replay/2ae60daf-4f2e-48bc-830a-e3e37e15b881) |
| tu93-0768757b | 3 | 19 | 19 | 0.00% | [OY1](https://arcprize.org/replay/3893f733-e1bd-4827-93b6-6ff8e64171ee) · [Provider Adapter](https://arcprize.org/replay/2ae60daf-4f2e-48bc-830a-e3e37e15b881) |
| tu93-0768757b | 4 | 18 | 18 | 0.00% | [OY1](https://arcprize.org/replay/3893f733-e1bd-4827-93b6-6ff8e64171ee) · [Provider Adapter](https://arcprize.org/replay/2ae60daf-4f2e-48bc-830a-e3e37e15b881) |
| tu93-0768757b | 5 | 29 | 29 | 0.00% | [OY1](https://arcprize.org/replay/3893f733-e1bd-4827-93b6-6ff8e64171ee) · [Provider Adapter](https://arcprize.org/replay/2ae60daf-4f2e-48bc-830a-e3e37e15b881) |
| tu93-0768757b | 7 | 14 | 14 | 0.00% | [OY1](https://arcprize.org/replay/3893f733-e1bd-4827-93b6-6ff8e64171ee) · [Provider Adapter](https://arcprize.org/replay/2ae60daf-4f2e-48bc-830a-e3e37e15b881) |
| tu93-0768757b | 8 | 23 | 23 | 0.00% | [OY1](https://arcprize.org/replay/3893f733-e1bd-4827-93b6-6ff8e64171ee) · [Provider Adapter](https://arcprize.org/replay/2ae60daf-4f2e-48bc-830a-e3e37e15b881) |
| vc33-5430563c | 2 | 7 | 7 | 0.00% | [OY1](https://arcprize.org/replay/c8995261-2fa7-48b4-9fc6-e1624a20697f) · [Provider Adapter](https://arcprize.org/replay/ec8082e6-fafd-4598-92f5-aa12ee7ecf09) |
| vc33-5430563c | 3 | 24 | 24 | 0.00% | [OY1](https://arcprize.org/replay/c8995261-2fa7-48b4-9fc6-e1624a20697f) · [Provider Adapter](https://arcprize.org/replay/ec8082e6-fafd-4598-92f5-aa12ee7ecf09) |
| vc33-5430563c | 5 | 49 | 49 | 0.00% | [OY1](https://arcprize.org/replay/c8995261-2fa7-48b4-9fc6-e1624a20697f) · [Provider Adapter](https://arcprize.org/replay/ec8082e6-fafd-4598-92f5-aa12ee7ecf09) |
| vc33-5430563c | 6 | 20 | 20 | 0.00% | [OY1](https://arcprize.org/replay/c8995261-2fa7-48b4-9fc6-e1624a20697f) · [Provider Adapter](https://arcprize.org/replay/ec8082e6-fafd-4598-92f5-aa12ee7ecf09) |
| wa30-ee6fef47 | 6 | 46 | 46 | 0.00% | [OY1](https://arcprize.org/replay/6503caa5-73c0-4b5e-9fdf-9d5d8e6eb176) · [Provider Adapter](https://arcprize.org/replay/6f55299f-71ce-4d33-97a6-7043e44bce70) |
| dc22-fdcac232 | 6 | 150 | 149 | -0.67% | [OY1](https://arcprize.org/replay/20d26669-51a5-4d89-9e35-9fc329abc363) · [Provider Adapter](https://arcprize.org/replay/b436a14c-e9c5-43f3-b41d-721ccf59519a) |
| dc22-fdcac232 | 4 | 64 | 63 | -1.59% | [OY1](https://arcprize.org/replay/20d26669-51a5-4d89-9e35-9fc329abc363) · [Provider Adapter](https://arcprize.org/replay/b436a14c-e9c5-43f3-b41d-721ccf59519a) |
| dc22-fdcac232 | 2 | 43 | 42 | -2.38% | [OY1](https://arcprize.org/replay/20d26669-51a5-4d89-9e35-9fc329abc363) · [Provider Adapter](https://arcprize.org/replay/b436a14c-e9c5-43f3-b41d-721ccf59519a) |
| ka59-38d34dbb | 4 | 42 | 41 | -2.44% | [OY1](https://arcprize.org/replay/9c9af5ce-b61a-4b87-ace9-8650e84907d6) · [Provider Adapter](https://arcprize.org/replay/a6e15bfa-590a-4053-b5dc-b11e7b8b1cb4) |
| ls20-9607627b | 7 | 81 | 79 | -2.53% | [OY1](https://arcprize.org/replay/0a9dfe50-1421-45c9-8041-773c58b6b85b) · [Provider Adapter](https://arcprize.org/replay/27b4461a-7bdb-45f6-9bb0-f1487d6ce662) |
| sc25-635fd71a | 5 | 39 | 38 | -2.63% | [OY1](https://arcprize.org/replay/e495099e-151b-41ec-b146-c1be2f71a589) · [Provider Adapter](https://arcprize.org/replay/6eaaa941-433c-41a3-b69a-a70be93c6a08) |
| lf52-271a04aa | 8 | 70 | 68 | -2.94% | [OY1](https://arcprize.org/replay/79127723-14e2-4d3d-a60c-9a45e99e6575) · [Provider Adapter](https://arcprize.org/replay/e1ef8feb-5393-4a69-9780-b6f7ef48ba93) |
| ka59-38d34dbb | 3 | 34 | 33 | -3.03% | [OY1](https://arcprize.org/replay/9c9af5ce-b61a-4b87-ace9-8650e84907d6) · [Provider Adapter](https://arcprize.org/replay/a6e15bfa-590a-4053-b5dc-b11e7b8b1cb4) |
| wa30-ee6fef47 | 4 | 54 | 52 | -3.85% | [OY1](https://arcprize.org/replay/6503caa5-73c0-4b5e-9fdf-9d5d8e6eb176) · [Provider Adapter](https://arcprize.org/replay/6f55299f-71ce-4d33-97a6-7043e44bce70) |
| ka59-38d34dbb | 1 | 25 | 24 | -4.17% | [OY1](https://arcprize.org/replay/9c9af5ce-b61a-4b87-ace9-8650e84907d6) · [Provider Adapter](https://arcprize.org/replay/a6e15bfa-590a-4053-b5dc-b11e7b8b1cb4) |
| ls20-9607627b | 3 | 43 | 41 | -4.88% | [OY1](https://arcprize.org/replay/0a9dfe50-1421-45c9-8041-773c58b6b85b) · [Provider Adapter](https://arcprize.org/replay/27b4461a-7bdb-45f6-9bb0-f1487d6ce662) |
| ar25-0c556536 | 1 | 17 | 16 | -6.25% | [OY1](https://arcprize.org/replay/74077944-f734-4895-adce-ae20e4d916fc) · [Provider Adapter](https://arcprize.org/replay/1550f0c9-c286-4e15-84f9-178c5c9f97ff) |
| ar25-0c556536 | 5 | 31 | 29 | -6.90% | [OY1](https://arcprize.org/replay/74077944-f734-4895-adce-ae20e4d916fc) · [Provider Adapter](https://arcprize.org/replay/1550f0c9-c286-4e15-84f9-178c5c9f97ff) |
| su15-1944f8ab | 3 | 15 | 14 | -7.14% | [OY1](https://arcprize.org/replay/f6101e88-def8-4e76-a78a-9427745a2385) · [Provider Adapter](https://arcprize.org/replay/bffe1ccd-c92c-44ee-abe3-d13d4185d862) |
| bp35-0a0ad940 | 2 | 43 | 40 | -7.50% | [OY1](https://arcprize.org/replay/bcd43d66-ac98-43c2-8221-f6e872c7d1c2) · [Provider Adapter](https://arcprize.org/replay/fbab92cd-0b28-4d8d-88f6-83a54b7aacfb) |
| su15-1944f8ab | 2 | 13 | 12 | -8.33% | [OY1](https://arcprize.org/replay/f6101e88-def8-4e76-a78a-9427745a2385) · [Provider Adapter](https://arcprize.org/replay/bffe1ccd-c92c-44ee-abe3-d13d4185d862) |
| ls20-9607627b | 4 | 51 | 47 | -8.51% | [OY1](https://arcprize.org/replay/0a9dfe50-1421-45c9-8041-773c58b6b85b) · [Provider Adapter](https://arcprize.org/replay/27b4461a-7bdb-45f6-9bb0-f1487d6ce662) |
| ka59-38d34dbb | 7 | 109 | 99 | -10.10% | [OY1](https://arcprize.org/replay/9c9af5ce-b61a-4b87-ace9-8650e84907d6) · [Provider Adapter](https://arcprize.org/replay/a6e15bfa-590a-4053-b5dc-b11e7b8b1cb4) |
| tn36-ef4dde99 | 1 | 10 | 9 | -11.11% | [OY1](https://arcprize.org/replay/22761359-7720-4a5c-acab-4432719a35c5) · [Provider Adapter](https://arcprize.org/replay/8d408961-f16e-419c-ad6b-12e0e697f2ca) |
| cd82-fb555c5d | 3 | 19 | 17 | -11.76% | [OY1](https://arcprize.org/replay/20fcc634-9e4e-4c3d-a638-b577b0301cd1) · [Provider Adapter](https://arcprize.org/replay/fdc50b7b-de6f-4838-9e05-10ee63bf9725) |
| lf52-271a04aa | 1 | 9 | 8 | -12.50% | [OY1](https://arcprize.org/replay/79127723-14e2-4d3d-a60c-9a45e99e6575) · [Provider Adapter](https://arcprize.org/replay/e1ef8feb-5393-4a69-9780-b6f7ef48ba93) |
| sp80-589a99af | 2 | 9 | 8 | -12.50% | [OY1](https://arcprize.org/replay/28db70d6-cd9c-446e-bf30-9a829c12e5ba) · [Provider Adapter](https://arcprize.org/replay/f37ae900-fd49-4d08-aee4-ca124ca44392) |
| sk48-d8078629 | 2 | 34 | 30 | -13.33% | [OY1](https://arcprize.org/replay/45d858f8-5c84-4994-87dc-f4a88502bdf8) · [Provider Adapter](https://arcprize.org/replay/5bcc0575-b75b-41eb-8361-909e886fb5b9) |
| sk48-d8078629 | 5 | 117 | 103 | -13.59% | [OY1](https://arcprize.org/replay/45d858f8-5c84-4994-87dc-f4a88502bdf8) · [Provider Adapter](https://arcprize.org/replay/5bcc0575-b75b-41eb-8361-909e886fb5b9) |
| vc33-5430563c | 1 | 8 | 7 | -14.29% | [OY1](https://arcprize.org/replay/c8995261-2fa7-48b4-9fc6-e1624a20697f) · [Provider Adapter](https://arcprize.org/replay/ec8082e6-fafd-4598-92f5-aa12ee7ecf09) |
| g50t-5849a774 | 1 | 28 | 24 | -16.67% | [OY1](https://arcprize.org/replay/4dbaf973-d3af-4aac-a325-0f0f8a4041e6) · [Provider Adapter](https://arcprize.org/replay/9ab081d6-34d8-4769-bdce-968b829f1091) |
| wa30-ee6fef47 | 8 | 127 | 108 | -17.59% | [OY1](https://arcprize.org/replay/6503caa5-73c0-4b5e-9fdf-9d5d8e6eb176) · [Provider Adapter](https://arcprize.org/replay/6f55299f-71ce-4d33-97a6-7043e44bce70) |
| lf52-271a04aa | 2 | 44 | 37 | -18.92% | [OY1](https://arcprize.org/replay/79127723-14e2-4d3d-a60c-9a45e99e6575) · [Provider Adapter](https://arcprize.org/replay/e1ef8feb-5393-4a69-9780-b6f7ef48ba93) |
| sp80-589a99af | 4 | 31 | 26 | -19.23% | [OY1](https://arcprize.org/replay/28db70d6-cd9c-446e-bf30-9a829c12e5ba) · [Provider Adapter](https://arcprize.org/replay/f37ae900-fd49-4d08-aee4-ca124ca44392) |
| su15-1944f8ab | 7 | 6 | 5 | -20.00% | [OY1](https://arcprize.org/replay/f6101e88-def8-4e76-a78a-9427745a2385) · [Provider Adapter](https://arcprize.org/replay/bffe1ccd-c92c-44ee-abe3-d13d4185d862) |
| sk48-d8078629 | 6 | 83 | 67 | -23.88% | [OY1](https://arcprize.org/replay/45d858f8-5c84-4994-87dc-f4a88502bdf8) · [Provider Adapter](https://arcprize.org/replay/5bcc0575-b75b-41eb-8361-909e886fb5b9) |
| sp80-589a99af | 1 | 9 | 7 | -28.57% | [OY1](https://arcprize.org/replay/28db70d6-cd9c-446e-bf30-9a829c12e5ba) · [Provider Adapter](https://arcprize.org/replay/f37ae900-fd49-4d08-aee4-ca124ca44392) |
| tn36-ef4dde99 | 7 | 44 | 33 | -33.33% | [OY1](https://arcprize.org/replay/22761359-7720-4a5c-acab-4432719a35c5) · [Provider Adapter](https://arcprize.org/replay/8d408961-f16e-419c-ad6b-12e0e697f2ca) |
| su15-1944f8ab | 1 | 11 | 8 | -37.50% | [OY1](https://arcprize.org/replay/f6101e88-def8-4e76-a78a-9427745a2385) · [Provider Adapter](https://arcprize.org/replay/bffe1ccd-c92c-44ee-abe3-d13d4185d862) |
| sk48-d8078629 | 4 | 49 | 35 | -40.00% | [OY1](https://arcprize.org/replay/45d858f8-5c84-4994-87dc-f4a88502bdf8) · [Provider Adapter](https://arcprize.org/replay/5bcc0575-b75b-41eb-8361-909e886fb5b9) |
| m0r0-492f87ba | 5 | 64 | 44 | -45.45% | [OY1](https://arcprize.org/replay/b3c4fd9b-d852-422c-9fe0-35271646bd6d) · [Provider Adapter](https://arcprize.org/replay/50d61a09-c2b8-4354-9312-de22c65eb9b7) |
| vc33-5430563c | 4 | 35 | 24 | -45.83% | [OY1](https://arcprize.org/replay/c8995261-2fa7-48b4-9fc6-e1624a20697f) · [Provider Adapter](https://arcprize.org/replay/ec8082e6-fafd-4598-92f5-aa12ee7ecf09) |
| tu93-0768757b | 2 | 15 | 10 | -50.00% | [OY1](https://arcprize.org/replay/3893f733-e1bd-4827-93b6-6ff8e64171ee) · [Provider Adapter](https://arcprize.org/replay/2ae60daf-4f2e-48bc-830a-e3e37e15b881) |
| tn36-ef4dde99 | 2 | 19 | 11 | -72.73% | [OY1](https://arcprize.org/replay/22761359-7720-4a5c-acab-4432719a35c5) · [Provider Adapter](https://arcprize.org/replay/8d408961-f16e-419c-ad6b-12e0e697f2ca) |
| su15-1944f8ab | 5 | 28 | 14 | -100.00% | [OY1](https://arcprize.org/replay/f6101e88-def8-4e76-a78a-9427745a2385) · [Provider Adapter](https://arcprize.org/replay/bffe1ccd-c92c-44ee-abe3-d13d4185d862) |
| lp85-305b61c3 | 7 | 14 | 5 | -180.00% | [OY1](https://arcprize.org/replay/320e870c-f647-4afb-8ba6-70cd496b540c) · [Provider Adapter](https://arcprize.org/replay/a478cd77-33fa-4289-a05b-7391809359a8) |
| lp85-305b61c3 | 8 | 20 | 7 | -185.71% | [OY1](https://arcprize.org/replay/320e870c-f647-4afb-8ba6-70cd496b540c) · [Provider Adapter](https://arcprize.org/replay/a478cd77-33fa-4289-a05b-7391809359a8) |
| re86-8af5384d | 3 | 189 | 47 | -302.13% | [OY1](https://arcprize.org/replay/e77ef5ea-f632-4b56-abdd-5d857634c408) · [Provider Adapter](https://arcprize.org/replay/d846db33-73ea-4066-b3be-0befc6c2dbc5) |

## Verify the counts

[Machine-readable comparison](../evidence/public-level-comparison.json) includes
recording hashes and observation-row boundaries for every level.
With Python 3.9 or newer, run:

```sh
python3 -B tools/verify_level_comparison.py --cache /tmp/oy1-level-comparison
```

The verifier downloads both sets of public recordings, checks their hashes,
recomputes every level count and verifies the highlight ranking. It makes no
model calls. Keep the recording cache outside the repository.
