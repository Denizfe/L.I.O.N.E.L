# ADR-0019: OpenTelemetry as the observability substrate

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 5 — **before** distribution |
| Related | [ADR-0006](ADR-0006-control-data-plane-separation.md), [ADR-0020](ADR-0020-kubernetes-cloud-portable.md), [ADR-0015](ADR-0015-secret-resolver.md) |

## Context

MASTER_PLAN v1.0 had no tracing, no metrics, and no structured event model. Its Phase 4
latency budget — six stages, each with a target, totalling under 2.5 s — was therefore
**unmeasurable and unenforceable.** The Definition of Done asked for a stopwatch reading
pasted into a Markdown file, once.

The original proposal placed observability at position 14, after Kubernetes. That ordering
is backwards. Phase 7 turns a single process into a distributed system, and debugging a
distributed system you cannot trace is the most expensive technical debt available.

## Decision

**OpenTelemetry throughout, landing in Phase 5 — before Kubernetes.**

### Traces
`turn_id` **is** the trace ID, propagated across both planes
([ADR-0006](ADR-0006-control-data-plane-separation.md)) and both runtimes
([ADR-0005](ADR-0005-dual-runtime.md)). One trace shows wake → capture → STT → recall →
brain → tool calls → synthesis → playback.

### Metrics
- Latency histogram **per pipeline stage, mapped 1:1 to the budget** in
  `docs/LATENCY_BUDGET.md`. The budget becomes a Prometheus alert instead of a stopwatch.
- Token and cost counters per provider ([ADR-0009](ADR-0009-extended-brain-provider-contract.md)).
- Tool-call success/denial rates ([ADR-0012](ADR-0012-policy-engine.md)).
- Wake-word FAR/FRR.

### Logs
Structured JSON (`structlog`), correlated by `turn_id`, **with secret redaction at the
formatter** — belt and braces alongside `SecretStr`
([ADR-0015](ADR-0015-secret-resolver.md)).

### Backend
OTel Collector → Prometheus / Tempo / Loki, Grafana on top. Runs in the Cluster Runtime.

### The L0 requirement
**The Host Runtime buffers telemetry to disk when the collector is unreachable and flushes
on reconnect.** L0 has no cluster and must still produce telemetry — otherwise the tier we
care most about is the one we can least observe.

## Consequences

### Positive
- The latency budget becomes enforceable, which is the difference between a target and a
  requirement.
- Phase 7 debugging is tractable.
- Regressions are detectable before they ship ([ADR-0021](ADR-0021-eval-harness-gates.md)).

### Negative / Costs
- Instrumentation overhead in code and at runtime; sampling configured per tier.
- An observability stack to run — real operational weight. Offset by using it to debug
  everything after Phase 5.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Observability after Kubernetes (proposal ordering) | Creates a distributed system with no way to see inside it |
| Logs only | Cannot express a distributed trace or a latency distribution |
| A vendor APM SDK | Lock-in, and most are network-dependent — breaks L0 |
| Manual timing in code | v1.0's implicit approach. Does not compose or aggregate |

## Verification

Gate **G5**. One trace spans an entire turn across both planes; every budget stage emits a
histogram; **a deliberate budget violation fires an alert**; no secrets appear in logs under
a fuzzing pass; **the host buffers telemetry offline and flushes on reconnect**.
