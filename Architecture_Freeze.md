# Architecture Freeze

| | |
|---|---|
| Architecture version | **1.1.1** |
| Freeze date | **2026-08-10** |
| Tag | **`architecture-1.1.1`** |
| Status | **FROZEN** |
| Previous versions | **1.1.0**, **1.0.0** — both tagged, both unchanged and still valid |
| Pending approval | ADR-0029, ADR-0030, ADR-0031 are **Proposed** — see §9 |

> **In force.** 1.1.0 is additive: it adds three decisions and three gates, and changes no
> decision already in force. `architecture-1.0.0` is untouched and remains a valid freeze of
> what it froze. **Clone the tag, not a commit** — §8.3 explains why that distinction
> matters here.
>
> **Three of 1.1.0's ADRs are `Proposed`.** Their gates are implemented and green so the
> decisions can be judged against something real, but under §5 step 4 they are not in force
> until Efe accepts them. §9 records what happens if he does not.

---

## 1. Architecture version

**1.1.1** — PATCH over 1.1.0: errata only. No decision changed, no ADR added. Four documents
asserted counts that had stopped being true, and ADR-0030 claimed a class was closed when it
was narrowed — see §9.5.

**1.1.0** — MINOR over 1.0.0: three new ADRs, no decision already in force changed.

**1.0.0** — the first frozen architecture of L.I.O.N.E.L.

Semantic meaning for this project:

| Component | Change requires |
|---|---|
| **MAJOR** | A superseding ADR that changes a decision already in force |
| **MINOR** | A new ADR that adds a decision without contradicting an existing one |
| **PATCH** | An erratum correcting text to state a decision already in force |

---

## 2. Architecture checksum

Deterministic SHA-256 over the architecture-defining set — sorted paths, path bytes plus
file bytes, grouped, then the group digests concatenated and hashed.

```
ARCHITECTURE CHECKSUM                                          architecture 1.1.1
sha256:aed60f6faa836855f634fa1fd5a547c728e3ccabf2d209c2eb798e45cea60d24

  ADRs         31 files   sha256:f837ac0df5d9965a60f311c2f2f1b3ba…
  contracts    31 files   sha256:222451c587f1c1ca1f2c29d1c908e989…
  policy        8 files   sha256:f2e7a3ff07f21392edb56eb58abeda82…
  artifacts     1 file    sha256:fc4d6a69230d0b3b5fb25d3f12b71176…
  plan          1 file    sha256:fb9f2e57f26eff1fd50854bc96680f7e…

  72 files hashed
```

Superseded values, kept so the earlier tags stay verifiable:

```
architecture 1.1.0   sha256:71c7c2fce1fccb2e0e263f98454d72ce85ce3220f3a17c5fea1e7ccaa1181687
                     72 files — ADRs 31 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.0.0   sha256:fab0610aa3167a2f26b0e812dbfe9563abbf7aa28ab18b9d773d945a5a84f233
                     69 files — ADRs 28 · contracts 31 · policy 8 · artifacts 1 · plan 1
```

**This value is now enforced.** `gate_checksum` recomputes it on every push and fails
`CHECKSUM-001` on drift, `CHECKSUM-003` if a group changes shape (ADR-0030). Between 1.0.0
and 1.1.0 it was recorded and checked by nothing — which is how it came to be wrong.

**Verified against a clean clone on 2026-08-10.** Reproduce it with:

```bash
python3 scripts/architecture_checksum.py --verify sha256:fab0610aa3167a2f26b0e812dbfe9563abbf7aa28ab18b9d773d945a5a84f233
```

The algorithm is: files partitioned into the five groups below; within a group, sorted by
POSIX-relative path; group digest = `sha256` over the concatenation of (path bytes ‖ file
bytes) with no separator; architecture checksum = `sha256` over the five **raw** group
digests concatenated in the order listed. `scripts/architecture_checksum.py` implements it
and reproduces every group digest above.

**Line endings are part of the checksum.** `.gitattributes` must pin every extension in the
set to `eol=lf` or the same commit yields two different checksums on two machines. This was
not merely theoretical: `*.proto` was unpinned, so a Windows clone checked the three proto
files out as CRLF and computed `222451c5…` → `0a3b44bc…` for the contracts group. Fixed in
`b2e0b94`.

### Files in the checksum set

```
docs/decisions/ADR-*.md                    28
contracts/{core,mcp,events,media}/v1/*.schema.json   27
contracts/grpc/v1/*.proto                   3
contracts/MANIFEST.json                     1
config/**/*.toml, config/*.json             7
ci/policy/policy.yaml                       1
artifacts.lock.yaml                         1
MASTER_PLAN_v2.md                           1
```

---

## 3. Frozen scope

The following are **frozen** at version 1.0.0. Changing any of them requires an ADR under §5.

| Element | Frozen state |
|---|---|
| **Architecture decisions** | **31 ADRs, 0001–0031** — 0029/0030/0031 `Proposed` |
| **Contracts** | Contract set 1.1.0 — 27 JSON Schemas + 3 protobuf, 5 planes |
| **Capability registry** | 5 capabilities, each declaring `requires_network`, `offline_allowed`, `owner`, `phase`, `trust_level` |
| **Artifact lock** | 13 artifacts, all RESOLVED, tiers A=8 B=2 C=2 D=1 |
| **Tier model** | L0–L3 per ADR-0007; L0 conformance is a blocking gate |
| **Trust model** | 4 levels, monotonically non-increasing within a turn (ADR-0012) |
| **Plane separation** | MCP = control, gRPC = data; no PCM on the control plane (ADR-0006) |
| **Policy** | `ci/policy/policy.yaml` — 16 sections |
| **CI gates** | **20 gates, 136 rules, 23 workflow jobs** — 17 checking the repository, 3 checking the pipeline (ADR-0030). Self-test 21/21, gate coverage 20/20 |
| **Phase plan** | MASTER_PLAN_v2 — 11 gated phases, G0–G10 |

---

## 4. Allowed future changes

Permitted **without** an ADR:

1. **Implementation** under `src/lionel/` conforming to frozen contracts.
2. **Tests** under `tests/` and `evals/`.
3. **Gate implementation work** that enforces an existing decision more completely —
   extending `ci/self_test.sh`, adding coverage. **Adding a new rule that changes what is
   permitted requires an ADR.**
4. **Regenerating generated documents** — `CI_Inventory.md`, `Policy_Gates.md`,
   `Contract_Inventory.md`.
5. **Errata** — correcting text to state a decision already in force, recorded as a dated
   Erratum quoting the original verbatim (precedent: ADR-0013, 2026-08-02).
6. **Artifact version bumps** within an existing artifact, following ADR-0013 pinning rules
   and ADR-0021 evaluation gates.

Requiring an ADR:

1. Any new subsystem, technology, or dependency.
2. Any change to a contract's `stable` surface.
3. Any change to the tier model, trust model, or plane separation.
4. Any new capability, or a change to an existing capability's governance fields.
5. Any relaxation of a gate, exclusion, or policy threshold.
6. Any change to the phase plan or gate criteria.

---

## 5. Change control policy

**Every architectural change follows ADR-0016.**

| Step | Requirement |
|---|---|
| 1 | Search existing ADRs and memory first. Settled decisions are not relitigated silently |
| 2 | Write an ADR: Status · Context · Decision · Consequences · **Alternatives Rejected** · **Verification** |
| 3 | Name the gate criterion that verifies it. A decision with no test is a preference |
| 4 | **Efe's explicit approval** before the ADR is Accepted |
| 5 | Implement the gate that enforces it |
| 6 | Add a planted violation to `ci/self_test.sh` |
| 7 | Recompute the architecture checksum; bump the architecture version |

**Commits use the `[LIONEL-CORE]` prefix. No autonomous commit or push — ever.**

---

## 6. ADR modification policy

**ADRs are immutable once Accepted.** Three permitted operations:

| Operation | Mechanism | Precedent |
|---|---|---|
| **Supersede** | New ADR; original's `Status` line updated with a forward link. Original text untouched | ADR-0004 → ADR-0010 |
| **Amend** | Dated `## Amendment` section appended. Adds scope without contradicting | ADR-0013 ×2, ADR-0017 |
| **Erratum** | Dated `## Erratum` section correcting text to state a decision **already in force**. Original wording quoted verbatim. **No policy change** | ADR-0013, 2026-08-02 |

Forbidden: editing an Accepted ADR's Decision in place without an Erratum; deleting an ADR;
renumbering.

> **Open governance gap, recorded not fixed:** ADR-0016 has no erratum provision, while
> practice has diverged from it three times. Closing it requires an ADR and is a Phase 1
> item.

---

## 7. Phase 1 entry criteria

Phase 1 may begin when **all** hold:

| # | Criterion | Status |
|---|---|---|
| 1 | Architecture frozen at a named commit SHA | ✅ `0066cb2`, tag `architecture-1.0.0` |
| 2 | Clean clone of that commit scores 17/17 gates | ✅ verified 2026-08-10 |
| 3 | `artifacts.lock.yaml` — 0 unresolved, in the frozen commit | ✅ 13 resolved / 0 unresolved |
| 4 | Capability registry governance fields, in the frozen commit | ✅ 5 of 5 capabilities |
| 5 | Architecture checksum recorded against the commit SHA | ✅ reproducible — `scripts/architecture_checksum.py` |
| 6 | ADR count 28, no contradictions | ✅ |
| 7 | Contract set 1.1.0, all schemas valid, examples validate | ✅ |
| 8 | Trust model consistent across contracts and registry | ✅ |
| 9 | CI enforces the architecture — 17 gates wired | ✅ |
| 10 | Security assumptions documented | ✅ |
| 11 | Ownership defined for contracts and capabilities | ✅ |
| 12 | No circular dependencies | ✅ |

**12 of 12 met.** Phase 1 may begin.

---

## 8. Freeze execution

Performed 2026-08-10.

### 8.1 What was executed

| Step | Result |
|---|---|
| 1 · Commit the architecture | `0066cb2` — 12 paths, exactly the set the audit enumerated |
| 2 · Push | `origin/main`, [run 31368070033](https://github.com/Denizfe/L.I.O.N.E.L/actions/runs/31368070033) green |
| 3 · Clean-clone, all gates | **17 / 17**, `0` broken |
| 4 · Clean-clone, self-test | **10 / 10** planted violations caught |
| 5 · Recompute the checksum | `sha256:fab0610a…` — **matches**, all five group digests |
| 6 · Tag | `architecture-1.0.0` |
| 7 · Re-submit the sign-off | `Phase0_Final_Signoff.md` §15 — verdict **PASS** |

Only the twelve paths the audit listed went into `0066cb2`. Nothing found afterwards was
folded back into it: a freeze commit that quietly grew is a freeze of something nobody
audited.

### 8.2 Reproducing the freeze

```bash
git clone https://github.com/Denizfe/L.I.O.N.E.L.git && cd L.I.O.N.E.L
git checkout architecture-1.0.0
pip install pyyaml jsonschema grpcio-tools
bash ci/run_gates.sh          # expect 17/17, 0 broken
bash ci/self_test.sh          # expect 10/10
python3 scripts/architecture_checksum.py --verify sha256:fab0610aa3167a2f26b0e812dbfe9563abbf7aa28ab18b9d773d945a5a84f233
```

`grpcio-tools` is required: without it the `protobuf` gate exits 2, which is a broken gate,
not a passing repository, and the runner reports it as such.

### 8.3 Why the tag is not on `0066cb2`

Verifying the freeze surfaced three defects in the tooling around it. None touched the
architecture — the checksum is byte-identical across all of them — but two had to be fixed
before the freeze could mean what it claims.

| Commit | Fix | Why it blocks the freeze |
|---|---|---|
| `b2e0b94` | `*.proto text eol=lf` | Without it a Windows clone computes a **different** architecture checksum. §7 criterion 5 is then unmeetable: the recorded checksum is not a property of the commit |
| `b2e0b94` | UTF-8 stdout in `ci/gates/_lib.py` | Every gate died with `UnicodeEncodeError` on a cp1252 console, reporting "broken gate" on a clean repository. §7 criterion 2 unverifiable on the platform this project targets |
| `b2e0b94` | `scripts/architecture_checksum.py` | A checksum nobody can recompute cannot detect drift, so §2 asserted something unfalsifiable |
| `968eace` | Regenerated `CI_Inventory.md`, `Policy_Gates.md` | Findings N1/N2. Documentation only |

All four are permitted by §4 without an ADR: items 3 and 4 — gate work that enforces an
existing decision more completely, and regenerating generated documents.

So `0066cb2` is where the architecture entered version control, and `architecture-1.0.0` is
the commit you should clone: the first one where the freeze's own criteria are all
demonstrably met.

### 8.4 Rule count: 116 → 127

§3 previously recorded 116 rules, an audit estimate taken from `g.fail(...)` call sites.
That undercounts, because `l0-conformance` emits 24 distinct rules through a **single**
`g.fail(rid, …)` driven by an invariant table. Counting distinct emittable rule IDs gives
**127**, now derived mechanically by `scripts/generate_ci_docs.py`. The gates did not
change; the count was wrong. Recorded here rather than silently corrected, per §6.

---

## 9. Version 1.1.0 — what changed and why

1.1.0 landed the same day as 1.0.0. That is not a sign the freeze was premature; it is what
the freeze was for. Verifying 1.0.0 end to end produced five findings, and they turned out
to be one finding five times.

### 9.1 The root cause

| The repository stated | Enforced by | What was true |
|---|---|---|
| "Regenerate rather than hand-edit" — both generated documents | nothing | 16 gates claimed vs 17; 88 rules vs 127; `l0-conformance` **absent from the rule catalogue** |
| "Deterministic checksum" — §2 of this document | nothing | not reproducible from a clone for 8 days |
| "A gate that has never rejected anything is unproven" — `CI_Architecture.md` §7 | nothing | 8 of 17 gates had never rejected anything |
| Windows + Git Bash is the host runtime — ADR-0002, ADR-0014 | nothing | every gate crashed on a cp1252 console |
| "verify per MODEL_CARD before release" — `artifacts.lock.yaml` | a registered deferral | the card said CC-BY-NC-SA-4.0, on the only Turkish voice |

Five rules the project wrote down, believed, cited elsewhere — and never gave a test. Its
own doctrine names the failure: *a decision with no test is a preference.* The doctrine had
never been applied to itself. Seventeen gates enforced invariants about the repository; none
enforced invariants about the gates, the documents describing them, or this freeze.

### 9.2 What 1.1.0 adds

| | |
|---|---|
| **ADR-0029** `Proposed` | Errata / Amendment / Supersede. Closes the §6 gap: ADR-0016 forbids what correct practice has done three times |
| **ADR-0030** `Proposed` | The pipeline enforces its own invariants — the three meta-gates |
| **ADR-0031** `Proposed` | A `review_required` licence must have somewhere to be reviewed |
| **`checksum`** gate | Recomputes §2 on every push. Would have caught the CRLF defect on the first Linux run |
| **`generated-docs`** gate | Every generated document matches its generator. Would have caught N1 and N2 the day they appeared |
| **`gate-coverage`** gate | Every gate has rejected a planted violation. Counts **gates**, not assertions |
| **Self-test 10 → 21 assertions** | Gate coverage **9/17 → 20/20**, with `coverage.exempt` empty |
| **R-A15 escalated** | Minor → Major. The Turkish voice is CC-BY-NC-SA-4.0: personal use unaffected, distribution blocked |

Nothing in force at 1.0.0 changed. §1's MINOR definition — "a new ADR that adds a decision
without contradicting an existing one" — is met three times over.

### 9.3 Why the version had to move

`docs/decisions/ADR-*.md` and `ci/policy/policy.yaml` are both inside the checksum set, so
adding three ADRs and a policy section changed the checksum whether or not anyone recorded
it. §5 step 7 requires the recomputation and the bump. What is new is that skipping it is
now impossible rather than merely discouraged: `gate_checksum` fails.

That is the shape of every change in 1.1.0. None of it is new policy. All of it is existing
policy that had no mechanism.

### 9.5 Version 1.1.1 — the gates' first real finding

Within an hour of 1.1.0 being tagged, a review found four documents asserting things that
had stopped being true. **None of them is generated, and none is in the checksum set, so no
gate could see any of it.**

| Document | Said | Actually |
|---|---|---|
| `Architecture_Risk_Register.md` | R-A01, R-A03 **"OPEN — blocks G0"**; R-A05, R-A06, R-A08 OPEN | G0 signed off; all six closed by work landed that day |
| `Phase0_Final_Signoff.md` §15 | coverage 9/17 "tracked for Phase 1"; three prerequisites open; 127 rules | 20/20; zero open; 136 rules |
| `CI_Architecture.md` §8 | `15 pass · 1 fail by design` | `20 pass · 0 fail` |
| `MASTER_PLAN_v2.md` §9 | an ADR table stopping at 0028 | 31 ADRs exist |
| `ADR-0030` | "The five defect classes are **closed** by mechanism" | Three are. The class is **narrowed** |

**R-A05 and R-A08 are the sharpest of these.** An auditor wrote them on 2026-08-02 —
*"silent CI coverage loss (counter ≠ coverage)"* and *"untested gates fail silently when
they matter"* — reading a pipeline that reported 8/8. Both were right. Both sat OPEN for
eight days while the counter climbed to 10/10 and eight gates still had never rejected
anything. **The register named the root cause before it was measured, and nothing acted on
it, because a risk row is prose and prose does not fail a build.** That is ADR-0030's thesis,
written down by someone else, a week early, and ignored — which is the strongest argument
for it in this document.

The corrections are errata: text brought into line with decisions already in force. Per §1
that is a PATCH. Two of them touch the checksum set — `ADR-0030` and `MASTER_PLAN_v2.md` —
so the checksum moved and had to be re-recorded and re-tagged for a set of typo-class fixes.

**That cost is the mechanism working.** `gate_checksum` went red on the first edit and
stayed red until §2 was updated. Before 1.1.0 the same edits would have silently invalidated
the recorded checksum, which is precisely how the CRLF defect survived eight days.

**What is still not enforced:** every hand-written document that asserts a count about this
repository — including this one. `generated-docs` covers documents that have a generator,
currently two. ADR-0030's Costs now record this rather than claiming the class is closed.
Closing it needs a different decision and its own ADR.

### 9.4 If the Proposed ADRs are rejected

They are additive and nothing depends on them.

| Rejected | Effect |
|---|---|
| ADR-0029 | Nothing to unwind — `ADR-009` was deliberately **not** implemented. A gate enforcing an unapproved decision is the error ADR-0030 is about |
| ADR-0030 | Remove `checksum`, `generated-docs`, `gate-coverage` from `ORDER` and from `ci.yml`. The 21 self-test assertions stay — §4 item 3 permits them without an ADR |
| ADR-0031 | Remove `licenses.review_accepted`. `licenses` returns to failing `LIC-002` on the Turkish voice, which is a true statement about an unresolved question |

Any of those is a MINOR bump of its own, not a revert of 1.1.0.

---

*Prepared 2026-08-03. In force 2026-08-10: 1.0.0, extended to 1.1.0, corrected to 1.1.1 — all the same day.*
