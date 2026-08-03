# ADR-0022: Zero trust between runtimes; mTLS at L2+

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 7 |
| Related | [ADR-0005](ADR-0005-dual-runtime.md), [ADR-0007](ADR-0007-degradation-ladder.md), [ADR-0015](ADR-0015-secret-resolver.md) |

## Context

At L0 and L1 the runtime boundary is loopback on one machine, and v1.0's loopback-only port
binding is adequate. At L2 the boundary crosses a network, and the traffic is not incidental:
it carries transcripts of everything spoken near the microphone, memory contents, and tool
invocations with real side effects.

A compromised or spoofed cluster endpoint could read every conversation and return crafted
tool calls to the host. Network-location trust ("it came from inside the LAN") is not a
control.

## Decision

**Neither runtime trusts the other by network location.** Identity is cryptographic.

| Tier | Posture |
|---|---|
| L0 | In-process. No network surface |
| L1 | Loopback only, bound to `127.0.0.1` (v1.0 rule preserved) |
| **L2+** | **mTLS on every host↔cluster connection**, both planes |

- Both sides present certificates; both verify. Server-only TLS is insufficient — the
  cluster must know it is talking to the real host.
- Short-lived certificates with automated rotation; no long-lived shared secrets.
- Per-service identity, not one blanket cluster certificate.
- **NetworkPolicy default-deny** inside the cluster; services reach only declared peers.
- Both control plane (MCP over HTTP) and data plane (gRPC) are covered. Audio is the most
  sensitive traffic in the system and must not be the exception.
- Certificates are resolved through `secret://`
  ([ADR-0015](ADR-0015-secret-resolver.md)), never baked into images.

## Consequences

### Positive
- Conversation content is protected in transit by default, not by network topology.
- A compromised pod cannot pivot freely — NetworkPolicy limits blast radius.
- Certificate rotation is automated, so nothing expires at an inconvenient moment.

### Negative / Costs
- PKI to operate: issuance, rotation, revocation, and a runbook for expiry.
- TLS handshake latency on the data plane; mitigated by connection reuse, measured at G7.
- Local development gains friction. Mitigated by L0/L1 not requiring mTLS at all.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Plain HTTP on a trusted network | "Trusted network" is not a security model. Transcripts in cleartext |
| Server-only TLS | Host verifies cluster; cluster cannot verify host. Half a control |
| Shared bearer token | Long-lived, leakable, no per-service identity, painful rotation |
| VPN instead of mTLS | Protects the tunnel, not service identity. A compromised pod is inside the tunnel |

## Verification

Gate **G7**. mTLS enforced on both planes at L2 with connection reuse measured against the
latency budget; NetworkPolicy blocks a deliberately unauthorized pod-to-pod call; a
certificate rotation drill completes without downtime.
