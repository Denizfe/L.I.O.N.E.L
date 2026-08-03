
A local-first, voice-driven autonomous agent. Bilingual (English / Turkish), MCP-native,
and designed to work with the network unplugged.

## Status

**Phase 0 — Contracts & Foundations.** No implementation code yet, by design.
ADRs and interface contracts land before the code they constrain.

## Read these first

| Document | Purpose |
|---|---|
| [MASTER_PLAN_v2.md](MASTER_PLAN_v2.md) | **Authoritative blueprint.** Start here |
| [docs/decisions/](docs/decisions/README.md) | 28 ADRs. Every decision, with its rejected alternatives |
| [docs/LATENCY_BUDGET.md](docs/LATENCY_BUDGET.md) | Per-stage targets, wired to alerts from Phase 5 |
| [MASTER_PLAN_v1.md](MASTER_PLAN_v1.md) | Historical. Superseded in full by v2.0 |
| [CI_Architecture.md](CI_Architecture.md) | How the policy pipeline is built, and why |
| [CI_Inventory.md](CI_Inventory.md) | The 16 gates, and which ADR each enforces |
| [Policy_Gates.md](Policy_Gates.md) | All 88 rules, with triggers |
| [Artifact_Verification_Report.md](Artifact_Verification_Report.md) | Artifact reproducibility state |

## The one thing to understand

**ADR-0007 — the Degradation Ladder.** Four tiers, L0 (fully offline) through L3 (cloud
brain). **L0 conformance is a blocking CI gate on every release.**

A change that improves L2 or L3 while breaking L0 is a rejected change, not a tradeoff.
Every other decision in this project is downstream of that rule.

## Architecture in one paragraph

Two runtimes split along a hardware-affinity boundary: the **Host Runtime** owns anything
touching physical devices or requiring sub-300 ms response — audio, wake word, interrupts,
session state — and the **Cluster Runtime** holds everything relocatable. Two planes:
**MCP** carries control (tool calls, memory, config), **gRPC** carries media. PCM never
crosses MCP; control decisions never ride the media stream. Both are correlated by a
`turn_id` that doubles as the OpenTelemetry trace ID.

## Non-negotiables

- **No arbitrary shell execution.** Anywhere. Ever. (ADR-0011)
- **No autonomous commits.** Code is staged and presented; Efe approves; then `[LIONEL-CORE]`.
- **L0 must always pass.** (ADR-0007)

## CI

```bash
bash ci/run_gates.sh          # all 16 policy gates
bash ci/self_test.sh          # prove the gates catch violations
```

16 gates enforce 19 of 28 ADRs. `artifacts` is red by design until every artifact digest
is pinned. An architectural rule with no test is a preference.
=======
# L.I.O.N.E.L
>>>>>>> 69d0234becd74812ef4803dc2ef0a8cf4a7e3eba
