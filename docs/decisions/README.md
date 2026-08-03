# Architecture Decision Records

Per **ADR-0016**, these files replace ephemeral `<thought>` reasoning as the project's
durable decision artifact. They are diffable, greppable, citable in review, and indexed
into the Memory Service on merge so `memory.recall` surfaces them months later.

## Rules

1. **Any decision that constrains future work gets an ADR.** Smaller calls get a Decision
   Summary in the response instead.
2. **Query before you decide.** Before proposing a change to a module, search existing ADRs
   (and, once Phase 2 lands, the Memory Service). Settled decisions are not relitigated silently.
3. **ADRs are immutable once Accepted.** To change one, write a new ADR that supersedes it.
   Never edit the original except to update its `Status` line and add the superseding link.
4. **Every ADR names its verification.** A decision with no way to check it is a preference.

## Statuses

| Status | Meaning |
|---|---|
| `Accepted` | In force |
| `Provisional` | Direction agreed, details deferred to a named gate |
| `Superseded by ADR-NNNN` | Replaced. Kept for the historical record |
| `Proposed` | Drafted, not yet approved by Efe |

## Index

| ADR | Title | Status | Phase |
|---|---|---|---|
| [0001](ADR-0001-swappable-brain-provider.md) | Swappable BrainProvider | Accepted | 0 |
| [0002](ADR-0002-project-root-path.md) | Project root path | Accepted | 0 |
| [0003](ADR-0003-mcp-first-capability-model.md) | MCP-first capability model | Accepted | 0 |
| [0004](ADR-0004-qdrant-in-docker.md) | Qdrant in Docker as the memory system | Superseded by 0010 | — |
| [0005](ADR-0005-dual-runtime.md) | Dual runtime: Host + Cluster | Accepted | 0 |
| [0006](ADR-0006-control-data-plane-separation.md) | Control plane / data plane separation | Accepted | 0 |
| [0007](ADR-0007-degradation-ladder.md) | **Degradation Ladder L0–L3** | Accepted | 0 |
| [0008](ADR-0008-coordinator-decomposition.md) | Coordinator decomposition; no god loop | Accepted | 0 |
| [0009](ADR-0009-extended-brain-provider-contract.md) | Extended BrainProvider contract | Accepted | 0 |
| [0010](ADR-0010-memory-service.md) | Memory Service with pluggable vector backend | Accepted | 0 |
| [0011](ADR-0011-capability-tools-no-shell.md) | Capability tools; shell execution abolished | Accepted | 0 |
| [0012](ADR-0012-policy-engine.md) | Policy Engine, default-deny | Accepted | 0 |
| [0013](ADR-0013-artifact-pinning.md) | Artifact pinning and supply chain | Accepted | 0 |
| [0014](ADR-0014-process-supervisor.md) | ProcessSupervisor on Windows Job Objects | Accepted | 1 |
| [0015](ADR-0015-secret-resolver.md) | Layered config and SecretResolver URIs | Accepted | 0 |
| [0016](ADR-0016-adr-driven-decisions.md) | ADRs replace `<thought>` | Accepted | 0 |
| [0017](ADR-0017-dual-tts.md) | Dual TTS: Kokoro EN + Piper TR | Accepted | 6c |
| [0018](ADR-0018-multilingual-stt.md) | Multilingual STT mandatory | Accepted | 6b |
| [0019](ADR-0019-opentelemetry.md) | OpenTelemetry as observability substrate | Accepted | 5 |
| [0020](ADR-0020-kubernetes-cloud-portable.md) | Kubernetes-native, cloud-portable | Accepted | 7 |
| [0021](ADR-0021-eval-harness-gates.md) | Eval harness gates model/prompt changes | Accepted | 8 |
| [0022](ADR-0022-zero-trust-runtimes.md) | Zero-trust between runtimes; mTLS at L2+ | Accepted | 7 |
| [0023](ADR-0023-turkish-locale-correctness.md) | Turkish locale correctness (İ/ı) | Accepted | 6c |
| [0024](ADR-0024-robotics-capability-safety.md) | Robotics capability and safety model | Provisional | 10 |
| [0025](ADR-0025-cancellation-backpressure.md) | Cancellation and backpressure | Accepted | 0 |
| [0026](ADR-0026-side-effect-classification.md) | Side-effect classification on tools | Accepted | 0 |
| [0027](ADR-0027-testing-strategy.md) | Five-layer testing strategy | Accepted | 0 |
| [0028](ADR-0028-data-plane-transport.md) | Data-plane transport selection | Accepted | 6 |
