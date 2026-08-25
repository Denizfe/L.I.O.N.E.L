# L.I.O.N.E.L

A local-first, voice-driven autonomous agent. Bilingual (English / Turkish), MCP-native,
and designed to work with the network unplugged.

## Status

**Phase 1 — Host Runtime Skeleton & Control Plane.** Gate G1, open since
architecture 1.6.0 (2026-08-24). Phase 0 is frozen and signed off; `STRUCT-004`, which
forbade any runtime code, is lifted but dormant rather than deleted.

ADRs and interface contracts land before the code they constrain, and they did: 33 ADRs
and 30 contracts were frozen before the first line of `src/lionel/` was written.

## Read these first

| Document | Purpose |
|---|---|
| [MASTER_PLAN_v2.md](MASTER_PLAN_v2.md) | **Authoritative blueprint.** Start here |
| [docs/decisions/](docs/decisions/README.md) | 33 ADRs. Every decision, with its rejected alternatives |
| [docs/LATENCY_BUDGET.md](docs/LATENCY_BUDGET.md) | Per-stage targets, wired to alerts from Phase 5 |
| [MASTER_PLAN_v1.md](MASTER_PLAN_v1.md) | Historical. Superseded in full by v2.0 |
| [CI_Architecture.md](CI_Architecture.md) | How the policy pipeline is built, and why |
| [CI_Inventory.md](CI_Inventory.md) | The gates, and which ADR each enforces. **Generated** |
| [Policy_Gates.md](Policy_Gates.md) | Every rule, with its trigger. **Generated** |
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
bash ci/run_gates.sh          # every policy gate
bash ci/self_test.sh          # prove the gates catch violations
```

An architectural rule with no test is a preference. The live counts — gates, rules,
workflow jobs — are in [CI_Inventory.md](CI_Inventory.md), which is generated from the
pipeline rather than written by hand.

They are not repeated here on purpose. Every number this file used to state had gone
stale, including the status above; `doc-claims` (ADR-0033) measures count-shaped claims
in three registered documents, and this was not one of them.

```bash
bash scripts/check_env.sh     # is THIS machine ready? (the host, not the repo)
```
