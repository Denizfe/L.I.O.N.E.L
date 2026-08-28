# ADR-0036: The Memory Service's vector client and embedding runtime

| | |
|---|---|
| Status | **Proposed** — awaiting Efe. `Architecture_Freeze.md` §4 and §5 step 4 |
| Date | 2026-08-28 |
| Phase | 2 |
| Related | [ADR-0010](ADR-0010-memory-service.md), [ADR-0013](ADR-0013-artifact-pinning.md), [ADR-0007](ADR-0007-degradation-ladder.md), [ADR-0004](ADR-0004-qdrant-in-docker.md) |

## Context

**Qdrant is not the decision here.** [ADR-0004](ADR-0004-qdrant-in-docker.md) chose it,
[ADR-0010](ADR-0010-memory-service.md) superseded that framing and demoted it to one adapter
behind a `VectorBackend` port, and [ADR-0013](ADR-0013-artifact-pinning.md) pins the image by
digest in `artifacts.lock.yaml`. The embedding model is pinned too:
`sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions, Apache-2.0. All of that is in
force and none of it needs re-deciding.

What G2 needs, and does not have, is the **Python** side. `pyproject.toml`'s own header
says so:

> MASTER_PLAN_v2 names technologies (Qdrant, Kokoro, Piper, faster-whisper, openWakeWord,
> Ollama) whose PYTHON CLIENTS are not yet chosen. Those arrive with the phase that builds
> against them — G2 for memory, G6 for the sensory stack — each with its own ADR.

This is that ADR for G2.

### One of the two has already been chosen, by nobody

`artifacts.lock.yaml`'s `embedding` entry is the only artifact in the lock whose `sha256` is
`null`. It justifies that with a Tier-A verification method:

> Pinned by model id + dimension, asserted at Memory Service startup. Fetched and
> cached by fastembed rather than downloaded by us, so there is no single file for
> us to hash — the pin is the identifier plus a dimension assertion that fails
> loudly on substitution.

**`fastembed` appears exactly once in this repository: in that sentence.** No ADR chose it.
`pyproject.toml` does not declare it. `uv.lock` does not contain it. The verification story
for the one pinned artifact that cannot be hashed rests on a library that is not part of the
system, and has done since 2026-08-02.

Nothing broke, because nothing runs yet. But the shape is the one the G1 sign-off audit spent
a week naming — **a statement about the system that nothing checks** — and this is its first
appearance inside `artifacts.lock.yaml`, which is in the architecture checksum set. Neither
`artifacts`, `licenses` nor `dependencies` looks at a prose `method:` field; there is no rule
that a verification method may only name software the repository actually has.

So this ADR has two jobs: choose the client, and turn an assumption someone made in passing
into a decision that was made.

## Decision

**`qdrant-client` for the `VectorBackend` adapter, and `fastembed` for the embedding
runtime. Both declared directly in `pyproject.toml`, each naming this ADR.**

1. **`qdrant-client`** (Apache-2.0, current 1.19.0). The official client, and the only one
   that tracks Qdrant's filtering, payload and collection semantics as they move. A hand-
   rolled `httpx` layer would re-implement exactly the part where a wrong answer looks like
   a right one — a filter that silently matches nothing returns an empty result set, which
   is indistinguishable from "no such memory".
2. **`fastembed`** (Apache-2.0, current 0.8.0) for embedding, **not `sentence-transformers`**.
   It runs the model under ONNX Runtime; `sentence-transformers` pulls PyTorch. For one
   384-dimension MiniLM, a multi-gigabyte torch install on the host runtime
   ([ADR-0002](ADR-0002-project-root-path.md)) is disproportionate, and it is the kind of
   weight that quietly makes an offline-first assistant something you only run on the
   machine where you set it up.
3. **Both are declared directly, not through the `qdrant-client[fastembed]` extra.** The
   extra installs the same two packages and hides one of them from review: `pyproject.toml`
   is where `DEP-001` reads version bounds and where `forbid_packages` is enforced, and a
   dependency that only appears as somebody else's extra is a dependency nobody diffed.
4. **`onnxruntime` arrives transitively through `fastembed` and is not declared here.** It is
   named because G6 needs it too — openWakeWord is ONNX by
   [ADR-0023](ADR-0023-turkish-locale-correctness.md)'s constraint — and **two ADRs must not pin it
   independently.** Whichever phase first needs a direct bound declares it; this one does
   not.
5. **The dimension assertion becomes executable.** `artifacts.lock.yaml` says the pin *is*
   "the identifier plus a dimension assertion that fails loudly on substitution". At G2 the
   Memory Service asserts `len(vector) == 384` against the lock at startup and refuses to
   start otherwise. A pin whose enforcement is a sentence is not a pin.

**Version bounds are not written in this document.** They are whatever `uv add` resolves on
acceptance, recorded in `uv.lock` and bounded in `pyproject.toml` per `DEP-001`. A number
typed here from memory would be the seventh instance of the thing described in Context, in
the ADR written about it.

## Consequences

**What gets better.** The lock file's Tier-A claim for its only unhashable artifact becomes
true. `VectorBackend` gets an implementation without callers learning what is behind it,
which is the whole point of ADR-0010's port.

**What this costs.**

- **A cold embedding cache needs the network, and L0 forbids counting on it.**
  `fastembed` fetches the model on first use and caches it outside the repository. That is
  fine on a primed host and a hard failure on a fresh one with no connection — and
  [ADR-0007](ADR-0007-degradation-ladder.md)'s guarantee is about the ordinary path working
  with the cable pulled. The mitigation is that priming is an install step and the failure is
  a named error at startup rather than an empty result set at recall time. **A memory service
  that silently returns nothing is worse than one that refuses to start**, and this is the
  choice between those two.
- **`onnxruntime` is a shared seam with G6, pinned by neither yet.** Recorded here so the
  second phase to need it finds this paragraph rather than adding a competing bound.
- **The embedding model becomes load-bearing in a new way.** ADR-0010 already gives it a
  migration path; this makes the substitution detectable at startup rather than at the point
  where retrieval has quietly degraded. The warning in `artifacts.lock.yaml` — *"changing
  this invalidates every stored vector"* — stops being advice.

**What is deliberately not decided here.** Whether Qdrant runs under `docker compose` or
under `ProcessSupervisor` ([ADR-0014](ADR-0014-process-supervisor.md)); the hybrid-ranking
weights; whether a reranker exists at all. Each is a G2 design question that wants the
service in front of it, and deciding them now would be deciding them without the thing that
needs them.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| **`sentence-transformers` for embedding** | Pulls PyTorch for a 384-dimension MiniLM. On the Windows host runtime that is gigabytes and a CUDA-or-not decision, to run a model ONNX Runtime executes in a fraction of the footprint. It would also be a second inference runtime alongside the ONNX one G6 already needs |
| **Raw `httpx` against Qdrant's REST API** | `httpx` is already a dependency, so this looks like the smaller change. It is not: it moves collection, filter and payload semantics into this repository, where they drift against the pinned server version silently. A filter that matches nothing and a query with no results are the same HTTP response |
| **`mcp-server-qdrant`, the official MCP server** | This is precisely ADR-0004's framing, and ADR-0010 superseded it: it puts `qdrant-store` / `qdrant-find` on the capability surface, which ADR-0010 removed by name and G2's DoD checks for. Adopting it would re-open a decision that is in force |
| **An embedded / in-process vector store** | ADR-0004's "Docker over embedded" carried forward unchanged through ADR-0010 — the store must survive host process death and move to a cluster with a URL change |
| **`qdrant-client[fastembed]`** | Installs the same two packages while declaring one. `DEP-001` reads bounds from `pyproject.toml`, and a dependency that appears only inside another package's extra is one nobody reviewed |
| **Defer the whole question and write the adapter against a stub** | The stub is already there — G1 shipped the coordinators as shells that raise `NotYetImplemented` rather than returning something plausible. Deferring again would mean building G2's ranking and dedup against a fake vector store, and discovering the client's semantics after the policy that depends on them |

## Verification

**Withheld until this ADR is Accepted.** Neither package is in `pyproject.toml` while this is
`Proposed`, and `uv.lock` is unchanged. `Architecture_Freeze.md` §4 requires an ADR *and*
Efe's approval before a new dependency exists, and running `uv add` alongside the proposal
would make the approval ceremonial. ADR-0029, ADR-0032, ADR-0033, ADR-0034 and ADR-0035 each
practised this withholding; this is the sixth.

The version numbers in the Decision are what PyPI reported on 2026-08-28, recorded so the
proposal names real software. They are not pins.

On acceptance:

| | |
|---|---|
| `pyproject.toml` | `qdrant-client` and `fastembed`, each with a bound and an `# ADR-0036` comment, per that file's own rule |
| `uv.lock` | regenerated; `DEP-001` and the `licenses` gate see both, Apache-2.0 either way |
| `src/lionel/memory/` | the `VectorBackend` port and its Qdrant adapter |
| dimension assertion | startup reads `artifacts.lock.yaml` → `models.embedding.dims` and refuses to start on a mismatch, with a test that plants 512 and asserts the refusal |
| offline behaviour | a test that a cold cache with no network produces a **named startup error**, not an empty recall |
| `artifacts.lock.yaml` | unchanged. Its `method:` sentence becomes true rather than aspirational, which is the point |

Gate **G2**, where the Memory Service's DoD runs: `forget(id)` provably removes a memory from
retrieval, near-duplicate ingestion is deduplicated, episodic decay is observed under an
accelerated clock, re-index against a second embedding model completes without data loss, and
`qdrant-store` is absent from the exposed capability surface — plus v1.0's two criteria
carried forward, the `compose down && up` persistence proof and the semantic-recall test that
keyword matching must fail.
