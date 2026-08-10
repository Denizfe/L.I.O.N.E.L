# Artifacts — Final Report

**The last unresolved artifact is pinned. The G0 artifact criterion is met.**

| | |
|---|---|
| Date | 2026-08-03 |
| Artifacts | **13 / 13 RESOLVED · 0 UNRESOLVED** |
| Verification tiers | **A=8 · B=2 · C=2 · D=1** |
| `artifacts` gate | ✅ **PASS — 16 checks** |
| `scripts/verify_artifacts.sh` | ✅ **PASS** |
| Lockfile validation | ✅ **PASS** |
| Full suite | ✅ **17 / 17 gates green** |
| Placeholders in the lockfile | **0** |

---

## 1. What was resolved

`images.github_mcp` — the only artifact that had ever carried `status: UNRESOLVED`.

```
$ docker buildx imagetools inspect ghcr.io/github/github-mcp-server:v1.1.2

Name:      ghcr.io/github/github-mcp-server:v1.1.2
MediaType: application/vnd.oci.image.index.v1+json
Digest:    sha256:30197479d8036c7811892bc07e06f9a05c9ef3cdd79bc59f256d50647f95788c
```

Recorded **verbatim**. Nothing was derived, inferred, or reformatted.

| Field | Value |
|---|---|
| `digest` (OCI image **index**) | `sha256:30197479d8036c7811892bc07e06f9a05c9ef3cdd79bc59f256d50647f95788c` |
| `digest_amd64` | `sha256:a69e2173bf2f28b29686e03456fd228468f87292aadf17e2304e0d2a3fe9a221` |
| `digest_arm64` | `sha256:a915dc384abd24b8e558a72adc9e759dbb4b73590f819c0e6c56b9a326c8c004` |
| `version` | `v1.1.2` |
| `pull_as` | `ghcr.io/github/github-mcp-server@sha256:30197479…788c` |

**The index digest is the pin.** Per-platform digests are recorded for the multi-arch build
in ADR-0020 and the arm64/Jetson path in ADR-0024, but the runtime selects the platform from
the index — so the index is what `pull_as` references.

### Provenance, as specified

```yaml
verification:
  tier: A
  provenance: local-registry-inspect
  method: >-
    `docker buildx imagetools inspect ghcr.io/github/github-mcp-server:v1.1.2` run by
    the operator on the Windows host, 2026-08-03. Docker performed the GHCR bearer-token
    exchange and TLS verification; the returned OCI image index digest was transcribed
    verbatim. This is the OCI MANIFEST DIGEST — content-addressed by construction, so a
    digest reference cannot be re-pointed at different bytes.
  retrieved: "2026-08-03"
  verified_locally: true
  confirm_locally: docker buildx imagetools inspect ghcr.io/github/github-mcp-server:v1.1.2
```

**`local-registry-inspect` is a new provenance value**, added to the artifacts policy rather
than reusing `registry-manifest`. The distinction is real: `registry-manifest` (used for
Qdrant) means a digest read from a *public API response*. This one was obtained by the
operator's own toolchain performing the OCI token exchange and TLS verification against the
registry. Flattening the two would lose exactly the kind of difference the tier model exists
to preserve.

### Bonus finding: the image carries build attestations

The index contains two additional manifests annotated
`vnd.docker.reference.type: attestation-manifest` — one per platform:

| Platform | Attestation manifest |
|---|---|
| linux/amd64 | `sha256:87712651884b0bbc86f9952c83d7d3b1aa4b498aff5761c32830c450cb4e57af` |
| linux/arm64 | `sha256:fb18369a705a90ded70ac6a209265b0b1c38ad824f9dda51632cab65c6ad6146` |

GitHub publishes build provenance alongside the image. **Recorded as evidence, not relied
upon** — the pin remains the index digest. Verifying the attestations would need `cosign`
and is a Phase 9 supply-chain hardening item, not a G0 requirement.

---

## 2. Also closed: AUD-M03

`config/capabilities.registry.json` carried a syntactically invalid image reference:

```
ghcr.io/github/github-mcp-server@sha256:UNRESOLVED-see-artifacts.lock.yaml
```

`docker run` would have rejected it. Replaced with the real index digest. The registry and
the lockfile now agree byte-for-byte — verified below.

---

## 3. Verification — all three requested runs

### 3.1 `artifacts` gate

```
$ bash ci/run_gates.sh artifacts

  note tiers: A=8 · B=2 · C=2 · D=1
  note 1 tier-D artifact(s) — single uncorroborated mirror. See Artifact_Verification_Report.md §3.4.

  PASS  16 checks
```

Tier A rose from 7 to 8. The tier-D note persists and is correct — `wake_bootstrap` is still
a single uncorroborated mirror, self-liquidating at Phase 6a per ADR-0023.

### 3.2 Artifact verification

```
$ bash scripts/verify_artifacts.sh
  PASS  16 checks
```

(Delegates to `gate_artifacts.py` — one source of truth for artifact policy.)

### 3.3 Lockfile validation

| Check | Result |
|---|---|
| YAML parses | ✅ |
| Every RESOLVED artifact has complete metadata | ✅ |
| Digest format `sha256:<64 lowercase hex>` | ✅ |
| `meta` declared 13/0 vs actual 13/0 | ✅ no drift |
| Placeholder strings | ✅ **none** |
| UNRESOLVED entries | ✅ **0** |

### 3.4 Cross-file consistency

| Check | Result |
|---|---|
| Lockfile `digest` == registry `args` digest | ✅ **MATCH** |
| `pull_as` is digest-pinned | ✅ |
| Registry `requires_network: true` / `offline_allowed: false` | ✅ consistent with ADR-0007 |

---

## 4. Final artifact inventory

| # | Artifact | Version | Tier | Provenance |
|---|---|---|---|---|
| 1 | `whisper_large_v3_turbo` | large-v3-turbo | A | host-published-lfs |
| 2 | `whisper_medium` | medium | A | host-published-lfs |
| 3 | `kokoro_v1` | v1.0 | B | host-published-lfs (size-matched) |
| 4 | `kokoro_voices` | v1.0 | B | host-published-lfs (size-matched) |
| 5 | `piper_tr_dfki` | tr_TR-dfki-medium | A | host-published-lfs |
| 6 | `piper_tr_dfki_config` | tr_TR-dfki-medium | A | git-blob-sha1 |
| 7 | `wake_bootstrap` | v0.1 | **D** | single mirror — self-liquidating at G6a |
| 8 | `wake_melspectrogram` | features | C | two independent mirrors agree |
| 9 | `wake_embedding_model` | features | C | two independent mirrors agree |
| 10 | `embedding` | all-MiniLM-L6-v2 | A | pinned-model-id |
| 11 | `qdrant` | v1.18.3 | A | registry-manifest |
| 12 | **`github_mcp`** | **v1.1.2** | **A** | **local-registry-inspect** ← resolved today |
| 13 | `whisper_cpp` | v1.9.1 | A | vcs-commit |

`wake_lionel` remains `NOT_YET_BUILT` — a project-produced artifact, correctly excluded
from the counts.

---

## 5. Full suite

```
17 / 17 gates PASS
```

`structure` · `adr` · `contracts` · `jsonschema` · `protobuf` · **`artifacts`** ·
`docker-digests` · `no-latest` · `no-pending` · `no-todo` · `secrets` · `licenses` ·
`markdown` · `dependencies` · `shell` · `architecture` · **`l0-conformance`**

> **One incident worth recording.** `no-pending` failed transiently mid-verification on
> `config/_selftest.yaml` containing `sha256: PENDING`. That was **litter from an
> interrupted `self_test.sh` run** — the script was killed by a command timeout before its
> cleanup step. Removed; the gate passes. The self-test's own cleanup-verification exists
> precisely for this failure mode and could not fire because the process was killed. Worth
> noting as a real limitation: a `trap`-based cleanup does not survive `SIGKILL`.

---

## 6. Resolution history

| Date | Event |
|---|---|
| 2026-08-02 | Recorded `UNRESOLVED`, tier E. Blocker classified **TEMPORARY** |
| 2026-08-02 → 08-03 | **Twelve** remote retrieval attempts across three sessions. All failed: GHCR requires an `Authorization: Bearer` header the audit environment could not set. An anonymous token *was* obtainable — the credential was in hand, only the header was missing |
| 2026-08-03 | Ten third-party Docker Hub forks found and **rejected** — ADR-0013 forbids substituting one artifact's digest for another's. Two were self-described modified forks |
| 2026-08-03 | Official prebuilt binaries discovered with API-published digests on an immutable release. Recorded as `alternatives[5]`; **not adopted** — switching from image to binary is an architecture change |
| **2026-08-03** | **Operator ran one command. Resolved.** |

**The TEMPORARY classification was correct throughout.** Nothing about GHCR, GitHub, or the
artifact was ever defective. The constraint was a missing capability in one environment, and
it dissolved the moment the command ran somewhere else.

Two things held under pressure and are worth naming, because both were tempting to abandon:

- **No hash was ever invented.** `ART-007` validates format only — a plausible 64-hex string
  would have passed every gate and failed at first pull in Phase 6.
- **No third-party image was substituted.** Ten were available with real pull counts.

---

## 7. G0 status

| Criterion | Status |
|---|---|
| **Artifact lockfile fails closed; zero unresolved** | ✅ **MET** |
| All 28 ADRs have decision + consequences | ✅ |
| Contract schemas validate | ✅ |
| CI runs and reports | ✅ |
| Secret scanner blocks a planted credential | ✅ 9/9 self-test |
| L0 conformance | ✅ 44 checks |

**The G0 artifact criterion is met.** `AUD-M01`, the last G0 blocker identified by the
independent audit, is closed.

### What remains before G0 sign-off

**Not artifact-related, and outside this task's scope:**

- **AUD-C01 residual** — the repository is committed and pushed, but I have no observable
  GitHub Actions run URL. Everything here is local execution.
- Open Major findings from the audit: `AUD-M02` (check counters), `M04` (syntactic
  architecture checks), `M05` (no Windows or Turkish-locale CI job), `M06` (self-test covers
  9 of 17 gates), `M07` (artifact blockers need owner and deadline).

A formal G0 re-audit is the correct next step. **I am not declaring G0 passed** — that is
the auditor's call, and this report is evidence for it, not a verdict.

---

## 8. Files changed

| File | Change |
|---|---|
| `artifacts.lock.yaml` | `github_mcp` → RESOLVED with index + per-platform digests, attestations, provenance, resolution history. `meta` 12/1 → **13/0**. Header STATUS updated |
| `config/capabilities.registry.json` | Invalid placeholder reference → real index digest (**closes AUD-M03**) |
| `ci/policy/policy.yaml` | `local-registry-inspect` added to `valid_provenance` |
| `Artifacts_Final_Report.md` | This document |

No ADR, contract, or gate implementation was modified.
