# ADR-0005: Dual runtime — Host Runtime and Cluster Runtime

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 |
| Related | [ADR-0006](ADR-0006-control-data-plane-separation.md), [ADR-0007](ADR-0007-degradation-ladder.md), [ADR-0020](ADR-0020-kubernetes-cloud-portable.md) |

## Context

MASTER_PLAN v1.0 assumed one process on one Windows box. That is a fine starting point and
a poor ending one: STT and TTS inference want a GPU, memory wants to persist independently
of the agent, and the brain may live anywhere. But some components are pinned to the
physical machine by hardware access and cannot move regardless of how much we would like
them to.

The question is not "monolith or distributed" — it is **which seam is real**.

## Decision

Two runtimes, separated by a **hardware-affinity boundary**, not by a layer diagram.

### Host Runtime — Windows, present at every tier

Owns anything that touches physical devices or must respond without a network in the path.

| Component | Why it cannot move |
|---|---|
| Audio capture / playback | Physical device access; no acceptable-latency virtualization |
| Wake-word detection | Latency, **and privacy** — raw audio must not cross a network boundary before the wake word fires |
| VAD / endpointing | Must run in the capture path |
| InterruptController | 300 ms barge-in budget with no network hop available |
| Session state | The conversation belongs to the person at the machine |
| Local filesystem capability | The files are on this machine |

### Cluster Runtime — placement-flexible

Everything else: Memory Service, Brain Gateway, STT inference, TTS inference, non-local
capabilities. Addressed by URI, not by import.

**The critical property:** cluster services are *the same libraries* the host uses, wrapped
in thin entrypoints under `src/lionel/services/`. At L0 they run in-process; at L2 they run
as pods. **There is no code fork between the two.**

## Consequences

### Positive
- Heavy inference can use cluster GPU without moving the microphone.
- Cluster services restart without losing the conversation, because session state is
  host-owned and every cluster service is stateless
  ([ADR-0008](ADR-0008-coordinator-decomposition.md)).
- Privacy has a structural guarantee, not a policy one: audio physically cannot leave the
  machine before wake.

### Negative / Costs
- Every host↔cluster call is now a network call with failure modes. Mitigated by
  per-call timeouts, circuit breakers, and declared degraded behavior.
- Two deployment targets to build and test.
- Latency budget must be re-measured at every tier, not measured once.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Single process (v1.0) | No path to GPU inference, no independent scaling, no upgrade story |
| Everything in the cluster, thin host client | Audio would have to stream over the network before wake — unacceptable on latency **and** privacy |
| Microservice-per-module | Boundaries that don't correspond to a real constraint create network calls where a function call belonged |

## Verification

Gate **G7**. The same component runs in-process at L0 and as a pod at L2 with no source
change — only configuration. Verified by running the full voice loop at both tiers from a
single build.
