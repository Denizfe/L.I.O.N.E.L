# Failed Gates

**4 of 17 gates failed.** Two block G0; two do not.
Executed 2026-08-03 from a genuine `git clone`. **Nothing was fixed.**

| Gate | Violations | Blocks G0 |
|---|---|---|
| [`artifacts`](#gate-1--artifacts) | 1 | **YES** |
| [`l0-conformance`](#gate-2--l0-conformance) | 6 | **YES** |
| [`no-todo`](#gate-3--no-todo) | 33 | No |
| [`markdown`](#gate-4--markdown) | 1 | No |

---

## Gate 1 — `artifacts`

### Gate name
`artifacts` · `ci/gates/gate_artifacts.py` · job **"artifacts · lockfile integrity"**

### Failure reason
Rule **ART-000** — one artifact carries `status: UNRESOLVED`. ADR-0013's `[RECORD]` duty
requires every artifact to hold an immutable pin **by G0**.

**Red by design.** Unchanged from the previous run.

### Evidence

```
  ✗ ART-000  1 artifact(s) unresolved
      at    artifacts.lock.yaml
      why   ADR-0013: G0 cannot be signed off while any artifact is unpinned.
      fix   Follow the alternatives in Artifact_Verification_Report.md §5.

  FAIL  1 violation(s) across 16 checks
```

`images.github_mcp` · tier E · `digest: null` · blocker classified TEMPORARY · 4 reproducible
alternatives · `meta.unresolved: 1` · 12 of 13 artifacts RESOLVED.

### Exact remediation

```bash
docker buildx imagetools inspect ghcr.io/github/github-mcp-server:<version-tag>
```

Then in `artifacts.lock.yaml` under `images.github_mcp`: set `status: RESOLVED` ·
`digest: sha256:<64 hex>` · `verification.tier: A` · `provenance: registry-manifest` ·
`method:` (≥ 40 chars, ART-008) · `retrieved:` today · `meta.resolved: 13` ·
`meta.unresolved: 0` · delete `blocker` and `alternatives`.

Also update `config/capabilities.registry.json:23`, which holds
`@sha256:UNRESOLVED-see-artifacts.lock.yaml` — an invalid image reference (AUD-M03).

> Use an explicit version tag. `:latest` is mutable and `no-latest` would reject it.
> **Never paste a plausible 64-hex string** — ART-007 validates format only, so a
> fabricated digest passes every gate and fails at first pull in Phase 6.

### Blocks G0
**YES.** ADR-0013 `[RECORD]`, a named G0 criterion. Tracked as **AUD-M01**.

---

## Gate 2 — `l0-conformance`

### Gate name
`l0-conformance` · `ci/gates/gate_l0_conformance.py` · job **"l0-conformance · offline invariants (BLOCKING — ADR-0007)"**

### Failure reason
**6 violations across 44 checks**, and 5 of them are a single finding:

**No capability in the registry declares `requires_network`.**

> This gate replaced two `echo` statements that exited 0 and reported green. Its first
> real execution found a gap every prior audit had asserted away.

### Evidence

```
  ✗ L0-NETDEP-004  capability `filesystem` does not declare `requires_network`
  ✗ L0-NETDEP-004  capability `github`     does not declare `requires_network`
  ✗ L0-NETDEP-004  capability `memory`     does not declare `requires_network`
  ✗ L0-NETDEP-004  capability `system`     does not declare `requires_network`
  ✗ L0-NETDEP-004  capability `media`      does not declare `requires_network`
      at    config/capabilities.registry.json
      why   ADR-0007 excludes network-dependent capabilities at L0. That exclusion is
            unenforceable against an undeclared field: absence is not a declaration
            of `false`.

  ✗ L0-ARTIFACT-004  cannot prove `images.github_mcp` is off the L0 path,
                     and it is UNRESOLVED
      at    artifacts.lock.yaml
      why   An unpinned artifact of unknown reachability must be treated as reachable.

  FAIL  6 violation(s) across 44 checks
```

Confirmed independently:

```
filesystem   requires_network=(ABSENT)
github       requires_network=(ABSENT)
memory       requires_network=(ABSENT)
system       requires_network=(ABSENT)
media        requires_network=(ABSENT)

schema: requires_network default=False, required=False
```

**ADR-0007's exclusion of the GitHub capability at L0 exists only in prose** — in the ADR,
in the lockfile notes, in three audit reports. Nowhere machine-readable. The schema permits
the field with a default of `false`; not one capability declares it.

The other 12 invariants passed, including: L0 tier `network_allowed=false` · all services
`inproc` · provider `ollama` not `anthropic` · no shell execution in the runtime surface ·
no mutable image tags · required contracts present · policy default pinned `deny` ·
ToolCall requires `trust` · ToolResult requires `trust_of_output` · ProviderRequest requires
`cancellation_token_id` · `memory.forget` required · **egress guard active, 0 attempts**.

### Exact remediation

**Step 1 — declare network status on all five capabilities.** In
`config/capabilities.registry.json`:

```jsonc
"filesystem": { …, "requires_network": false },
"github":     { …, "requires_network": true  },   // ADR-0007 excludes it at L0
"memory":     { …, "requires_network": false },   // inproc; Qdrant is local
"system":     { …, "requires_network": false },
"media":      { …, "requires_network": false }
```

This converts ADR-0007's exclusion from prose into an enforceable fact.

**Step 2 — `L0-ARTIFACT-004` then clears automatically.** Once `github` declares
`requires_network: true`, `images.github_mcp` is provably off the L0 path.

**Recommended follow-up (separate review):** make `requires_network` **required** in
`contracts/mcp/v1/capabilities-registry.schema.json` so a future capability cannot omit it.
That is a schema change and belongs in its own change.

> **Note the interaction with Gate 1.** Step 1 clears `l0-conformance` but leaves
> `artifacts` red. The two gates ask different questions: `artifacts` wants the digest
> recorded; `l0-conformance` wants to know whether the artifact is on the offline path.
> That separation is intentional.

### Blocks G0
**YES.** ADR-0007: *"L0 conformance is a blocking CI gate on every release."*

---

## Gate 3 — `no-todo`

### Gate name
`no-todo` · `ci/gates/gate_no_todo.py` · job **"no-todo · unregistered markers"**

### Failure reason
Rule **TODO-001** — 33 unregistered `TODO` occurrences. **All 33 are in documents produced
by this audit/review process**, where TODO governance is the subject matter. None is a
deferred task.

**Up from 10 in the previous run.** This is compounding.

### Evidence

| File | Hits | Origin |
|---|---|---|
| `Failed_Gates.md` | **21** | audit output — previous run of *this* report |
| `Phase0_Audit_Report.md` | 6 | audit output |
| `Architecture_Risk_Register.md` | 2 | audit output |
| `Phase0_Blockers.md` | 1 | audit output |
| `Gate_Summary.md` | 1 | audit output |
| `CI_Execution_Report.md` | 1 | audit output |
| `ADR0013_Review.md` | 1 | review output |

Representative context — every hit is prose *about* the registry:

```
Phase0_Audit_Report.md:56   …with rules TODO-002 and LIC-005 policing the escape hatches…
Phase0_Audit_Report.md:436  …a weaker standard than this project applies to a TODO comment.
Phase0_Audit_Report.md:451  | AUD-N01 | TODO registry entry is over-broad | …
```

### Root cause

`gate_no_todo.py` excludes `ci/` and `docs/`. **Root-level `.md` is not excluded**, and
every audit artefact lives at the repository root.

`no-latest` and `no-pending` both exclude `.md` wholesale, on the stated rationale that
*"gates police executable config, not prose that documents a rejected practice."*
**`no-todo` never received that treatment.**

**This is a compounding feedback loop.** Each audit round produces documents discussing
forbidden tokens; those documents are scanned; violations rise; the next round documents the
rise. 10 → 33 in one cycle, with 21 from a single generated file. Left alone, this gate goes
permanently red and stops being read — the failure `CI_Architecture.md` warns about when
arguing against a warnings tier.

### Exact remediation

**Option A — align with the sibling gates (recommended).** In `ci/gates/gate_no_todo.py`,
exclude `.md` as `no-latest` and `no-pending` already do. Makes three gates consistent
rather than two-plus-one, and the rationale is already written and accepted.

**Option B — register the generated documents** in `ci/policy/policy.yaml`:

```yaml
todo:
  registry:
    - pattern: "TODO"
      path_glob: "*.md"
      owner: architecture
      unblocked_by: "n/a — audit records are immutable"
```
Sits awkwardly against `TODO-002`, which rejects entries with no removal route; would need
`TODO-002` to permit an explicit permanent-exemption value.

**Option C — accept a standing red.** Defensible since it does not block G0. **Not
recommended** — and now actively harmful, since the count grows every audit round.

### Blocks G0
**No.** Phase 0's DoD names: every ADR has decision and consequences · contract schemas
validate · **CI runs and reports** · secret scanner blocks a planted credential · artifact
lockfile fails closed on a corrupted checksum. TODO hygiene is not among them, and the DoD
explicitly permits failing CI.

Tracked as a variant of **AUD-N01**.

---

## Gate 4 — `markdown`

### Gate name
`markdown` · `ci/gates/gate_markdown.py` · job **"markdown · links + structure"**

### Failure reason
Rule **MD-HEADING** — a heading level jumps from `h1` to `h3`.

**New since the previous run.** Also generated by this audit process.

### Evidence

```
  ✗ MD-HEADING  heading jumps from h1 to h3
      at    Failed_Gates.md:199
      why   Skipped levels break document outline and screen-reader navigation, and
            usually mean a section was deleted without re-levelling its children.
      fix   Use h2 here, or add the intermediate heading.

  FAIL  1 violation(s) across 52 checks
```

`Failed_Gates.md:199` is in the previous run's output of **this very report** — the
"Not a gate failure, but worse than one" section, which used `###` directly under `#`.

All 51 other markdown checks passed: internal links resolve, no trailing whitespace,
heading hierarchy correct everywhere else.

### Exact remediation

Re-level the heading in `Failed_Gates.md` from `###` to `##`, or introduce the intermediate
`##` section.

> This run's regenerated `Failed_Gates.md` uses `##` throughout, so the specific violation
> is expected to clear on the next execution. The **class** of problem — generated
> documents tripping structural gates — remains, and is the same scoping question as
> Gate 3.

### Blocks G0
**No.** No G0 criterion references heading structure.

---

## Summary

| | |
|---|---|
| Gates failed | 4 of 17 |
| **Blocking G0** | **2** — `artifacts` (AUD-M01) and `l0-conformance` (new) |
| Non-blocking | 2 — `no-todo`, `markdown` (both audit-generated) |
| Gate errors (exit 2) | 0 |
| New blockers this run | **1** — `l0-conformance`, and it is a genuine discovery |

### Where the four failures come from

| Source | Gates |
|---|---|
| Known open work | `artifacts` |
| **Real gap found by the new L0 gate** | `l0-conformance` |
| Audit process generating its own noise | `no-todo`, `markdown` |

**Only two of the four represent work on the product.** The other two are a scoping gap in
two gates, made visible by this process producing documents about the tokens those gates
hunt.

### G0 outlook

| ID | Status |
|---|---|
| **AUD-C01** | ⚠️ **Mostly resolved** — 4 commits, 161 files, pushed to `origin/main`, clean clone works. Residual: no observable GitHub Actions run |
| **AUD-M01** | **OPEN** — one `docker buildx imagetools inspect` away |
| **L0 declaration gap** | **OPEN** — five `requires_network` fields away |

---

*Audit only. No repository file was modified. `CI_Execution_Report.md`, `Gate_Summary.md`
and `Failed_Gates.md` were overwritten with this run's results.*
