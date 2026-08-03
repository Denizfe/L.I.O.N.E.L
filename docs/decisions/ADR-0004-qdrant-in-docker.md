# ADR-0004: Qdrant in Docker as the memory system

| | |
|---|---|
| Status | **Superseded by [ADR-0010](ADR-0010-memory-service.md)** |
| Date | 2026-08-01, superseded 2026-08-02 |
| Phase | — |

> **This ADR is retained for the historical record and is no longer in force.**
> Read [ADR-0010](ADR-0010-memory-service.md) instead.

## Original context

L.I.O.N.E.L needs persistent semantic recall that survives process death and reboot.

## Original decision

Run Qdrant as a Docker container with a named volume, reached via the official
`mcp-server-qdrant` MCP server. Treat this as the memory system.

## Why it was superseded

The operational choices were right; the **architectural framing was wrong.** Qdrant is a
vector store — it performs similarity search. A memory system additionally requires
ingestion policy, deduplication, consolidation, decay, hybrid retrieval ranking,
provenance, and a real forget path. None of those belong in a vector database, and by
exposing `qdrant-store` / `qdrant-find` directly as the capability surface, this ADR made
every caller a de-facto memory-policy author.

[ADR-0010](ADR-0010-memory-service.md) puts a Memory Service in front and demotes Qdrant to
one adapter behind a `VectorBackend` port.

## What carried forward unchanged

These operational decisions were correct and are preserved inside the new backend adapter:

- **Docker over embedded**, so the store survives host process restarts and can later move
  to a cluster with a URL change.
- **Named volume over bind mount** — avoids MSYS path mangling entirely and gives better
  I/O than a bind mount onto NTFS under the WSL2 backend.
- **Loopback-only port binding** (`127.0.0.1:6333`), not exposed to the LAN.
- **Pinned embedding model**, with the explicit note that changing it invalidates every
  stored vector and requires a full re-index. Now enforced by
  [ADR-0013](ADR-0013-artifact-pinning.md) and given a migration path by ADR-0010.
- **Two-collection split** (durable vs. episodic) on the grounds that retention policy
  differs by memory kind. Now the Memory Service's internal schema.
