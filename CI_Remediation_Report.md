# CI Remediation Report

**Category A + Category B, 2026-08-03.**

| | |
|---|---|
| Source of truth | The two findings you reported from the CI run: `ART-000`, `L0-NETDEP-004` |
| **`l0-conformance`** | ❌ 6 violations → ✅ **PASS, 44 checks** |
| **`no-todo`** | ❌ 33 violations → ✅ **PASS** |
| **`artifacts`** | ❌ `ART-000` → ❌ **still failing — unresolvable here** |
| Document exclusions added | **Zero** |

---

## 0. A note on the source of truth

You asked me to use the first real GitHub Actions run rather than local executions. **I
could not retrieve it** — `api.github.com/repos/Denizfe/L.I.O.N.E.L/actions/runs` returns
empty, consistent with a private repository.

I have therefore worked from **the two findings you reported**, which match my local
execution exactly: `ART-000` and `L0-NETDEP-004`. That agreement is itself worth recording
— the pipeline behaves identically in CI and locally, which is what a hermetic gate design
is supposed to deliver.

Every result below is from local execution against the working tree. **No claim here rests
on a CI run I have not seen.**

---

# CATEGORY A

## A1 · `ART-000` — still unresolved

### Root cause

The OCI manifest endpoint requires an `Authorization: Bearer` header. No header-capable
HTTP client exists in this environment. Re-attempted this session against the explicit tag:

```
GET ghcr.io/v2/github/github-mcp-server/manifests/v1.1.2   → empty (401)
```

This is the twelfth distinct attempt across three sessions. The full method log is in
`GHCR_Digest_Justification.md` §2.

### Changes

**None.** The digest was not obtained, so nothing was written. Inventing a plausible 64-hex
string would pass `ART-007` (format-only validation) and fail at first pull in Phase 6 —
ADR-0013: *"a fabricated checksum is strictly worse than an absent one, because it looks
verified."*

### Status

`status: UNRESOLVED` · `tier: E` · `meta: 12/1` — unchanged. **Blocks G0.**

### Resolution, unchanged

```bash
docker buildx imagetools inspect ghcr.io/github/github-mcp-server:v1.1.2
```

One command on any machine with Docker. Classification remains **TEMPORARY**: nothing about
GHCR, GitHub, or the artifact is defective — only this session's tooling.

> An alternative with **already-retrieved tier-A digests** exists — GitHub publishes SHA-256
> for every release asset on immutable release v1.1.2. Adopting it means switching from a
> container image to a native binary, which changes process supervision and removes the
> Docker Desktop dependency on the Windows host. **That is an architecture decision needing
> an ADR, not a lockfile edit.** Evidence recorded in the lockfile's `alternatives[5]`.

---

## A2 · `L0-NETDEP-004` — RESOLVED

### Root cause

ADR-0007 excludes network-dependent capabilities at L0. **That exclusion existed only in
prose** — in the ADR, in the lockfile notes, in three audit reports. The registry schema
permitted `requires_network` with a default of `false`, and **not one of the five
capabilities declared it.**

Absence of a field is not a declaration of `false`. Every prior audit — including mine —
repeated "the GitHub capability is excluded at L0" as established fact. Nothing in the
repository established it.

### Changes

**1. `contracts/mcp/v1/capabilities-registry.schema.json` → v1.1.0**

| Field | Added | Rationale |
|---|---|---|
| `requires_network` | already present → **now required** | Optional means unenforceable |
| `offline_allowed` | new, **required** | Tier-aware L0 admission. Stated separately from `requires_network` so a contradiction is *detectable* rather than inferred |
| `owner` | new, **required**, enum | Same vocabulary as contract ownership |
| `phase` | new, **required**, `^G(10\|[0-9])[a-d]?$` | Makes the registry readable as a delivery plan |
| `trust_level` | new, **required**, enum | Trust the capability's **output** carries — distinct from `trust_required`, which is the minimum trust to **invoke** |
| `governance_note` | new, optional | Why the values are what they are |

Plus **two `allOf` consistency rules** enforcing that `requires_network` and
`offline_allowed` are logical inverses.

> `additionalProperties: false` rejected my first attempt at `governance_note`. The contract
> caught the author. Recorded because that is the schema working.

**2. `config/capabilities.registry.json` — all five capabilities**

| capability | requires_network | offline_allowed | owner | phase | trust_level |
|---|---|---|---|---|---|
| `filesystem` | false | true | capabilities | G1 | **external_content** |
| `github` | **true** | **false** | capabilities | G1 | **external_content** |
| `memory` | false | true | memory | G2 | tool_result |
| `system` | false | true | capabilities | G4 | tool_result |
| `media` | false | true | capabilities | G4 | tool_result |

Derivations worth stating:

- **`filesystem.trust_level: external_content`** — the capability is local, but ADR-0012
  classes file contents as untrusted. The field describes what the *output* carries, not
  where the code runs. Getting this backwards would silently launder hostile file content
  into a trusted turn.
- **`memory.trust_level: tool_result`** with a `governance_note` recording that recall
  inherits each record's stored trust via `MemoryQueryResult.trust_floor` — a memory
  ingested from `external_content` stays `external_content`.
- **`phase`** from MASTER_PLAN_v2 deliverables: filesystem/github at Phase 1,
  memory at Phase 2, system/media at Phase 4.

**3. `ci/gates/gate_l0_conformance.py` — `L0-NETDEP-003` corrected**

The check demanded `enabled: false` on network capabilities. **That was wrong once
`offline_allowed` existed**: the registry is tier-agnostic, so `enabled: false` would
disable GitHub at L1/L2/L3 as well. It now checks `offline_allowed: false`, which is the
tier-aware field designed for exactly this.

### Consistency verification

| # | Check | Result |
|---|---|---|
| 1 | Registry validates against schema v1.1.0 | ✅ 0 errors |
| 2 | ADR-0007: `requires_network == not offline_allowed` | ✅ all 5 consistent |
| 3 | `artifacts.lock.yaml`: `images.github_mcp` provably off the L0 path | ✅ gate confirms |
| 4 | L0 policy vs `l0.toml`: provider not forbidden, network off | ✅ |
| 5 | All 5 fields present on all 5 capabilities | ✅ |
| 6 | Schema's own example still validates | ✅ |

### Gate result

```
l0-conformance   exit=0   PASS 44 checks

  note  declared network-dependent, excluded from L0: github
  note  artifacts off the L0 path (network-backed, excluded by ADR-0007): images.github_mcp
  note  network egress guard: active for the whole run, 0 attempts
  note  13 substantive check group(s) · 0 vacuous
```

**`L0-ARTIFACT-004` cleared as a side effect** — with `github` declaring
`requires_network: true`, the artifact is provably off the L0 path. That is exactly what
the gate's `fix` line asked for: *"declare `requires_network` on the capability backing it,
or resolve the pin."*

---

# CATEGORY B — engineering review

## B1 · Root cause: a detector defect, not a scoping problem

The instruction was not to blindly exclude `*.md`. **The review found that no exclusion was
needed at all.**

`no-todo` matched the **word** `TODO`, not a **marker**:

| Text | Is it a deferred task? | Old rule |
|---|---|---|
| a hash-comment marker with a colon | **yes** | flagged ✅ |
| `TODO-001` | no — a rule identifier | flagged ❌ |
| `a weaker standard than a TODO comment` | no — prose | flagged ❌ |
| `the TODO registry requires an owner` | no — prose | flagged ❌ |

**13 of 37 hits in report documents were the gate's own rule identifiers.** A gate flagging
`TODO-001` is flagging its own vocabulary.

## B2 · Classification of every failing document

| Document | Class | Gate applies? |
|---|---|---|
| `Failed_Gates.md` | generated audit | **yes** |
| `Phase0_Audit_Report.md` | generated audit | **yes** |
| `Gate_Summary.md` | generated audit | **yes** |
| `CI_Execution_Report.md` | generated audit | **yes** |
| `Architecture_Risk_Register.md` | generated audit | **yes** |
| `Phase0_Blockers.md` | generated audit | **yes** |
| `ADR0013_Review.md` | temporary review | **yes** |
| `MASTER_PLAN_v2.md`, `CI_Architecture.md` | architecture | **yes** |
| `ci/policy/policy.yaml`, `config/**` | executable policy | **yes** |
| `README.md`, `Policy_Gates.md`, `CI_Inventory.md`, `docs/**` | product documentation | **yes** |

**The gate applies to every class.** I initially drafted seven per-document exclusions with
individual justifications. After the root-cause fix, **all seven became unnecessary** — and
an exclusion that turns out to be unneeded is removed, not kept "just in case."

## B3 · The review strengthened the gate

`gate_no_todo.py` contained an **undocumented blanket exclusion**:

```python
or r.endswith(("Policy_Gates.md", "CI_Inventory.md", "CI_Architecture.md"))
```

No justification anywhere. It silenced the gate across **one architecture document and two
product documents** — precisely the classes where a TODO is a real deferred promise.

**Removed.** After the detector fix none of the three hits, so the gate now applies to them.
**Category B ended with the gate covering more of the repository than before, not less.**

## B4 · Changes

| File | Change |
|---|---|
| `ci/policy/policy.yaml` | `forbid` word-list → `marker_patterns` (comment-introduced or punctuation-followed). `document_class_exclusions: []` with the classification recorded |
| `ci/gates/gate_no_todo.py` | Uses marker patterns; undocumented blanket removed |

One refinement during testing: `*` was initially treated as a comment introducer (valid in
C block comments) and matched markdown bold `**TODO-001**`. Removed — in markdown `*` is
emphasis, not a comment.

## B5 · Detection is not weakened

Self-test verifies a planted hash-comment marker is still caught:

```
ok    no-todo   catches an unregistered TODO
SELF-TEST PASS  9/9 planted violations caught
```

**Still caught:** hash-comment markers with a colon · slash-comment markers with a
parenthesis · FIXME in a hash comment · indented hash-comment markers followed by text.

**Correctly ignored:** rule identifiers such as TODO-001 · the phrase "a TODO comment" ·
the phrase "the TODO registry".

> The forms are described rather than reproduced. This report has no deferred tasks in
> it, so it should contain no marker-shaped text — and when the first draft did, the gate
> caught it. That is the mechanism working on its own documentation rather than being
> exempted from it.

**Word hits 71 → marker hits 0. No document exempted.**

---

## Gates re-executed

| Gate | Before | After |
|---|---|---|
| **`l0-conformance`** | ❌ 6 violations | ✅ **PASS — 44 checks** |
| **`artifacts`** | ❌ `ART-000` | ❌ **FAIL — unchanged** |
| **`no-todo`** | ❌ 33 violations | ✅ **PASS** |
| `jsonschema` | ✅ | ✅ PASS — 155 checks *(schema changed)* |
| `contracts` | ✅ | ✅ PASS — 34 checks *(schema changed)* |
| `structure` | ✅ | ✅ PASS — 24 checks |
| `gate-self-test` | ✅ | ✅ **9/9** |

`jsonschema`, `contracts` and `structure` were run because the registry contract changed,
not because they were failing.

---

## Remaining blockers

| ID | Blocker | Status |
|---|---|---|
| **AUD-M01 / `ART-000`** | GHCR image digest | **OPEN — the only G0 blocker left.** One `docker buildx imagetools inspect` away. TEMPORARY |
| AUD-C01 residual | No observable GitHub Actions run | Repository is committed and pushed; I cannot see a run URL from here |

**Everything else in Category A and Category B is closed.**

### Not addressed here, deliberately

- **Adopting the prebuilt binary** instead of the container image. Digests are retrieved and
  recorded; adoption is an architecture change requiring an ADR.
- `AUD-M02` (check counters), `M04` (syntactic architecture checks), `M05` (no Windows or
  Turkish-locale CI job), `M06` (self-test covers 9 of 17 gates), `M07` (artifact blockers
  need owner and deadline). Out of scope for this remediation.

---

## Files changed

```
contracts/mcp/v1/capabilities-registry.schema.json   v1.0.0 → v1.1.0
config/capabilities.registry.json                    5 governance fields × 5 capabilities
ci/gates/gate_l0_conformance.py                      L0-NETDEP-003 → offline_allowed
ci/gates/gate_no_todo.py                             marker patterns; blanket removed
ci/policy/policy.yaml                                marker_patterns; classification
CI_Remediation_Report.md                             new
```

No ADR was modified. `artifacts.lock.yaml` was not modified in this round.
