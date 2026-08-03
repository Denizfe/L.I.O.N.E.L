# ADR-0007: The Degradation Ladder — L0 through L3

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 |
| Significance | **Keystone. Every other decision in this project is downstream of it.** |
| Related | [ADR-0001](ADR-0001-swappable-brain-provider.md), [ADR-0005](ADR-0005-dual-runtime.md), [ADR-0020](ADR-0020-kubernetes-cloud-portable.md) |

## Context

L.I.O.N.E.L has two goals that pull against each other:

1. **Fully local and autonomous** — it must work with no network at all.
2. **Cloud-deployable Kubernetes** — manifests portable to a managed cluster (Efe, 2026-08-02).

These are not incompatible, but they degrade in a predictable and well-documented way.
Nobody ever decides to abandon offline operation. It **erodes**: one service assumes the
network is present, then a second one does, and eighteen months later the offline test has
been skipped for a year and nobody can make it pass again.

MASTER_PLAN v1.0 contained exactly the right test — airplane mode, Ollama provider, full
voice loop — and exactly **zero machinery** to keep it passing. It was a one-time checkbox
in Phase 4's Definition of Done.

## Decision

Four deployment tiers, each independently testable, each with a documented capability delta.

| Tier | Composition | Network | Brain | Purpose |
|---|---|---|---|---|
| **L0** | Everything in-process in the Host Runtime | **None** | Ollama / llama.cpp | The autonomy guarantee |
| **L1** | Host Runtime + Cluster Runtime on Minikube, same machine | Loopback only | Ollama in-cluster | Proves service boundaries without leaving the box |
| **L2** | Host on Windows + Cluster on remote k8s | mTLS ([ADR-0022](ADR-0022-zero-trust-runtimes.md)) | In-cluster or API | Scale-out; the cloud-portable target |
| **L3** | L2 + Claude API as brain | Internet | Claude API | Maximum capability, minimum independence |

### The invariant

> **L0 conformance is a blocking CI gate on every release.**
>
> A change that improves L2 or L3 while breaking L0 is a **rejected change**, not a
> tradeoff to be weighed. The build is red. It does not merge.

This is the entire point of the ADR. Everything else here is mechanism.

### Components that may never leave the Host Runtime

Enumerated in [ADR-0005](ADR-0005-dual-runtime.md): audio I/O, wake word, VAD,
InterruptController, session state, local filesystem capability. Raw audio must not cross
a network boundary before the wake word fires — this is a privacy guarantee enforced by
topology rather than by policy.

### Tier configuration

`config/tiers/l0.toml` … `l3.toml`. A tier selects service placement and transport. It
never selects *different code*.

## Consequences

### Positive
- "Local-first" becomes an **invariant with a test**, not a slogan in a README.
- The capability delta between tiers is explicit and measured, so "what do I lose offline?"
  has a real answer.
- Forces the stateless-service discipline in
  [ADR-0008](ADR-0008-coordinator-decomposition.md) — a service that can run in-process at
  L0 and as a pod at L2 cannot hoard state.

### Negative / Costs
- **Four tiers to test.** This is a real, recurring cost, and it is the price of the
  guarantee. Mitigated by the sensory harness in
  [ADR-0027](ADR-0027-testing-strategy.md), which makes L0 runnable in CI without hardware.
- Some features will be harder because they must work offline. That constraint is the
  product, not an obstacle to it.
- Local-model quality bounds L0's ceiling. Accepted and measured, per
  [ADR-0021](ADR-0021-eval-harness-gates.md).

### Neutral
- L3 is legitimate and useful. The ladder does not disparage it; it just refuses to let it
  become the only rung that works.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| "Local-first" as a design principle with no gate | Precisely the erosion failure this ADR exists to prevent. Principles without tests decay |
| Two tiers (local / cloud) | Hides the interesting middle. L1 is where service boundaries get proven cheaply, before remote networking is in the picture |
| Offline as a fallback mode | Fallback paths are exercised rarely and therefore broken. L0 is the *primary* configuration; the others add capability on top |
| Feature flags per capability | Combinatorial explosion, and no single thing to point CI at |

## Verification

**Every gate, G0 through G9**, carries universal exit criterion **U1: the L0 suite passes.**

Specifically:
- **G0** — the L0 CI gate is wired and reporting. Failing is acceptable at G0; *absent* is not.
- **G6d** — full voice loop, English and Turkish, network disconnected, Ollama provider.
- **G7** — the decisive one: after Kubernetes lands, **L0 still passes with the cluster
  entirely absent.**
