# ADR-0008: Coordinator decomposition — no god loop

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 |
| Replaces | v1.0's `host/loop.py` |
| Related | [ADR-0025](ADR-0025-cancellation-backpressure.md), [ADR-0005](ADR-0005-dual-runtime.md) |

## Context

MASTER_PLAN v1.0 specified `host/loop.py` as "the agent loop: perceive → think → act →
speak." That is four responsibilities with four different concurrency models and four
different failure modes, fused into one module. Left alone it would also accumulate session
state, prompt assembly, tool dispatch, streaming, interrupt handling, and error recovery.

By Phase 4 it becomes the file nobody opens voluntarily, every feature touches it, and
barge-in becomes unimplementable because cancellation has no seam to pass through.

## Decision

Five coordinators. One responsibility each, one failure mode each, one test suite each.

| Coordinator | Owns | Explicitly does not know |
|---|---|---|
| **SessionCoordinator** | Session lifecycle, turn queue, conversation state, wake/sleep | How a turn is executed |
| **TurnExecutor** | One turn: brain call → tool loop → response assembly | Where the brain runs; which provider |
| **ContextAssembler** | System prompt, memory recall, history windowing, token budget | The brain's wire format |
| **ToolRouter** | Capability discovery, policy evaluation, MCP dispatch, result normalization | What any specific tool does |
| **InterruptController** | Barge-in detection, cancellation fan-out, cleanup | What is being cancelled |

### State ownership rule

**SessionCoordinator holds all mutable session state. Every other component is stateless
and receives what it needs as arguments.**

This is not stylistic. It is what allows a cluster service to be restarted mid-conversation
without losing the conversation, and it is a hard prerequisite for L2 in
[ADR-0007](ADR-0007-degradation-ladder.md).

## Consequences

### Positive
- Each coordinator is unit-testable in isolation with stub collaborators.
- Cancellation has an owner and a defined fan-out path
  ([ADR-0025](ADR-0025-cancellation-backpressure.md)).
- Policy enforcement has exactly one chokepoint — ToolRouter — so it cannot be bypassed.
- Cluster services become restartable, which is what makes L2 viable.

### Negative / Costs
- More files, more indirection, more interfaces to keep coherent. Real cost, paid once,
  cheapest now while nothing is implemented.
- Passing state explicitly is more verbose than reaching for an instance attribute. That
  verbosity is the property doing the work.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| One loop, refactor later (v1.0) | "Later" arrives after the state is already entangled. This review exists because doing it now costs zero |
| Two components (loop + tools) | Leaves prompt assembly and interrupts homeless; they would settle in the loop |
| Event bus between fine-grained handlers | Control flow becomes non-local and much harder to trace. Explicit coordinators keep the turn readable end to end |

## Verification

Gate **G1**. Coordinators exist as contract-conforming shells and pass contract tests with
stub implementations. Gate **G6d**: cancellation fan-out leaves zero orphaned work.
