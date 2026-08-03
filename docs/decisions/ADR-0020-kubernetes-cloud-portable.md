# ADR-0020: Kubernetes-native, cloud-portable deployment

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 7 |
| Scope set by | Efe, 2026-08-02 — "cloud-deployable path" |
| Related | [ADR-0007](ADR-0007-degradation-ladder.md), [ADR-0005](ADR-0005-dual-runtime.md), [ADR-0022](ADR-0022-zero-trust-runtimes.md) |

## Context

MASTER_PLAN v1.0's deployment model was "run the scripts on the box" — no packaging, no
environment separation, no upgrade or rollback path. Efe scoped the target explicitly:
manifests must remain portable to a managed cloud cluster (EKS/GKE), not merely run on
Minikube.

Cloud portability is a **constraint on how we build**, not a deployment we necessarily
perform. It rules out choices that only work locally.

## Decision

Cluster Runtime components deploy as Kubernetes workloads, packaged for portability.

| Element | Choice |
|---|---|
| Images | Multi-arch (amd64 + arm64 — the latter also seeds [ADR-0024](ADR-0024-robotics-capability-safety.md)) |
| Packaging | **Helm chart** — the unit of portability |
| Environments | Kustomize overlays: `minikube` / `staging` / `cloud` |
| Registry | GHCR, images pinned by digest ([ADR-0013](ADR-0013-artifact-pinning.md)) |
| Qdrant | StatefulSet + PVC — no bind mounts, no host paths |
| Secrets | External Secrets Operator ([ADR-0015](ADR-0015-secret-resolver.md)) |
| Network | NetworkPolicy default-deny; Gateway API for ingress |
| Scaling | HPA on inference services |
| Host↔cluster | mTLS ([ADR-0022](ADR-0022-zero-trust-runtimes.md)) |

### The operative portability test

> **The same chart deploys to a cloud cluster with overlay-only changes. No chart edits.**

If a cloud deployment requires editing the chart, the chart was not portable — it was
Minikube-specific with extra steps.

### The non-negotiable constraint

**L0 must still pass with the cluster entirely absent.** Per
[ADR-0007](ADR-0007-degradation-ladder.md) this is a gate at G7, and it is the criterion
that keeps Kubernetes from quietly becoming mandatory.

## Consequences

### Positive
- Real upgrade and rollback; declarative environments.
- Inference scales independently of the host.
- Multi-arch images make the robotics path cheap later.

### Negative / Costs
- Substantial operational surface: Helm, Kustomize, ESO, NetworkPolicy, Gateway API.
- Cloud deployment adds cost and egress considerations not present locally.
- Genuine tension with local-first, which is precisely why ADR-0007 exists and why G7's
  decisive criterion is that L0 still passes.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Docker Compose only | No upgrade/rollback story, no scaling, no cloud path — v1.0's implicit position |
| Minikube-specific manifests | Would require a rewrite the day cloud is wanted; contradicts Efe's stated scope |
| Raw manifests, no Helm | Environment differences become copy-paste divergence |
| Cloud-only, no local cluster | Breaks L0 and L1. Non-starter |

## Verification

Gate **G7**. L1 runs end-to-end on Minikube; L2 runs host-on-Windows + remote cluster over
mTLS with the latency budget re-measured; **the same chart deploys to a cloud cluster with
overlay-only changes**; Qdrant survives pod deletion; NetworkPolicy blocks an unauthorized
pod-to-pod call; rollback verified; **L0 still passes with the cluster absent**.
