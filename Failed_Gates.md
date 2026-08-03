# Failed Gates

**2 of 16 gates failed.** One blocks G0; one does not.
Executed 2026-08-02 from a clean-checkout simulation. **Nothing was fixed.**

| Gate | Violations | Blocks G0 |
|---|---|---|
| [`artifacts`](#gate-1--artifacts) | 1 | **YES** |
| [`no-todo`](#gate-2--no-todo) | 10 | No |

---

## Gate 1 — `artifacts`

### Gate name
`artifacts` · `ci/gates/gate_artifacts.py` · workflow job **"artifacts · lockfile integrity"**

### Failure reason
Rule **ART-000** — one artifact in `artifacts.lock.yaml` has `status: UNRESOLVED`.
ADR-0013's `[RECORD]` clause requires every artifact to carry an immutable pin **by G0**.

**This gate is red by design.** It is behaving exactly as specified.

### Evidence

```
  ✗ ART-000  1 artifact(s) unresolved
      at    artifacts.lock.yaml
      why   ADR-0013: G0 cannot be signed off while any artifact is unpinned.
            This gate is RED on purpose until the lockfile reaches zero unresolved.
      fix   Follow the alternatives in Artifact_Verification_Report.md §5, then
            update the lockfile entry and meta counts.

  FAIL  1 violation(s) across 16 checks
```

The artifact:

```yaml
images:
  github_mcp:
    status: UNRESOLVED
    ref: ghcr.io/github/github-mcp-server
    digest: null
    verification: { tier: E }
    blocker:
      classification: TEMPORARY
      what: >-
        GHCR requires an Authorization: Bearer header on the manifest endpoint…
    alternatives: 4 (all reproducible)
```

Corroborating state: `meta.unresolved: 1` · `meta.gate: "G0 blocks while unresolved > 0"`
· 12 of 13 artifacts RESOLVED (tiers A×7, B×2, C×2, D×1).

### Exact remediation

Two valid paths. Both are approved options; neither has been taken.

**Path A — resolve the digest (~5 minutes, recommended)**

```bash
docker buildx imagetools inspect ghcr.io/github/github-mcp-server:<version-tag>
```

Then in `artifacts.lock.yaml` under `images.github_mcp`:

| Field | Set to |
|---|---|
| `status` | `RESOLVED` |
| `digest` | `sha256:<64 lowercase hex>` from the inspect output |
| `verification.tier` | `A` |
| `verification.provenance` | `registry-manifest` |
| `verification.method` | how it was obtained (≥ 40 chars — ART-008 enforces this) |
| `verification.retrieved` | today's date |
| `meta.resolved` | `13` |
| `meta.unresolved` | `0` |
| `blocker`, `alternatives` | delete |

Also update `config/capabilities.registry.json:23`, which currently holds
`@sha256:UNRESOLVED-see-artifacts.lock.yaml` — a syntactically invalid image reference
(`AUD-M03`).

> Use an explicit version tag. `:latest` is mutable, and pinning a mutable tag defeats the
> purpose — `no-latest` (DOCKER-002) would reject it anyway.

**Path B — adopt an approved ADR amendment**

`ADR0013_Review.md` proposes ADR-0029 (per-artifact gating by first use). Note that
`ADR0013_Contradiction_Resolution.md` §7 records that this proposal was **weakened** —
part of its evidence rested on a misreading since corrected. It should be re-argued on its
practical merits rather than adopted to clear this gate.

**Not acceptable:** pasting a plausible 64-hex string. `ART-007` validates format only;
a fabricated digest would pass every gate and be caught at first pull in Phase 6.
ADR-0013: *"a fabricated checksum is strictly worse than an absent one, because it looks
verified."*

### Blocks G0
**YES.**

ADR-0013 `[RECORD]`: *"`artifacts.lock.yaml` fails closed … on any `UNRESOLVED` entry"* at
Gate G0. `artifacts.lock.yaml` header: *"G0 cannot be signed off until this file contains
zero of them."* This is a named G0 criterion and it is unmet.

Tracked as **AUD-M01**.

---

## Gate 2 — `no-todo`

### Gate name
`no-todo` · `ci/gates/gate_no_todo.py` · workflow job **"no-todo · unregistered markers"**

### Failure reason
Rule **TODO-001** — 10 unregistered `TODO` occurrences.

**All 10 are in audit and review documents that discuss TODO governance as their subject
matter.** None is a deferred task.

### Evidence

```
  ✗ TODO-001  unregistered `TODO`   at ADR0013_Review.md:249
  ✗ TODO-001  unregistered `TODO`   at Architecture_Risk_Register.md:127
  ✗ TODO-001  unregistered `TODO`   at Architecture_Risk_Register.md:133
  ✗ TODO-001  unregistered `TODO`   at Phase0_Audit_Report.md:56
  ✗ TODO-001  unregistered `TODO`   at Phase0_Audit_Report.md:436
  ✗ TODO-001  unregistered `TODO`   at Phase0_Audit_Report.md:451
  ✗ TODO-001  unregistered `TODO`   at Phase0_Audit_Report.md:547
  ✗ TODO-001  unregistered `TODO`   at Phase0_Audit_Report.md:552
  ✗ TODO-001  unregistered `TODO`   at Phase0_Audit_Report.md:554
  ✗ TODO-001  unregistered `TODO`   at Phase0_Blockers.md:172

  FAIL  10 violation(s) across 11 checks
```

Distribution: `Phase0_Audit_Report.md` ×6 · `Architecture_Risk_Register.md` ×2 ·
`ADR0013_Review.md` ×1 · `Phase0_Blockers.md` ×1

Representative context — every hit is prose *about* the TODO registry:

```
Phase0_Audit_Report.md:56    …with rules TODO-002 and LIC-005 policing the escape hatches…
Phase0_Audit_Report.md:436   …a weaker standard than this project applies to a TODO comment.
Phase0_Audit_Report.md:451   | AUD-N01 | TODO registry entry is over-broad | …
```

### Root cause

`gate_no_todo.py` excludes `ci/` and `docs/`. **Root-level `.md` is not excluded.** Every
audit artefact lives at the repository root.

This is the same class as the exclusion already granted to `no-latest` and `no-pending`,
which skip `.md` entirely on the stated rationale that *"gates police executable config, not
prose that documents a rejected practice."* **`no-todo` did not receive that treatment.**

The gate is not malfunctioning — it is correctly reporting a scope that was never widened
to cover documents whose subject is the thing being scanned.

### Exact remediation

Three valid options. **Not applied — audit only.**

**Option A — align with `no-latest` / `no-pending` (recommended)**

In `ci/gates/gate_no_todo.py`, extend the skip prefix from `("ci/", "docs/")` to also cover
root-level markdown, or filter by suffix as the sibling gates do:

```python
# current
if r.startswith(("ci/", "docs/")):
# aligns with no-latest / no-pending, which exclude .md wholesale
```

Rationale is already written and accepted for two other gates. This makes three gates
consistent rather than two-plus-one.

**Option B — register the audit documents in `ci/policy/policy.yaml`**

```yaml
todo:
  registry:
    - pattern: "TODO"
      path_glob: "Phase0_*.md"
      owner: architecture
      unblocked_by: "never — audit records are immutable"
```

Consistent with the existing registry mechanism, but `unblocked_by: never` sits awkwardly
against `TODO-002`, which exists to reject entries with no removal route. Would need
`TODO-002` to permit an explicit permanent-exemption value.

**Option C — accept it as a standing red**

Defensible, since `no-todo` does not block G0. **Not recommended** — a permanently red gate
that everyone knows to ignore is how a pipeline stops being read.

### Blocks G0
**No.**

MASTER_PLAN_v2's Phase 0 DoD names: every ADR has decision and consequences · contract
schemas validate · **CI runs and reports** · secret scanner blocks a planted credential ·
artifact lockfile fails closed on a corrupted checksum.

**TODO hygiene is not among them**, and the DoD explicitly states *"failing is fine; present
is mandatory"* for CI. This failure is cosmetic with respect to G0.

Tracked as a variant of **AUD-N01** (TODO registry scope).

---

## Not a gate failure, but worse than one

### `l0-conformance` reports SUCCESS while asserting nothing

Not counted above because it exits 0. Recorded here because a green vacuous gate is more
dangerous than a red one.

```yaml
- name: Assert no network egress during the L0 suite
  run: echo "STUB — needs the sensory harness (ADR-0027)…"
- name: Wake → STT → brain(ollama) → tools → TTS, EN and TR, no microphone
  run: echo "STUB — Phase 6…"
```

Both steps are `echo` → exit 0 → **GitHub reports a green checkmark.**

This is the keystone gate of ADR-0007 — the mechanism that is supposed to make offline
operation impossible to erode unnoticed. It currently produces a passing result for doing
nothing, and `config/tiers/l0.toml` describes `network_allowed: false` as *"asserted by the
conformance suite, not merely documented"* — no suite asserts it.

The workflow comment anticipates two states (*"failing later is fine — ABSENT is not"*) but
not the third: **present, green, and hollow.**

**Suggested remediation:** make the stub steps `exit 1` with an explicit "not implemented
until Phase 6" message, so the job is honestly red until real. **Blocks G0: no** — the DoD
requires the gate be *wired*, and it is.

---

## Summary

| | |
|---|---|
| Gates failed | 2 of 16 |
| **Blocking G0** | **1** — `artifacts` (AUD-M01) |
| Non-blocking | 1 — `no-todo` |
| Gate errors (exit 2) | 0 |
| New blockers found by this run | **none** |

Both failures were known before execution. **The run surfaced no new G0 blocker.**

The outstanding G0 items remain **AUD-C01** (repository has 0 commits; CI has never run) and
**AUD-M01** (`artifacts` gate red).

---

*Audit only. No repository file was modified. `CI_Execution_Report.md`, `Gate_Summary.md`
and `Failed_Gates.md` are new files.*
