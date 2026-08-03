# ADR-0024: Robotics capability and safety model

| | |
|---|---|
| Status | **Provisional** — direction agreed; details deferred to G9 |
| Date | 2026-08-02 |
| Phase | 10 — **horizon, not committed** |
| Related | [ADR-0012](ADR-0012-policy-engine.md), [ADR-0026](ADR-0026-side-effect-classification.md), [ADR-0020](ADR-0020-kubernetes-cloud-portable.md) |

## Context

Robotics appeared in the v2.0 review criteria as a future consideration. It is not
scheduled. This ADR exists to record the decisions that would be **expensive to reverse**,
so that today's architecture does not preclude it.

Physical actuation differs from software capabilities in one respect that matters
architecturally: **the consequences are not undoable.** A bad file write can be restored
from backup. A bad arm movement cannot.

## Decision (provisional)

### The capability model already fits
`arm.move_to(pose)` is a typed tool with a schema and a policy — structurally identical to
`fs.write(path, content)`. [ADR-0011](ADR-0011-capability-tools-no-shell.md) and
[ADR-0012](ADR-0012-policy-engine.md) require no change to accommodate actuators. This is a
useful confirmation that those decisions were made at the right level of abstraction.

### The one rule that must never be violated

> **Hardware safety interlocks live in the Policy Engine and in hardware. Never in the
> prompt. A language model must never be the last line of defence before a motor.**

Envelope limits, velocity ceilings, emergency stop, and human-proximity constraints are
enforced by [ADR-0012](ADR-0012-policy-engine.md) as declarative rules and, where the
hardware supports it, by the hardware itself. The model *requests*; the policy engine and
the hardware *permit*.

### Preparations already in place
- **Multi-arch images** (arm64) from [ADR-0020](ADR-0020-kubernetes-cloud-portable.md) —
  Jetson and similar are already a target.
- **Data-plane separation** ([ADR-0006](ADR-0006-control-data-plane-separation.md)) — sensor
  streams reuse the same pattern as audio.
- **A reserved ROS 2 / DDS interop seam** on the data plane
  ([ADR-0028](ADR-0028-data-plane-transport.md)).
- **Side-effect classification** ([ADR-0026](ADR-0026-side-effect-classification.md)) —
  physical actions are `destructive` by default, and irreversibility is the reason the
  category exists.

### Deferred to G9
Real-time guarantees on the data plane, hardware E-stop integration, sensor fusion, and
whether ROS 2 is adopted at all.

## Consequences

### Positive
- No architectural work is wasted if robotics is pursued; none is required if it is not.
- The safety principle is recorded now, while it is cheap, rather than argued later under
  schedule pressure.

### Negative / Costs
- A provisional ADR can read as speculative. Mitigated by keeping it narrow: it commits to
  a safety principle and records existing preparations. Nothing more.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Say nothing about robotics | Risks an architectural choice that forecloses it — the multi-arch decision in particular |
| Design the full stack now | Speculative work against unknown hardware |
| Model-level safety via prompting | The specific thing this ADR exists to forbid |

## Verification

Gate **G10** — not committed. At **G9**, confirm no decision taken in Phases 0–9 forecloses
this path.
