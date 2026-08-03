# Artifact Verification Report

| | |
|---|---|
| Project | L.I.O.N.E.L |
| Scope | ADR-0013 artifact reproducibility |
| Lockfile | `artifacts.lock.yaml` (schema v3, authoritative) |
| Retrieval date | **2026-08-02** |
| Result | **12 of 13 artifacts reproducible · 1 UNRESOLVED (temporary)** |
| Gate | `bash scripts/verify_artifacts.sh` — **currently FAILS by design** |
| G0 | **BLOCKED** until unresolved reaches 0 |

---

## 1. Executive summary

Twelve of thirteen external artifacts now carry a verifiable pin with documented provenance,
a source URL, a version, a verification method, and a retrieval date. **No hash in this
project was invented, estimated, or copied from a similar-looking file.**

The one remaining artifact — the `ghcr.io/github/github-mcp-server` image digest — is
blocked by a **tooling limitation in this session, not by anything about the artifact**. It
is resolvable in one command on any machine with Docker. Four reproducible alternatives are
documented in §5.

The previous pass resolved 7 of 12. This pass resolved 5 more by finding sources that
publish digests, rather than by lowering the standard.

### What changed, and why it is not a compromise

Three artifacts were previously unpinnable because their upstreams publish no digest. The
fix was **not** to accept a weaker check — it was to **change where we fetch from**, to a
source that does publish one. That is exactly the sourcing rule the ADR-0013 amendment
already required. The pin is now honest because the thing we pin is the thing we fetch.

---

## 2. The central finding: a hash is not a hash

A lockfile that records `sha256: <64 hex>` for every artifact looks uniformly rigorous and
is not. Where a hash came from determines what it actually proves, and flattening that
distinction is how a lockfile grants false confidence — which is the specific failure
ADR-0013 exists to prevent.

Every artifact therefore declares a **verification tier**:

| Tier | Meaning | What it proves | Count |
|---|---|---|---|
| **A** | Primary upstream publishes the digest | The file is what its producers say it is | **7** |
| **B** | Third-party mirror + byte length matches upstream **exactly** | Strong evidence of identity. Not proof — two files can share a length | **2** |
| **C** | Two or more **unrelated** mirrors publish byte-identical digests | Strong. Independent convergence is hard to fake | **2** |
| **D** | Single mirror, no corroboration, no upstream size to check | Reproducibility **from that source only** | **1** |
| **E** | Unresolved. No hash, and never a placeholder | Nothing — and it says so | **1** |

**Tier D is the honest weak point of this lockfile.** It is one artifact, it is documented
below, and §6 explains why the risk is bounded and self-liquidating.

---

## 3. Resolved artifacts

### 3.1 Tier A — primary-published (7)

| Artifact | Version | Pin | Method |
|---|---|---|---|
| `whisper_large_v3_turbo` | large-v3-turbo | `1fc70f77…bc69` | HF API tree; Git-LFS `oid` **is** the content SHA-256 |
| `whisper_medium` | medium | `6c14d5ad…6208` | Same |
| `piper_tr_dfki` | tr_TR-dfki-medium | `2844717f…a8fb` | Same |
| `piper_tr_dfki_config` | tr_TR-dfki-medium | `ea4036df…` (SHA-1) | Non-LFS file; HF publishes a git blob SHA-1 |
| `embedding` | all-MiniLM-L6-v2 | model id + `dims=384` | Fetched and cached by fastembed; pinned by identifier with a startup assertion |
| `qdrant` | v1.18.3 | `sha256:0bd98fa7…5286` | Docker Hub registry manifest — content-addressed by construction |
| `whisper_cpp` | v1.9.1 | commit `f049fff9…4916` | GitHub tags API; a commit SHA pins the whole tree |

Two of these deserve a note rather than silent acceptance:

**`piper_tr_dfki_config` is SHA-1, not SHA-256.** The file is not Git-LFS, so a blob SHA-1
is the strongest thing Hugging Face publishes for it. SHA-1 is collision-vulnerable in the
adversarial case. Accepted because the file is a 5 KB JSON config that is fully
inspectable, and a useful collision would also have to be valid Piper configuration. It is
recorded as SHA-1 rather than described as "verified", because upgrading a claim by
assertion is the thing this report exists to avoid.

**`embedding` has no file hash at all.** fastembed fetches and caches it; there is no single
file we download. The pin is the model identifier plus a dimension assertion that fails
loudly at Memory Service startup if the model is substituted. Different mechanism, real
guarantee — and the gate has an explicit branch for it rather than a silent exemption.

### 3.2 Tier B — mirror, size-matched to upstream (2)

Both Kokoro artifacts. The GitHub release assets return `digest: null` from the API — they
predate the field — so the primary source is unpinnable.

`huggingface.co/fastrtc/kokoro-onnx` mirrors both files and publishes LFS SHA-256s. The
identity check that makes this usable:

| File | Mirror bytes | GitHub asset bytes | Match |
|---|---|---|---|
| `kokoro-v1.0.onnx` | 325,532,387 | 325,532,387 | **exact** |
| `voices-v1.0.bin` | 28,214,398 | 28,214,398 | **exact** |

Byte-length equality is **necessary but not sufficient** for identity — which is precisely
why the mirror is pinned as the **source of record** rather than being used to vouch for the
GitHub asset. We fetch what we hashed. The distinction matters and is recorded in the
lockfile as `source_change`.

`fastrtc` is a reputable Hugging Face organisation whose library depends on exactly these
two files, which is a plausible reason for the mirror to exist and to be maintained.

> **The substitution that was rejected.** `onnx-community/Kokoro-82M-v1.0-ONNX` publishes a
> clean LFS SHA-256 and is **325,532,232 bytes — 155 fewer**. It is a different file.
> Pasting its hash in would have produced a lockfile that verifies perfectly against a model
> nobody runs. This is recorded in the lockfile as `rejected_substitute` so the trade is not
> quietly made later by someone in a hurry.

### 3.3 Tier C — independently corroborated (2)

The openWakeWord preprocessors. openWakeWord v0.6.0 **removed all model assets** from its
GitHub releases (PR #50, "Remove model files"); models are fetched at runtime by
`download_models()`, so there is nothing on the releases API to hash.

Two unrelated Hugging Face uploaders publish these files, and they agree byte-for-byte:

| File | SHA-256 | Bytes | Sources |
|---|---|---|---|
| `melspectrogram.onnx` | `ba2b0e0f…6176f` | 1,087,958 | `littlebearlabs/openwakeword-features` **and** `harvestsu/openwakeword-onnx` |
| `embedding_model.onnx` | `70d16429…75c1f` | 1,326,578 | Both, identical |

Independent uploaders converging on identical digests is meaningfully stronger than one
mirror's word. It is not a signature from the author, and the tier says so.

**Worth stating plainly:** without these two files, *no* wake-word model runs. They are easy
to overlook because they are not "the wake word", and they are pinned with the same rigour.

### 3.4 Tier D — single uncorroborated mirror (1)

`wake_bootstrap` — `hey_jarvis_v0.1.onnx`, `94a13cfe…d2cb`, 1,271,370 bytes, from
`harvestsu/openwakeword-onnx`.

**This is the weakest entry in the lockfile and should be read as such.** One third-party
mirror, no upstream byte size to check against, and no second mirror carrying this
particular file. It proves reproducibility *from that source*; it does **not** prove the
file matches what `download_models()` would fetch.

Why that is acceptable here, and only here:

1. The mirror is pinned as the source of record, so the build is reproducible.
2. **The artifact is self-liquidating.** ADR-0023 replaces it with a project-trained
   "Hey Lionel" model at Phase 6a. It is scaffolding for proving the audio pipeline, and it
   leaves the tree before Phase 6 ends — taking both the tier-D weakness and the licence
   ambiguity below with it.
3. It is not on the L0 correctness path in any lasting way.

---

## 4. Licence finding — openWakeWord models

**Flagging this because it is the kind of thing that surfaces at the worst moment.**

| Source | Licence claimed |
|---|---|
| openWakeWord library (GitHub) | Apache-2.0 |
| **`huggingface.co/davidscripka/openwakeword`** — the author's own model repo | **cc-by-nc-sa-4.0 (NON-COMMERCIAL)** |
| `littlebearlabs/openwakeword-features` | Apache-2.0 |
| `harvestsu/openwakeword-onnx` | none declared |

The library is permissively licensed; **the pretrained models may not be.** The author's own
model repository is tagged non-commercial, and the mirrors disagree with it and with each
other.

**Impact:** none for personal use. It would matter if L.I.O.N.E.L is ever distributed or
used commercially.

**Mitigation, already in the plan:** the custom "Hey Lionel" model (ADR-0023) is
project-trained and project-owned. Once Phase 6a lands, no third-party wake model ships.
The preprocessors remain, and those are Apache-2.0 in the source we pin.

**Action:** resolve the licence question before any non-personal use. Recorded in the
lockfile as `license_risk` on `wake_bootstrap`.

---

## 5. The unresolved artifact

### `ghcr.io/github/github-mcp-server` — image digest

**Status:** UNRESOLVED · Tier E · **no hash recorded, and no placeholder**

#### Exactly why

GHCR requires an `Authorization: Bearer <token>` header on the manifest endpoint.

An anonymous token **is** obtainable — confirmed on 2026-08-02:

```
GET https://ghcr.io/token?scope=repository:github/github-mcp-server:pull&service=ghcr.io
  → {"token":"djE6Z2l0aHViL2dpdGh1Yi1tY3Atc2VydmVyOjE3ODU2NzEzNTk1MzI1MzA3Mzk="}
```

The fetch tooling available in this session **cannot set request headers**, and GHCR rejects
the token passed as a query parameter (verified — returns empty). Docker Hub carries no
`mcp/github-mcp-server` mirror, and the GitHub Packages API for org-owned container
versions requires authentication.

So the blocker is: *the token exchange is available, the header to use it with is not.*

#### Temporary or permanent?

**TEMPORARY.** Unambiguously.

Nothing about the artifact, the registry, or the upstream project is at fault. GHCR behaves
exactly as the OCI distribution spec requires. Any machine with `docker` or `crane` performs
the token exchange automatically and returns the digest immediately. This is a property of
the environment this session runs in, and it disappears the moment the command runs
elsewhere.

Contrast with a **permanent** blocker, which would look like: the upstream never publishes
digests and the artifact is only obtainable through a non-deterministic installer. Nothing
in this project is in that category.

#### Reproducible alternatives

| # | Approach | Reproducible | Effort | Notes |
|---|---|---|---|---|
| **1** | `docker buildx imagetools inspect ghcr.io/github/github-mcp-server:<tag>` | ✅ | one command | **Recommended.** Docker performs the token exchange. Choose an explicit version tag — never `:latest`, which is mutable and defeats pinning |
| 2 | `crane digest ghcr.io/github/github-mcp-server:<tag>` | ✅ | one command | go-containerregistry CLI; no Docker daemon needed, so it works in CI |
| 3 | Build from source, pin the **git commit** instead of an image digest | ✅ | moderate — needs Go | Trades a registry dependency for a build dependency. Yields a **tier-A** `vcs-commit` pin, the same mechanism already used for whisper.cpp |
| 4 | Drop the GitHub capability from the L0 configuration | ✅ | zero — already true | `requires_network: true`, so ADR-0007 already excludes it at tier L0 |

#### Why this does not block L0

Alternative 4 is not a dodge, it is the existing architecture. The GitHub capability is
network-dependent and therefore **already excluded from tier L0** by ADR-0007. The offline
conformance gate — the one that carries the project's autonomy guarantee — does not depend
on this image.

**It blocks full G0 sign-off. It does not block L0 conformance.** Those are different
claims and the distinction is deliberate.

---

## 6. Residual risk register

| # | Risk | Severity | Status |
|---|---|---|---|
| R1 | `github_mcp` unpinned | Low | Temporary; 4 reproducible alternatives; not on the L0 path |
| R2 | `wake_bootstrap` tier D — one uncorroborated mirror | Low | Self-liquidating: replaced by the project-trained model at Phase 6a |
| R3 | openWakeWord model licence ambiguity (NC vs Apache) | Medium *if distributed*, none for personal use | Resolve before non-personal use; mitigated by ADR-0023 |
| R4 | Kokoro tier B — size match is evidence, not proof | Low | Mirror pinned as source of record, so we fetch what we hashed |
| R5 | `piper_tr_dfki_config` pinned by SHA-1 | Low | 5 KB inspectable JSON; local SHA-256 recorded alongside on first fetch |
| R6 | Piper voice licence — "verify per MODEL_CARD" | Medium | Unresolved by design; MODEL_CARD must be read before release |
| R7 | Embedding model is a hidden schema | High **if changed** | Pinned; ADR-0010 defines the re-index migration path |

---

## 7. Verification you can run

```bash
# The gate. Fails closed. Currently exits 1 by design.
bash scripts/verify_artifacts.sh
```

It asserts, per artifact: required fields present · hash well-formed (64 hex, or 40 for
SHA-1, or an explicit non-file pin mechanism) · `verification.method` substantial enough to
audit · retrieval date present · every UNRESOLVED entry classified TEMPORARY or PERMANENT
with at least one **reproducible** alternative · `[meta]` counts match reality · no
placeholder pins · no `.en` whisper model (ADR-0018).

To confirm any hash independently after downloading:

```bash
sha256sum models/whisper/ggml-large-v3-turbo.bin
git hash-object models/piper/tr_TR-dfki-medium.onnx.json
docker buildx imagetools inspect qdrant/qdrant:v1.18.3
git -C vendor/whisper.cpp rev-parse HEAD
```

Every artifact carries its own `confirm_locally` command in the lockfile.

---

## 8. Close-out

**To reach zero unresolved,** run alternative 1 or 2 from §5, then set `images.github_mcp`
to `status: RESOLVED` with `verification.tier: A`, `provenance: registry-manifest`, the
retrieval date, and an explicit version tag. Update `meta.resolved` to 13 and
`meta.unresolved` to 0. Re-run the gate.

**Then, and only then, G0's artifact criterion is met.**

Two things that must not happen in the meantime:

1. **Do not paste a plausible-looking digest to make the gate green.** A fabricated hash is
   strictly worse than an absent one, because it looks verified and will be trusted.
2. **Do not pin `:latest`.** A mutable tag pinned by name is not a pin.

---

*Generated 2026-08-02 from `artifacts.lock.yaml` schema v3. Regenerate rather than
hand-edit — a stale verification report is worse than none, because it gets believed.*
