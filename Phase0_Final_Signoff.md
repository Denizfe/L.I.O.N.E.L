# Phase 0 — Final Sign-off

| | |
|---|---|
| Auditor | Independent Principal Architect · Principal DevSecOps · Release Manager · Technical Auditor |
| Date | 2026-08-03 · **remediation verified 2026-08-10 (§15)** |
| Scope | Complete independent audit for Architecture Freeze |
| Method | Clean-clone execution + cross-artefact consistency verification |
| **VERDICT** | **FAIL** (2026-08-03) → **PASS** (2026-08-10, §15) |

---

## 1. Executive Summary

**The architecture is ready. The repository is not.**

Every architectural consistency check passes. ADRs, contracts, policies, capability
registry, artifact lock, trust model and CI are mutually consistent with **zero
contradictions found**. The design is implementation-ready.

**One Critical blocker prevents the freeze: none of the Phase 0 remediation is committed.**

```
$ git rev-parse HEAD      == origin/main   (30285c0)
$ git status --porcelain  →  9 modified · 3 untracked
```

The claimed "17/17 gates green" is a property of an **uncommitted working tree**. The
repository — the version-controlled artefact that would be frozen, cloned, and handed to
the next engineer — is at **13/17**.

**An architecture cannot be frozen at a state that does not exist in version control.** A
freeze must name a commit. There is no commit containing this architecture.

The blocker is trivial to clear — one `git add`, one commit, one push — but it is absolute.
Until then, the freeze would certify a state nobody else can obtain.

---

## 2. Repository Status

### 2.1 Version control — **BLOCKER**

| Check | Result |
|---|---|
| Commits | 4 |
| Branch / upstream | `main` → `origin/main` |
| HEAD == origin/main | ✅ yes (`30285c0`) |
| Tracked files | 161 |
| **Modified, uncommitted** | **9** |
| **Untracked** | **3** |

**Files whose current content is not in any commit:**

```
 M artifacts.lock.yaml                                  ← GHCR digest, meta 13/0
 M config/capabilities.registry.json                    ← 5 governance fields × 5 caps
 M contracts/mcp/v1/capabilities-registry.schema.json   ← schema v1.1.0
 M ci/policy/policy.yaml                                ← l0 section, marker patterns
 M ci/gates/gate_l0_conformance.py                      ← L0-NETDEP-003 correction
 M ci/gates/gate_no_todo.py                             ← marker-pattern detector
 M CI_Execution_Report.md · Failed_Gates.md · Gate_Summary.md
?? Artifacts_Final_Report.md · CI_Remediation_Report.md · GHCR_Digest_Justification.md
```

### 2.2 What a clean clone actually produces

Cloned `HEAD` into a scratch directory and executed all 17 gates with only the declared
dependencies:

| | Working tree | **Clean clone (HEAD)** |
|---|---|---|
| Gates passing | 17 / 17 | **13 / 17** |
| `artifacts` | PASS | **FAIL** — `ART-000`, `github_mcp` UNRESOLVED |
| `l0-conformance` | PASS | **FAIL** — `L0-NETDEP-004` ×5, `L0-ARTIFACT-004` |
| `no-todo` | PASS | **FAIL** — 33 violations |
| `markdown` | PASS | **FAIL** — 1 violation |
| `artifacts.lock.yaml` | 13 resolved / 0 unresolved | **12 / 1** |
| Capabilities declaring `requires_network` | 5 / 5 | **0 / 5** |

### 2.3 Repository hygiene — clean

| Check | Result |
|---|---|
| CRLF in index | **0** — `.gitattributes` applied |
| Runtime `.py` under `src/lionel/` | **0** — Phase 0 discipline held |
| Self-test litter | **0** |
| `src/lionel/capabilities/shell/` | absent (ADR-0011) |
| Machine-specific paths in `ci/` | **0** (one `.pyc`, gitignored) |
| Python version pinned in workflow | 18 declarations |
| Ignore rules exercised | `models/`, `data/`, `logs/`, `backups/`, `__pycache__` all excluded |

---

## 3. Architecture Status — **CONSISTENT**

| Check | Result |
|---|---|
| ADR count vs policy expectation | 28 / 28 ✅ |
| Numbering contiguous 0001–0028 | ✅ |
| Superseded ADRs name their successor | ✅ |
| Dangling ADR references | **none** ✅ |
| Contradictory ADRs remaining | **none** ✅ |
| Circular dependencies | **none** — protobuf graph is a tree; `stt`/`tts` import only `common` ✅ |

Every gate file, `ORDER` entry and workflow job reconciles exactly:

```
gates on disk : 17    ORDER : 17    workflow gate jobs : 17
missing from ORDER : none    in ORDER without a file : none    missing from workflow : none
```

---

## 4. Security Status — **CONSISTENT**

| Check | Result |
|---|---|
| Trust vocabulary: `TrustContext` ↔ registry `trust_level` | **identical** ✅ |
| Capability `trust_level` values valid | ✅ |
| `trust_required` floor vocabulary (incl. `any`) intentionally distinct | ✅ documented |
| ADR-0011 — no shell execution in the capability surface | ✅ |
| ADR-0012 — policy default pinned `deny` by `const` | ✅ |
| ADR-0012 — `ToolCall.trust`, `ToolResult.trust_of_output` required | ✅ |
| ADR-0025 — `ProviderRequest.cancellation_token_id` required | ✅ |
| Secret scanning — zero path exclusions | ✅ |
| L0 network egress guard | ✅ armed, 0 attempts |

**Security assumptions are documented** across ADR-0011, ADR-0012, ADR-0015, ADR-0022 and
`Secret_Scanning_Design.md`.

---

## 5. CI Status

| | Working tree | Clean clone |
|---|---|---|
| Gates | **17 / 17 PASS** | **13 / 17** |
| Workflow jobs | 18 | 18 |
| Stubbed jobs | **0** | 0 |
| Self-test | 9 / 9 planted violations caught | 9 / 9 |
| **Self-test gate coverage** | **7 of 17 gates** | — |

**`l0-conformance` is not covered by the standing self-test** — see Finding M1.

---

## 6. Contract Status — **COHERENT**

| Check | Result |
|---|---|
| Contract set version | 1.1.0 |
| Schemas on disk | 27 + 3 protobuf |
| `Contract_Inventory.md` claim | 27 ✅ matches |
| `MANIFEST.json` control-plane list vs `mcp/v1` on disk | 8 = 8 ✅ |
| `capabilities-registry.schema.json` | v1.1.0, breaking change recorded ✅ |
| Registry validates against its schema | ✅ 0 errors |
| Every schema declares version / plane / owner / producer / consumers | ✅ 27/27 |

---

## 7. ADR Status — **CLEAN**

28 ADRs. ADR-0004 superseded by ADR-0010 with a forward link. ADR-0013 carries a dated
Erratum plus two Amendments; ADR-0017 carries a Correction and an Amendment. All
cross-references resolve. **No ADR contradicts another.**

---

## 8. Artifact Status — **RESOLVED (working tree)**

| | |
|---|---|
| Artifacts | **13 / 13 RESOLVED · 0 UNRESOLVED** |
| Tiers | A=8 · B=2 · C=2 · D=1 |
| Tier-D count vs policy max | 1 ≤ 1 ✅ |
| All provenance values in policy allowlist | ✅ |
| `meta` counts vs actual | ✅ no drift |
| Placeholder strings | **0** |
| Lockfile digest ↔ registry arg digest | ✅ **MATCH** |

**Not in any commit.** See §2.

---

## 9. Capability Registry Status — **CONSISTENT**

| capability | requires_network | offline_allowed | owner | phase | trust_level |
|---|---|---|---|---|---|
| `filesystem` | false | true | capabilities | G1 | external_content |
| `github` | **true** | **false** | capabilities | G1 | external_content |
| `memory` | false | true | memory | G2 | tool_result |
| `system` | false | true | capabilities | G4 | tool_result |
| `media` | false | true | capabilities | G4 | tool_result |

| Check | Result |
|---|---|
| All 5 governance fields on all 5 capabilities | ✅ |
| `requires_network == !offline_allowed` (ADR-0007) | ✅ all 5 |
| Owners ⊆ contract owner vocabulary | ✅ |
| Phases match `^G(10\|[0-9])[a-d]?$` | ✅ G1, G2, G4 |
| ADR-0007 L0 exclusion machine-readable | ✅ |

---

## 10. Findings

### CRITICAL

**C1 — Phase 0 remediation is not committed; a clean clone fails 4 gates**

*Evidence:* `git status --porcelain` → 9 modified, 3 untracked. Clean clone of HEAD scores
13/17; `artifacts.lock.yaml` reads 12/1 with `github_mcp: UNRESOLVED`; 0 of 5 capabilities
declare `requires_network`.

*Impact:* The architecture to be frozen exists only on one machine. A freeze names a commit;
no commit contains this architecture. Another engineer cloning today receives a repository
that fails artifact verification and L0 conformance.

*Blocks Phase 1:* **YES.**

### MAJOR

**M1 — `l0-conformance` has no standing self-test coverage**

*Evidence:* `ci/self_test.sh` covers 7 of 17 gates. `l0-conformance` is absent.

*Impact:* The keystone gate — 8 invariants, 18 rules, network egress guard — has no
regression protection. Ten negative tests were executed when it was built, but none is in
the standing suite, so a future change could silently disable it. `CI_Architecture.md` §7
states the project's own rule: *"a gate that has never rejected anything is unproven."*

*Blocks Phase 1:* **No.** The gate demonstrably works today (44 checks, 0 violations). This
is regression risk, not present unsafety.

### MINOR

**N1** — `CI_Inventory.md` states 16 gates; 17 exist. **N2** — `Policy_Gates.md` catalogues
90 rules; 116 are extractable, the L0 gate's rules being uncatalogued. Both are generated
documents that need regeneration. Neither affects implementation safety.

### INFORMATIONAL

**I1** — `pyproject.toml` and `uv.lock` are absent. **Correct for Phase 0** — policy declares
`lockfile_required_at: G1`. **I2** — One tier-D artifact (`wake_bootstrap`), documented and
self-liquidating at G6a per ADR-0023.

---

## 11. Remaining Risks

| Risk | Severity | Status |
|---|---|---|
| Architecture exists only in an uncommitted working tree | **Critical** | **OPEN — C1** |
| L0 gate could silently regress | Major | OPEN — M1 |
| No observable GitHub Actions run | Minor | Repository is pushed; no run URL available to this audit |
| No Windows or Turkish-locale CI job | Minor | Windows-first project, Ubuntu-only CI |
| Tier-D artifact provenance | Minor | Documented, bounded, self-liquidating |
| Self-test covers 7 of 17 gates | Major | Subsumed by M1 |

---

## 12. Implementation Readiness

### Can Phase 1 begin today?

**No.**

### Exactly what prevents it

**The repository does not contain the architecture.**

An engineer cloning `origin/main` today receives:

- `artifacts.lock.yaml` with an **unresolved** artifact — `artifacts` gate fails, and
  ADR-0013's `[RECORD]` duty is unmet
- A capability registry where **no capability declares `requires_network`** —
  `l0-conformance` fails 6 checks, and ADR-0007's L0 exclusion is unenforceable
- A `no-todo` detector with the pre-fix pattern — 33 violations
- No `Artifacts_Final_Report.md`, `CI_Remediation_Report.md` or `GHCR_Digest_Justification.md`

Phase 1's first task is to build the host runtime skeleton against these contracts and
policies. **Those contracts and policies are not in the repository.**

This is the only thing preventing Phase 1. It is not a design problem.

---

## 13. Architecture Freeze Readiness

| Criterion | Verdict |
|---|---|
| Architecture internally consistent | ✅ |
| Trust model consistent | ✅ |
| Capability registry matches ADRs | ✅ |
| Contracts match architecture | ✅ |
| Policies match implementation rules | ✅ |
| CI enforces architecture | ✅ 17 gates, 116 rules |
| Artifact lock reproducible | ✅ 13/13, tiers declared |
| Security assumptions documented | ✅ |
| Ownership defined | ✅ contracts + capabilities |
| Versioning coherent | ✅ |
| No circular dependencies | ✅ |
| No contradictory ADR | ✅ |
| **Frozen state exists in version control** | ❌ **C1** |

**Twelve of thirteen criteria met.** The thirteenth is not a design property — it is whether
the design has been committed.

---

## 14. Final Verdict

# FAIL

**One blocker. Nothing else.**

**C1 — The Phase 0 architecture is not committed to version control.**

```
git add -A
git commit -m "[LIONEL-CORE] Phase 0: architecture freeze candidate"
git push
```

Then re-verify: clean clone → 17/17 gates → record the commit SHA in
`Architecture_Freeze.md` → re-submit for sign-off.

**No architectural change is required. No design defect was found.** The architecture
passed every consistency check in this audit. It simply does not yet exist anywhere except
one working tree, and a freeze that cannot name a commit is not a freeze.


---

## 15. Remediation — 2026-08-10

**Everything above is the audit as it stood on 2026-08-03 and is left unedited.** The
evidence tables in §2.2 and §12 describe a repository that no longer exists; they are kept
verbatim because a verdict whose evidence has been rewritten to agree with it is not a
verdict. This section records what changed.

### 15.1 C1 — CLOSED

The Phase 0 remediation is committed and pushed.

```
commit 0066cb23c0447070714ab11df270c2c955ac35c1
        [LIONEL-CORE] Phase 0: architecture freeze 1.0.0
        12 paths — exactly the 9 modified + 3 untracked enumerated in §2.1
```

Re-executed the §2.2 comparison against a clean clone of that commit:

| | Working tree (2026-08-03) | Clean clone of `0066cb2` | Clean clone of `architecture-1.0.0` |
|---|---|---|---|
| Gates passing | 17 / 17 | **17 / 17** | **17 / 17** |
| `artifacts` | PASS | PASS | PASS |
| `l0-conformance` | PASS | PASS | PASS |
| `no-todo` | PASS | PASS | PASS |
| `markdown` | PASS | PASS | PASS |
| `artifacts.lock.yaml` | 13 / 0 | **13 / 0** | **13 / 0** |
| Capabilities declaring `requires_network` | 5 / 5 | **5 / 5** | **5 / 5** |
| Self-test | 9 / 9 | 9 / 9 | **10 / 10** |
| Architecture checksum reproduces | — | ❌ **no** (§15.3) | ✅ **yes** |

CI confirms it independently:
[run 31368070033](https://github.com/Denizfe/L.I.O.N.E.L/actions/runs/31368070033) — green
on the freeze commit; the three preceding pushes are red, which is the 13/17 this audit
recorded.

### 15.2 M1 — CLOSED

`ci/self_test.sh` now plants `network_allowed = true` in `config/tiers/l0.toml` and asserts
`L0-OFFLINE-002`. **10/10**, up from 9/9. The keystone gate has standing regression
protection.

`config/tiers/l0.toml` is inside the architecture checksum set, so the test restores it from
a byte-exact backup and the restoration is **verified**, not assumed — an unrestored file
would move the architecture checksum and read as an unexplained architecture change.

### 15.3 Three defects this audit did not reach

Verifying the remediation found three problems, all in the tooling around the architecture
rather than in the architecture. None changes the checksum.

**A — the architecture checksum was not reproducible from a clone.** `.gitattributes` pinned
`eol=lf` for `.sh/.py/.md/.toml/.json/.yaml/.yml` but not `.proto`, so a Windows clone
checked the three proto files out as CRLF and computed a different contracts-group digest —
and therefore a different architecture checksum — from the same commit. §13's criterion
"frozen state exists in version control" was met by `0066cb2`; the checksum recorded against
it was not a property of it. Fixed in `b2e0b94`; verified by clean clone.

*This audit could not have seen it.* It compared gate results, and no gate reads the
checksum. It is visible only by recomputing the checksum somewhere other than where it was
first computed.

**B — every gate crashed on a cp1252 console.** `ci/gates/_lib.py` printed box-drawing
characters unconditionally. On any Windows console defaulting to cp1252 — the default on the
host platform this project targets, ADR-0002 and ADR-0014 — all 17 gates died with
`UnicodeEncodeError` inside `report_and_exit`, *after* their checks had passed, and the
runner correctly reported exit 2, "broken gate", on a clean repository. §5's "17/17" was a
property of a shell with `PYTHONIOENCODING=utf-8` exported. Fixed in `b2e0b94`.

This is also why §11's "no Windows CI job" was more than a minor gap: the Windows job added
for it fails immediately on this bug. On Actions stdout is a pipe, where Python still selects
the locale encoding.

**C — the generated documents had no generator.** `CI_Inventory.md` and `Policy_Gates.md`
both ended with "Regenerate rather than hand-edit" while nothing could regenerate them.
`scripts/generate_ci_docs.py` now does. Findings N1 and N2 are closed, with one correction
to this audit: **N2's "116 extractable" is itself an undercount.** Rule IDs read off
`g.fail(...)` call sites miss the 24 rules `l0-conformance` emits through a single
table-driven call — which is exactly how the gate came to be absent from the catalogue.
Counting distinct emittable rule IDs gives **127**.

### 15.4 Remaining risks

| Risk | Severity | Status |
|---|---|---|
| Architecture exists only in an uncommitted working tree | Critical | **CLOSED** — `0066cb2` |
| L0 gate could silently regress | Major | **CLOSED** — self-test 10/10 |
| Self-test covers 7 of 17 gates | Major | **Reduced** — 9 of 17. Open, tracked for Phase 1 |
| No observable GitHub Actions run | Minor | **CLOSED** — 20/20 jobs green |
| No Windows or Turkish-locale CI job | Minor | **CLOSED** — both jobs added and green |
| Checksum not reproducible across platforms | Critical | **CLOSED** — §15.3 A |
| Tier-D artifact provenance | Minor | Open — documented, bounded, self-liquidating at G6a |
| Piper voice licence deferred to MODEL_CARD | Minor | Open — checklist item 4 |

### 15.5 Verdict

# PASS

C1 and M1 are closed; §13's thirteenth criterion is met. Three further defects were found
and fixed in the process, two of them load-bearing for the freeze's own claims.

**Phase 1 may begin.** Its remaining prerequisites — `pyproject.toml`, `uv.lock`, the Piper
licence — are G1 items, not G0 blockers, and are tracked in `Phase1_Entry_Checklist.md`.

*Remediation verified 2026-08-10 against a clean clone of `architecture-1.0.0`.*


---

## 16. Second remediation — 2026-08-10, later the same day

**§15 is left unedited, as §15 left §2.2 unedited.** It was accurate when written and is
now partly stale, which is worth showing rather than hiding: the gap between "we fixed it"
and "the document still says otherwise" is the subject of this section.

### 16.1 What §15 said that is no longer true

| §15 | Then | Now |
|---|---|---|
| §15.4 — self-test covers 9 of 17 gates, "Open, tracked for Phase 1" | 9/17 | **20/20.** Closed the same day, not tracked forward |
| §15.5 — remaining prerequisites: `pyproject.toml`, `uv.lock`, the Piper licence | 3 open | **0 open.** All nine checklist items closed |
| §15.3 C — 127 rules | 127 | **136** — three meta-gates added |

### 16.2 What was done

Architecture **1.1.1**, tagged. The full record is `Architecture_Freeze.md` §9; in brief:

- **Three meta-gates** — `checksum`, `generated-docs`, `gate-coverage` (ADR-0030,
  `Proposed`). Each enforces something this repository already asserted about itself and
  checked nowhere.
- **Self-test 10 → 21 assertions, coverage 9/17 → 20/20**, `coverage.exempt` empty. The
  suite also now asserts it left the architecture checksum byte-identical.
- **Item 4 closed with a finding, not a tick.** The Turkish voice is **CC-BY-NC-SA-4.0**:
  personal use unaffected, distribution blocked, no alternative voice exists. R-A15 escalated
  Minor → Major. ADR-0031 (`Proposed`) adds the register that lets a reviewed licence be
  recorded rather than suppressed.
- **ADR-0029** (`Proposed`) closes the ADR-0016 errata gap this audit did not reach.
- **Six risk-register rows closed**, three of which still read *"blocks G0"* after G0 was
  signed off.

### 16.3 The finding this section exists to record

§10's MINOR findings N1 and N2 were scored as documentation drift — *"Neither affects
implementation safety."* That was true of the two instances and wrong about the class.

The same shape produced every defect found on 2026-08-10, including one Critical: the
architecture checksum did not reproduce from a clone, so §13's thirteenth criterion was met
in form and not in fact. **Documentation drift is not a cosmetic category in a repository
whose controls are documents.** A stale count is harmless; a stale *invariant* is a control
that has stopped working while still being cited.

This audit could not have found it. It compared gate results, and no gate read the checksum,
the generated documents, or the coverage figure. Three now do.

### 16.4 What is still not enforced

`generated-docs` covers documents that have a generator — two. This document does not, and
neither does `Architecture_Risk_Register.md` or `CI_Architecture.md`. All three asserted
stale counts within an hour of the gates going green, which is how §16.1 came to exist.

Recorded as an open limitation in ADR-0030's Costs rather than presented as closed.

### 16.5 Verdict — unchanged

# PASS

C1 and M1 remain closed. Nothing found on 2026-08-10 reopens them. Phase 1 may begin; three
`Proposed` ADRs await Efe under Architecture_Freeze.md §5 step 4, and none of them blocks it.

*Second remediation verified 2026-08-10 against a clean clone of `architecture-1.1.1`.*
