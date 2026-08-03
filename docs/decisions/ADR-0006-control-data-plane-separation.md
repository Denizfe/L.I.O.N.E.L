# ADR-0006: Control plane / data plane separation

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 |
| Amends | [ADR-0003](ADR-0003-mcp-first-capability-model.md) |
| Related | [ADR-0028](ADR-0028-data-plane-transport.md), [ADR-0019](ADR-0019-opentelemetry.md) |

## Context

[ADR-0003](ADR-0003-mcp-first-capability-model.md) says every capability is MCP. Read
literally, that would put 16 kHz PCM audio inside JSON-RPC messages. The consequences:

- **~33% inflation** from base64 encoding on the highest-volume path in the system.
- **No backpressure.** JSON-RPC has no flow control; a slow consumer has no way to say so.
- **Head-of-line blocking.** An audio frame queues behind an unrelated tool call.
- **No jitter buffer, no frame sequencing, no drop semantics.**

This would work in a demo and collapse under a real conversation.

## Decision

Two planes with different protocols, different failure semantics, and a hard rule at the
boundary.

| | Control Plane | Data Plane |
|---|---|---|
| **Carries** | Tool calls, capability discovery, memory ops, config, health | Audio frames, partial transcripts, synthesized PCM, future video |
| **Protocol** | **MCP** (JSON-RPC 2.0) | **gRPC bidirectional streaming** ([ADR-0028](ADR-0028-data-plane-transport.md)) |
| **Transport** | stdio at L0 → Streamable HTTP at L1+ | HTTP/2 |
| **Shape** | Request/response, low volume, high semantic value | Continuous, high volume, latency-critical |
| **On failure** | Retry with idempotency key ([ADR-0026](ADR-0026-side-effect-classification.md)) | Drop frames, degrade quality — **never block** |
| **Ordering** | Per-request | Strict, sequence-numbered |

### The two rules

1. **No PCM ever crosses the control plane.**
2. **No control decision ever rides the media stream.**

### What binds them

Every turn carries a **`turn_id`**, which is also the OpenTelemetry trace ID on both planes.
One trace shows wake → capture → STT → recall → brain → tools → synthesis → playback,
across both protocols and both runtimes.

## Consequences

### Positive
- Media gets real backpressure, sequencing, and drop semantics.
- A saturated audio stream cannot starve tool dispatch, and a slow tool cannot stutter audio.
- The planes scale independently — the usual reason this pattern exists.

### Negative / Costs
- Two protocols to implement, secure, and observe.
- The `turn_id` correlation is load-bearing. If it breaks, debugging gets much worse — which
  is why [ADR-0019](ADR-0019-opentelemetry.md) lands in Phase 5, before distribution.

### Neutral
- ADR-0003 is narrowed, not weakened: everything *controllable* is still MCP.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Everything over MCP | The failure modes above. This is the proposal this ADR exists to reject |
| Everything over gRPC | Loses the MCP ecosystem, third-party servers, and standard tooling for zero benefit on the control path |
| MCP with a side-channel file handle | Half-measure; inherits the worst of both and complicates cancellation |

## Verification

Gate **G5**. A single trace spans an entire turn across both planes, correlated by
`turn_id`. Gate **G6d**: a saturated data plane does not delay control-plane tool dispatch.
