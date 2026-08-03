# ADR-0010: Memory Service with a pluggable vector backend

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 (design), 2 (build) |
| Supersedes | [ADR-0004](ADR-0004-qdrant-in-docker.md) |

## Context

[ADR-0004](ADR-0004-qdrant-in-docker.md) treated Qdrant as the memory system and exposed
`qdrant-store` / `qdrant-find` directly as capabilities. A vector store does one thing:
similarity search over embeddings. A *memory system* needs considerably more, and if the
store is the interface, every caller becomes an ad-hoc memory-policy author.

Concretely, ADR-0004 had no answer for: what is worth storing, what to do about near
duplicates, how episodic memory expires, how to rank beyond raw cosine similarity, where a
memory came from and how much to trust it, and — most practically — **how to forget
something that turned out to be wrong.**

## Decision

A **Memory Service** owns memory policy. Qdrant becomes one adapter behind a
`VectorBackend` port.

| Concern | Responsibility |
|---|---|
| **Ingestion policy** | Salience scoring. Not "store everything" |
| **Deduplication** | Near-duplicate detection before write |
| **Consolidation** | Periodic episodic → durable summarization |
| **Decay / TTL** | Episodic memory expires; durable memory does not |
| **Retrieval ranking** | Hybrid: vector similarity + recency + importance + provenance |
| **Provenance** | Every memory records source and confidence |
| **Redaction** | A real `forget(id)`. "No, that's wrong" must be actionable |
| **Re-index** | Embedding-model migration without data loss |

**Ports:** `VectorBackend` (Qdrant now; pgvector or managed later) and a reserved
`EntityBackend` seam for future relational/graph entity memory.

**`qdrant-store` and `qdrant-find` are removed from the exposed capability surface.**
Callers use the Memory Service's MCP interface only.

The two-collection split from ADR-0004 (durable vs. episodic) is preserved as the service's
internal schema — it was the right instinct in the wrong place.

## Consequences

### Positive
- Memory quality stays governable as volume grows.
- Forgetting is possible, which matters both practically and for anything privacy-adjacent.
- Backends are swappable without touching callers; adding entity memory is additive.
- Embedding-model changes have a migration path instead of being a silent data loss event.

### Negative / Costs
- A service to build and maintain rather than a container to run. Phase 2 grows.
- Ranking and salience heuristics need tuning, and tuning needs evaluation
  ([ADR-0021](ADR-0021-eval-harness-gates.md)).

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Keep ADR-0004; add policy in callers | Policy duplicated per caller, drifts immediately, and there is still no forget path |
| Thin wrapper over Qdrant only | Solves naming, not the missing capabilities |
| Full knowledge graph now | Large investment before we know retrieval quality is the bottleneck. The `EntityBackend` seam keeps the door open |

## Verification

Gate **G2**. `forget(id)` provably removes a memory from retrieval; near-duplicate
ingestion is deduplicated; episodic decay is observed under an accelerated clock; re-index
against a second embedding model completes without loss; **`qdrant-store` is absent from
the capability surface**. v1.0's persistence and semantic-recall tests are retained.
