# ADR-0025: Cancellation and backpressure architecture

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 |
| Related | [ADR-0008](ADR-0008-coordinator-decomposition.md), [ADR-0009](ADR-0009-extended-brain-provider-contract.md), [ADR-0026](ADR-0026-side-effect-classification.md) |

## Context

MASTER_PLAN v1.0 required barge-in — speaking the wake word mid-response aborts playback
within 300 ms — and described **the requirement without the mechanism.**

Meeting it means cancelling, concurrently: audio playback, TTS synthesis, brain token
generation, and any in-flight tool call. Some of those are in another process. After Phase
7, some are on another machine. Cancellation that is retrofitted never reaches every call
site, and the ones it misses become orphaned work: a synthesis job still rendering, a tool
call still writing.

## Decision

### One token per turn
A `CancellationToken` created by `SessionCoordinator`, propagated to **every** async
operation in the turn. Non-optional on the `BrainProvider` interface
([ADR-0009](ADR-0009-extended-brain-provider-contract.md)) — optional cancellation is
cancellation that some paths will not have.

### Fan-out order is specified, not incidental

`InterruptController` cancels in this order, and the order is the design:

1. **Stop audio playback** — the user-perceptible effect. This is what "300 ms" measures.
2. **Abort TTS synthesis** — stop producing audio nobody will hear.
3. **Cancel brain streaming** — stop generating text nobody will synthesize.
4. **Cancel in-flight tool calls** — governed by side-effect class below.

Cheapest and most visible first; the user perceives responsiveness even while the tail
unwinds.

### Tool cancellation depends on side-effect class

Per [ADR-0026](ADR-0026-side-effect-classification.md):

| Class | On cancel |
|---|---|
| `read` | Abort freely. No consequences |
| `write` | **Complete or roll back. Never abandon mid-flight** — a half-written file is worse than either outcome |
| `destructive` | Same as `write`, and always audited |

### Backpressure
The data plane applies backpressure by **dropping frames, never by blocking**. A blocked
data plane stalls the control plane and produces the exact stutter the plane separation in
[ADR-0006](ADR-0006-control-data-plane-separation.md) exists to prevent.

### Across the runtime boundary
gRPC stream cancellation carries the token to cluster services. MCP calls carry it as
request metadata. **Cancellation must cross the boundary**, or L2 barge-in leaves orphaned
cluster work.

## Consequences

### Positive
- Barge-in is achievable rather than aspirational.
- No orphaned work: no zombie synthesis, no half-finished tool call.
- The same mechanism serves timeouts, shutdown, and error unwinding — cancellation is not
  a barge-in special case.

### Negative / Costs
- Every async call site carries a token. Verbose, and the verbosity is the guarantee.
- Rollback semantics for `write` tools are real work per tool.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Task cancellation only, no explicit token | Does not cross process or network boundaries |
| Kill the subprocess | Loses rollback for writes; leaves inconsistent state |
| Ignore in-flight work; let it finish | Orphaned synthesis plays over the next turn. Directly user-visible |
| Optional cancellation parameter | The paths that omit it are exactly the ones that will hang |

## Verification

Gate **G3**: a token aborts a streaming generation within 200 ms. Gate **G6d**: barge-in
aborts playback within 300 ms and **leaves zero orphaned work** — no running synthesis, no
in-flight tool call.
