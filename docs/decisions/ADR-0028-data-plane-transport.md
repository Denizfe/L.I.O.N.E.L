# ADR-0028: Data-plane transport selection

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 6 |
| Related | [ADR-0006](ADR-0006-control-data-plane-separation.md), [ADR-0022](ADR-0022-zero-trust-runtimes.md), [ADR-0024](ADR-0024-robotics-capability-safety.md) |

## Context

[ADR-0006](ADR-0006-control-data-plane-separation.md) establishes that continuous media
needs its own transport. This ADR selects it.

Requirements: bidirectional streaming (audio in, partial transcripts out; text in, PCM out),
backpressure, sequencing, low overhead, cancellation that crosses the runtime boundary
([ADR-0025](ADR-0025-cancellation-backpressure.md)), mTLS support
([ADR-0022](ADR-0022-zero-trust-runtimes.md)), and a Python implementation good enough to
sit on the latency-critical path.

## Decision

**gRPC bidirectional streaming over HTTP/2.**

| Requirement | How gRPC satisfies it |
|---|---|
| Bidirectional streaming | Native |
| Backpressure | HTTP/2 flow control |
| Sequencing | Ordered streams; explicit sequence numbers in the message schema |
| Overhead | Protobuf binary — no base64 inflation |
| Cancellation | Native stream cancellation, carries the token across the boundary |
| mTLS | First-class |
| Kubernetes | Well-understood; standard load-balancing and observability |

Service definitions live in `contracts/grpc/`, versioned alongside the MCP schemas.

### WebRTC — deferred, not rejected

WebRTC is the better answer for NAT traversal, adaptive jitter buffering, and lossy
networks. None of those apply at L0, L1, or L2-over-LAN, and it brings signalling, ICE, and
codec negotiation. **Deferred until a tier actually requires traversing a hostile network.**
The `TransportPort` abstraction keeps the swap cheap.

### ROS 2 / DDS — reserved seam

For [ADR-0024](ADR-0024-robotics-capability-safety.md), sensor and actuator streams would
plausibly use DDS. The data-plane abstraction is deliberately shaped so an additional
transport is an adapter rather than a redesign. **No commitment made.**

## Consequences

### Positive
- One transport covers STT, TTS, and future video with the same primitives.
- Protobuf schemas are versioned artifacts, so wire-format drift is caught at build time.
- Standard Kubernetes tooling applies without special cases.

### Negative / Costs
- Protobuf toolchain and a codegen step in the build.
- gRPC on Windows adds native dependencies; must be verified early on the host.
- HTTP/2 load balancing in Kubernetes needs correct configuration to avoid pinning all
  streams to one pod.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| WebSockets | Streaming yes; no flow control, no schema, no native cancellation. Would rebuild gRPC badly |
| Raw TCP / UDP | Every property above becomes ours to implement |
| WebRTC now | Correct eventually, heavy now. Signalling and ICE for a loopback connection |
| HTTP chunked streaming | Unidirectional; no backpressure |
| MCP with base64 audio | The failure mode ADR-0006 exists to prevent |

## Verification

Gate **G6b**: streaming partial transcripts flow with correct sequencing and backpressure.
Gate **G6d**: a saturated data plane does not delay control-plane dispatch.
Gate **G7**: gRPC works over mTLS through Kubernetes ingress without stream pinning.
