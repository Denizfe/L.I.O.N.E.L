# ADR-0013: Artifact pinning and supply chain

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 |
| Related | [ADR-0010](ADR-0010-memory-service.md), [ADR-0021](ADR-0021-eval-harness-gates.md) |

## Context

MASTER_PLAN v1.0 used `qdrant/qdrant:latest`, an untagged GitHub MCP image, models fetched
by URL with no checksum, and left `<pinned-tag>` as a literal placeholder for whisper.cpp.
A rebuild three months later produces a different system, and "it worked last week" becomes
unanswerable.

For this project specifically there is a sharper failure: **the embedding model is a hidden
schema.** Changing it silently invalidates every stored vector — retrieval degrades rather
than errors, which is the worst way for something to break.

## Decision

Everything external carries an immutable pin. This imposes **two distinct duties**, at
different times:

| | Duty | Deadline |
|---|---|---|
| **RECORD** | An immutable pin (SHA-256, OCI digest, or commit SHA) exists in the lockfile, with its provenance | **By G0.** Every artifact, whether or not it is used yet |
| **VERIFY** | Every fetched artifact is checked against that recorded pin | **Before every use**, at every gate, forever |

The two are frequently conflated and are not the same act. *Recording* is discovering and
writing down what an artifact's digest is. *Verifying* is checking that what arrived
matches. An artifact can be recorded long before it is ever fetched, and must be verified
every single time it is.

| Artifact | Pinning requirement |
|---|---|
| Container images | Tag **and** digest: `qdrant/qdrant:v1.x.y@sha256:…` |
| whisper.cpp | Submodule pinned to release tag **and** commit SHA |
| Models (whisper, Kokoro, Piper, wake word) | `artifacts.lock.toml`: URL, SHA-256, size, license, and the ADR that chose it |
| Python | `uv.lock` with `--require-hashes` |
| Node | `package-lock.json`, `npm ci` (never `npm install` in CI) |
| Embedding model | Pinned; changing it requires a documented full re-index via ADR-0010's migration path |

**The download script fails closed.** A checksum mismatch aborts. It does not warn and
continue.

`artifacts.lock.toml` records **license** per artifact, so a license question is a lookup
rather than an archaeology exercise.

## Consequences

### Positive
- Builds are reproducible; regressions are bisectable.
- A supply-chain substitution is caught by checksum rather than discovered in behavior.
- The embedding model cannot change accidentally.
- License posture is known at all times.

### Negative / Costs
- Updates become deliberate: bump the pin, verify the checksum, run evals
  ([ADR-0021](ADR-0021-eval-harness-gates.md)). Slower than `:latest`, which is the point.
- Digest pinning makes upgrades explicit work. Accepted.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Tags without digests | Tags are mutable. `v1.2.3` can be re-pushed |
| `:latest` (v1.0) | Non-reproducible by construction |
| Checksums recorded but unverified | Documentation, not a control |
| Vendoring models into git | Hundreds of MB to GB in version control; the lockfile achieves the same guarantee |

## Erratum — 2026-08-02: the Decision understated the enforced rule

**Nature of change: ERRATUM, not amendment.** No policy changed. The text now states the
rule that was already in force and already enforced by the gate. Recorded here in full so
the original wording survives.

### What the Decision originally said

> "Everything external is pinned, checksummed, and verified before use."

### The defect

Audit finding **AUD-M08** alleged this contradicted the Verification section, which blocks
G0 on any `UNRESOLVED` entry. On close reading it does not:

- "Pinned by G0" satisfies "pinned before use". **The G0 clause is strictly stronger and
  therefore implies the Decision.** No contradiction exists, and the ADR *can* be complied
  with as written — by meeting the stricter clause.
- The Verification line *"Gate G1: the **pinned** GitHub MCP image digest is verified **at
  pull**"* was read as assigning a recording deadline to G1. It does not. "Pinned"
  presupposes the record exists; "at pull" names a runtime check. That clause was always
  about verifying, never about when to record.

**AUD-M08 was therefore overstated and is downgraded Major → Minor.**

The real defect is milder and still worth correcting: a Decision section is read as *the*
statement of the rule, and "before use" invites the conclusion that an artifact first used
at G1 may remain unrecorded until then. It may not. **The Decision understated the enforced
policy**, and an ADR whose Decision does not describe what is enforced fails at its one job.

### The correction

The Decision now separates the two duties it always contained — **RECORD by G0** and
**VERIFY before every use** — and the Verification section labels each clause with the duty
it checks.

### Why in place rather than a superseding ADR

ADR-0016 holds that ADRs are immutable once Accepted. **Correcting a text so it accurately
states a decision already in force is an erratum, not a new decision.** Immutability exists
to prevent decisions being silently revised; it is not meant to freeze an understatement
into permanence, which would preserve the record at the cost of the record being wrong.

Safeguards: the original wording is quoted verbatim above, and no policy changed — the gate
(`ART-000`), `artifacts.lock.yaml` and `ci/policy/policy.yaml` are untouched.

> **Open item, not fixed here:** ADR-0016 has no erratum provision, while practice has now
> diverged from it three times (two Amendments and this Erratum). It should be amended to
> distinguish *superseding decisions* from *errata*. Recorded as a Minor finding.

Full analysis, including the six rejected resolutions: `ADR0013_Contradiction_Resolution.md`.

## Amendment — 2026-08-02: prefer sources that publish digests

Resolving the initial lockfile surfaced a sourcing criterion this ADR did not state.

Of eleven artifacts, six could be pinned from **upstream-published** digests and five
could not:

| Source type | Publishes a digest? | Example |
|---|---|---|
| Hugging Face LFS | **Yes** — the LFS `oid` *is* the file's SHA-256 | whisper, Piper |
| OCI registry | **Yes** — content-addressed by construction | Qdrant |
| Git | **Yes** — commit SHA | whisper.cpp |
| GitHub release asset | **Often not** — older assets return `digest: null` | Kokoro |
| Library-managed download | **No** | openWakeWord |

**New rule, in order of preference when a choice exists:**

1. A source that publishes a content digest.
2. A source that does not, accepted only with a recorded trust-on-first-use hash and an
   explicit `sha256_provenance = "local-tofu"`.

**Never substitute a digest from a different artifact to satisfy the lockfile.** The Kokoro
case is the cautionary one: `onnx-community/Kokoro-82M-v1.0-ONNX` publishes a proper LFS
SHA-256 and is 155 bytes smaller than the GitHub asset. It is a *different file*. Pasting
its hash in would have produced a lockfile that verified cleanly against a model nobody
was running.

**`sha256_provenance` is therefore mandatory on every hash.** A hash read from a host API
and a hash computed from a file you downloaded are different security claims, and a
lockfile that conflates them grants false confidence — the specific failure this ADR
exists to prevent.

## Amendment — 2026-08-02: verification tiers

`sha256_provenance` proved necessary but not sufficient. Resolving the full artifact set
surfaced that hashes differ not just in *how* they were obtained but in *what they prove*,
and a lockfile that records `sha256: <64 hex>` uniformly looks rigorous while hiding that.

Every artifact now declares a **verification tier** in `artifacts.lock.yaml`:

| Tier | Meaning | Proves |
|---|---|---|
| **A** | Primary upstream publishes the digest | The file is what its producers say it is |
| **B** | Third-party mirror + byte length matches upstream exactly | Strong evidence of identity, not proof |
| **C** | Two or more unrelated mirrors publish byte-identical digests | Strong — independent convergence is hard to fake |
| **D** | Single mirror, uncorroborated, no upstream size to check | Reproducibility from that source only |
| **E** | Unresolved. No hash, never a placeholder | Nothing, and says so |

**Rules that follow:**

- A tier-D artifact requires a documented reason it is acceptable, and preferably a plan
  that removes it.
- **Pin the source you actually fetch from.** A hash for a mirror you do not use proves
  nothing. When a mirror provides the only usable digest, the mirror becomes the source of
  record — that is an ADR amendment, not a lockfile edit.
- An UNRESOLVED artifact must classify its blocker **TEMPORARY or PERMANENT** and propose at
  least one **reproducible** alternative. "Blocked" without a route forward is not a status,
  it is a shrug.
- Not every pin is a file hash. `pinned-model-id` (identifier plus a startup dimension
  assertion) is legitimate for artifacts a library fetches and caches on our behalf, and the
  gate branches on it explicitly rather than granting a silent exemption.

## Verification

Each clause is labelled with the duty it checks, so that a clause about *verifying* is never
mistaken for a deadline to *record*.

**[RECORD] — Gate G0.** `artifacts.lock.yaml` **fails closed** on a corrupted checksum, on
any `UNRESOLVED` entry, on any hash lacking a verification tier, method or retrieval date,
on any UNRESOLVED entry without a classified blocker and a reproducible alternative, and on
`[meta]` drift — enforced by `ci/gates/gate_artifacts.py` (`scripts/verify_artifacts.sh`
delegates to it). Current state and residual risks: `Artifact_Verification_Report.md`.

**[VERIFY] — every gate, every fetch.** Any artifact fetched is checked against its
recorded pin before use, and a mismatch aborts. This obligation never expires and is not
satisfied by having recorded the pin.

**[VERIFY] — Gate G1, worked example.** When the GitHub MCP image is pulled, the
*already-recorded* digest is verified against what the registry returns. This is an
illustration of the [VERIFY] duty at a named gate. **It is not a recording deadline** — the
digest must already be present under [RECORD] at G0.
