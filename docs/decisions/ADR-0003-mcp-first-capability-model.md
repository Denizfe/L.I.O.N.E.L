# ADR-0003: MCP-first capability model

| | |
|---|---|
| Status | **Accepted** — carried forward from MASTER_PLAN v1.0 |
| Date | 2026-08-01, amended 2026-08-02 |
| Phase | 0 |
| Amended by | [ADR-0006](ADR-0006-control-data-plane-separation.md) |
| Related | [ADR-0011](ADR-0011-capability-tools-no-shell.md), [ADR-0012](ADR-0012-policy-engine.md) |

## Context

An agent accumulates capabilities forever. Without a single boundary, each new capability
arrives with its own calling convention, its own error shape, and its own place in the core
loop — and the core loop becomes the union of every integration ever added.

## Decision

**Every capability L.I.O.N.E.L has is an MCP server.** This includes first-party
capabilities we write ourselves. There is no privileged internal API into the core.

Adding a capability means writing a server and registering it in
`config/capabilities.registry.json`. It never means editing `core/`.

## Amendment (2026-08-02)

**MCP is the *control* protocol, not the transport for everything.** Continuous media —
audio frames, synthesized PCM, future video — travels the data plane instead. See
[ADR-0006](ADR-0006-control-data-plane-separation.md). This amendment narrows the scope of
"everything is MCP" without weakening it: everything *controllable* is MCP.

## Consequences

### Positive
- Uniform discovery, schema, and error semantics across every capability.
- One place to enforce authorization ([ADR-0012](ADR-0012-policy-engine.md)) — a policy
  engine at the MCP boundary covers all capabilities by construction.
- Capabilities are relocatable. The same server runs in-process at L0 and as a pod at L2
  because the caller only knows a protocol, not an import path.
  ([ADR-0007](ADR-0007-degradation-ladder.md))

### Negative / Costs
- Protocol overhead on calls that could have been function calls. Acceptable: tool calls
  are low-frequency and high-value; the media path that *would* suffer is explicitly
  excluded by ADR-0006.
- Each capability needs a schema. This is a cost that pays for itself at the policy layer.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Python plugin interface for first-party, MCP for third-party | Two capability models, two policy enforcement points, two test strategies. The split would drift |
| Direct function calls with MCP only at the edge | Loses relocatability, which Phase 7 depends on entirely |

## Verification

Gate **G4**. Every capability is reachable only through the MCP boundary; the Policy
Engine sees 100% of tool invocations, verified by audit-log completeness.
