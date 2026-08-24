# Architecture Freeze

| | |
|---|---|
| Architecture version | **1.6.0** |
| Freeze date | **2026-08-10** |
| Tag | **`architecture-1.6.0`** |
| Status | **FROZEN** — Phase 1 open; the freeze governs the architecture, not the code written against it |
| Previous versions | **1.5.0**, **1.4.0**, **1.3.0**, **1.2.0**, **1.1.1**, **1.1.0**, **1.0.0** — all tagged, all unchanged and still valid |
| Governance | **0 ADRs pending.** ADR-0033 and ADR-0032 both accepted 2026-08-24 |

> **In force.** 1.1.0 is additive: it adds three decisions and three gates, and changes no
> decision already in force. `architecture-1.0.0` is untouched and remains a valid freeze of
> what it froze. **Clone the tag, not a commit** — §8.3 explains why that distinction
> matters here.
>
> **All 33 ADRs are in force.** ADR-0033 was accepted 2026-08-24 and implemented in the
> same version — but only after the working gate was removed from the repository so the
> decision could be made in writing rather than by having shipped. §9.9.
>
> ADR-0032 was accepted 2026-08-24 and implemented in the
> same version: `.mcp.json` now exists, `gate_mcp` enforces `MCP-000`–`MCP-003`, and the ADR
> carries an Erratum discharging the two paragraphs that described it as pending. §9.8.
> ADR-0029, ADR-0030 and ADR-0031 were accepted 2026-08-11;
> `ADR-009`, which ADR-0029 deliberately left unimplemented while it was `Proposed`, landed
> with the acceptance. §9.6 records what that surfaced.

---

## 1. Architecture version

**1.6.0** — MINOR over 1.5.0: `STRUCT-004` lifted and Phase 1 opened. No ADR was added
and no decision changed — G0's sign-off (2026-08-10) was always the condition, and
`STRUCT-004`'s own fix text names updating `repository.runtime_code_forbidden_until` as the
way to satisfy it. The version moves because `ci/policy/policy.yaml` is in the checksum set.

**1.5.0** — MINOR over 1.4.0: ADR-0033 added and accepted, bringing `doc-claims` with it.
No decision already in force changed.

**1.4.0** — MINOR over 1.3.0: ADR-0032 accepted, so a pending decision comes into force,
which §1 defines as MINOR. Nothing already in force changed. `.mcp.json` and `gate_mcp`
land with the acceptance.

**1.3.0** — MINOR over 1.2.0: ADR-0032 added (`Proposed`). No decision in force changed.

**1.2.0** — MINOR over 1.1.1: ADR-0029, ADR-0030 and ADR-0031 accepted and in force, and
`ADR-009` implemented. No decision already in force changed; three that were pending now
bind.

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
ARCHITECTURE CHECKSUM                                          architecture 1.6.0
sha256:e279470a2d42ce319437f5fd16593accf0870aca88c28ebc07ee1ed4e8aed1ba

  ADRs         33 files   sha256:20888f57f60d14ad15267a754f793c3c…
  contracts    31 files   sha256:222451c587f1c1ca1f2c29d1c908e989…
  policy        8 files   sha256:5dbaf3178194cf136cd02c3aae785ae1…
  artifacts     1 file    sha256:fc4d6a69230d0b3b5fb25d3f12b71176…
  plan          1 file    sha256:fb9f2e57f26eff1fd50854bc96680f7e…

  74 files hashed
```

Superseded values, kept so the earlier tags stay verifiable:

```
architecture 1.5.0   sha256:e5dbceda15533d681589400ec455677592307877d787cd780350bf90dd791818
                     74 files — ADRs 33 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.4.0   sha256:8d77af2c61f6fedfe748221abcffb00f6f7f703e81d8e3c5b0e4d35712d2d86d
                     73 files — ADRs 32 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.3.0   sha256:c13b16c6527ac26564e4041ec2c71aa88a72b59ac12cf6d6f94d3b4ef94bd481
                     73 files — ADRs 32 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.2.0   sha256:77e6f37244a7ffa6248a3c1607b42f23145493ecebcd0cb1ce1f8b1425479ec7
                     72 files — ADRs 31 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.1.1   sha256:aed60f6faa836855f634fa1fd5a547c728e3ccabf2d209c2eb798e45cea60d24
                     72 files — ADRs 31 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.1.0   sha256:71c7c2fce1fccb2e0e263f98454d72ce85ce3220f3a17c5fea1e7ccaa1181687
                     72 files — ADRs 31 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.0.0   sha256:fab0610aa3167a2f26b0e812dbfe9563abbf7aa28ab18b9d773d945a5a84f233
                     69 files — ADRs 28 · contracts 31 · policy 8 · artifacts 1 · plan 1
```

**This value is now enforced.** `gate_checksum` recomputes it on every push and fails
`CHECKSUM-001` on drift, `CHECKSUM-003` if a group changes shape (ADR-0030). Between 1.0.0
and 1.1.0 it was recorded and checked by nothing — which is how it came to be wrong.

**Verified against a clean clone on 2026-08-24** (1.4.0 and 1.5.0, the same day). Reproduce it with:

```bash
python3 scripts/architecture_checksum.py --verify sha256:e279470a2d42ce319437f5fd16593accf0870aca88c28ebc07ee1ed4e8aed1ba
```

The algorithm is: files partitioned into the five groups below; within a group, sorted by
POSIX-relative path; group digest = `sha256` over the concatenation of (path bytes ‖ file
bytes) with no separator; architecture checksum = `sha256` over the five **raw** group
digests concatenated in the order listed. `scripts/architecture_checksum.py` implements it
and reproduces every group digest above.

**Line endings are part of the checksum, and `CHECKSUM-004` now enforces it directly.**
`.gitattributes` governs what git *checks out*; it does not stop a tool from writing CRLF
into a working copy afterwards, and `CHECKSUM-001` cannot see that on its own — it compares
the recorded value against one computed from the same contaminated bytes, so both agree and
the gate goes green. `CHECKSUM-004` reads every file in the set and fails on a CR. This was
not merely theoretical, twice: `*.proto` was unpinned, so a Windows clone checked the three proto
files out as CRLF and computed `222451c5…` → `0a3b44bc…` for the contracts group. Fixed in
`b2e0b94`. And while 1.4.0 was being prepared, a Python `write_text()` without `newline=""`
rewrote `ci/policy/policy.yaml` and `ADR-0032` with `os.linesep`; the wrong value was
recorded, and the only thing that noticed was a `git add` warning. §9.8.

### Files in the checksum set

```
docs/decisions/ADR-*.md                    33
contracts/{core,mcp,events,media}/v1/*.schema.json   27
contracts/grpc/v1/*.proto                   3
contracts/MANIFEST.json                     1
config/**/*.toml, config/*.json             7
ci/policy/policy.yaml                       1
artifacts.lock.yaml                         1
MASTER_PLAN_v2.md                           1
```

**`.mcp.json` is not in this set**, and ADR-0032 says why: it is workstation tooling, not
architecture. Adding it would mean every developer-tool version bump moved the architecture
checksum, which would teach people that a moved checksum is routine — the one lesson this
mechanism cannot afford to teach. `structure` guarantees the file exists and `gate_mcp`
checks its contents; neither is a claim about the architecture.

---

## 3. Frozen scope

The following are **frozen** at version 1.0.0. Changing any of them requires an ADR under §5.

| Element | Frozen state |
|---|---|
| **Architecture decisions** | **33 ADRs, 0001–0033** — all Accepted or Superseded, 0 pending |
| **Contracts** | Contract set 1.1.0 — 27 JSON Schemas + 3 protobuf, 5 planes |
| **Capability registry** | 5 capabilities, each declaring `requires_network`, `offline_allowed`, `owner`, `phase`, `trust_level` |
| **Artifact lock** | 13 artifacts, all RESOLVED, tiers A=8 B=2 C=2 D=1 |
| **Tier model** | L0–L3 per ADR-0007; L0 conformance is a blocking gate |
| **Trust model** | 4 levels, monotonically non-increasing within a turn (ADR-0012) |
| **Plane separation** | MCP = control, gRPC = data; no PCM on the control plane (ADR-0006) |
| **Policy** | `ci/policy/policy.yaml` — 16 configuration sections (`mcp` added at 1.4.0) |
| **CI gates** | **22 gates, 145 rules, 26 workflow jobs** — 18 checking the repository, 4 checking the pipeline (ADR-0030, ADR-0033). Self-test 25/25, gate coverage 22/22 |
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

> **~~Open governance gap, recorded not fixed:~~ CLOSED 2026-08-11.** The gap — ADR-0016
> having no erratum provision while practice had diverged from it three times — is closed by
> **[ADR-0029](docs/decisions/ADR-0029-adr-errata-provision.md)**, accepted 2026-08-11 and
> enforced by **`ADR-009`**. ADR-0016 carries a dated Amendment pointing to it. The table
> above is no longer a description of practice; it is the rule.

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

### 9.6 Version 1.2.0 — the ADRs accepted, and what enforcing one taught

Efe accepted ADR-0029, ADR-0030 and ADR-0031 on 2026-08-11. Three consequences.

**The acceptance was itself the first test of ADR-0029.** Each ADR asserted its own
`Proposed` status *in its body*, and ADR-0029 rule 1 makes the body append-only — so the
status could not simply be edited out. Each carries a dated `## Erratum — 2026-08-11`
quoting the superseded sentence verbatim. ADR-0016 carries a dated `## Amendment` pointing
to ADR-0029, which under the old rule would have been forbidden and under the new one is the
correct instrument. **The mechanism's first use was on the document that introduced it.**

**`ADR-009` landed, having been deliberately withheld.** ADR-0029's Verification said the
rule would not be implemented until acceptance, "a gate enforcing an unapproved decision
would be the same category error this ADR is about." That condition was met in that order.

**Implementing it surfaced a problem the ADR had not anticipated,** and this is the part
worth reading. ADR-0029 rule 2 requires an Erratum to quote verbatim what it corrects.
**ADR-0017's `## Correction — 2026-08-02` paraphrases instead.** It is a faithful correction,
written nine days before the rule existed.

Enforcing rule 2 retroactively would have failed `ADR-009` on ADR-0017 **permanently, with
no permitted fix** — adding the missing quote means editing the body of an Accepted ADR,
which rule 1 forbids. The gate would have had no reachable green state: precisely the failure
ADR-0031 was written about, reproduced by the ADR meant to prevent that class, on its first
day.

Resolved by an Amendment to ADR-0029 rather than by quietly weakening the gate:
`errata_quote_required_from: "2026-08-11"` in policy, so the boundary is a reviewable value.
Rule 4 (the date) binds everything; rule 2 binds forward. `gate_adr` **reports the two
grandfathered sections as notes on every run** rather than passing silently — a
grandfathered violation that stops being visible is just a violation.

> A rule cannot bind documents written before it existed. The cheap move was to drop rule 2;
> the honest one was to bound it, say where the boundary is, and keep saying what sits on the
> far side of it.

### 9.7 Version 1.3.0 — ADR-0032, and a rule applied to itself

An automation review recommended checking in a `.mcp.json` so the toolchain is part of the
clone like everything else. Implementing it would have meant adding **context7** — a network
documentation service — to the repository.

**It was not added.** §4 requires an ADR and Efe's approval for any new technology, and
`CLAUDE.md` had just been written stating that rule. Adding the server on the reasoning that
"it's only dev tooling" is precisely the shortcut §4 exists to prevent, and the fact that the
answer is probably *yes* is what makes the shortcut tempting.

So ADR-0032 proposes it instead, and `.mcp.json` does not exist until the ADR is Accepted —
the same discipline ADR-0029 applied to `ADR-009`.

The ADR is worth reading for three things it had to resolve rather than assert:

| | |
|---|---|
| **The offline objection** | ADR-0007's L0 guarantee constrains the **product at runtime**, not the workstation. A developer reading docs over the network no more breaks it than a browser does. But MASTER_PLAN_v2 §W1 names erosion as this project's characteristic failure mode, so the ADR draws a hard line: no gate, no runtime path, ever |
| **`npx -y` versus ADR-0013** | Unpinned `npx -y <pkg>` resolves latest at every launch — *"a rebuild in three months produces a different system"*, the exact sentence ADR-0013 was written around. Pinned to `@4.0.0` |
| **The API key** | The hosted endpoint takes one. Declined: it buys rate limit, not capability, and ADR-0015 plus a `gate_secrets` scan with no path exclusions make a checked-in credential a live hazard |

Nothing else in 1.3.0. The automation work landed separately in `5bcecb6` and moved no
checksum, because `CLAUDE.md`, `.claude/` and the hooks are outside the checksum set.

### 9.8 Version 1.4.0 — ADR-0032 accepted, and the mechanism it proposed

Efe accepted ADR-0032 on 2026-08-24. §1 calls this MINOR — a pending decision comes into
force — and nothing already in force changed.

**What landed**

| | |
|---|---|
| `.mcp.json` | One entry, `context7`, pinned to `@upstash/context7-mcp@4.0.0` (MIT), with an `x-lionel` block declaring licence, transport, scope and egress. No credential |
| `ci/gates/gate_mcp.py` | `MCP-000` malformed manifest · `MCP-001` unpinned package · `MCP-002` undeclared egress · `MCP-003` literal credential |
| `ci/policy/policy.yaml` | `mcp:` section — pinning shapes, the egress requirement, the credential key pattern and the allowed value forms |
| `repository.required_paths` | `.mcp.json`, so a deleted manifest fails `structure` instead of leaving `gate_mcp` with nothing to check |
| `ci/self_test.sh` | Assertion 17b: strips the version pin and asserts `MCP-001`. 23/23 |
| `.github/workflows/ci.yml` | A 24th job. It runs the gate; it does not install or launch an MCP server, because a gate that depended on one would be ADR-0032's first violation |

**One rule beyond the ADR.** `MCP-000` is not in ADR-0032's Verification list. A malformed
`.mcp.json` is a file the repository owns and a human must fix, so reporting it through
`gate_error` — exit 2, "the gate is broken" — would collapse the two exit codes §5 keeps
apart. It is mechanical necessity, not a new decision, and the ADR's Erratum says so rather
than leaving the discrepancy for a reader to find.

**One rule deliberately not written.** ADR-0032's standing criterion — one entry, and a
second is a decision rather than a routine addition — is a *note* on every run, never a
violation. Blocking the second entry would settle by implementation the question the ADR
left to a reviewer, and a gate that answered it would be claiming to check something it
cannot see.

**Why `.mcp.json` is outside the checksum set.** It is workstation tooling. Inside the set,
every developer-tool version bump would move the architecture checksum, and a checksum that
moves routinely stops carrying information — which is the failure §2 exists to prevent, not
one it should import.

**A stale count, found by hand again.** §3 read *"Self-test 21/21"* through the whole of
1.3.0, when the suite had been 22/22 since 1.2.0. §3 also read *"16 sections"* for a
`policy.yaml` that had 15; adding `mcp` has made that figure accidentally true. Both are the
class ADR-0030's Costs section records as open: `generated-docs` covers only documents that
have a generator, and this one does not. The `doc-claim-auditor` agent mitigates it. It does
not close it.

**The checksum was recorded wrong, and nothing in the pipeline caught it.** Two files in
the set — `ci/policy/policy.yaml` and `ADR-0032` — were rewritten by a Python
`Path.write_text()` call, which translates `
` to `os.linesep` unless you pass
`newline=""`. Both acquired CRLF, and the value first recorded in §2 (`0e8cfbc2…`) was a
property of one Windows working copy. A clean clone would have computed something else — the
1.0.0-era defect, by a different route, thirteen days after `gate_checksum` was written to
prevent it.

`CHECKSUM-001` was green throughout, and could not have been anything else: it compares the
recorded number against one computed from the same contaminated bytes. `git add`'s "CRLF
will be replaced by LF" warning was the only signal, and warnings are not gates.

**`CHECKSUM-004`** now reads every file in the checksum set and fails on a CR. `ci/self_test.sh`
assertion 18b plants CRLF in `artifacts.lock.yaml` and asserts it — 24/24. This is gate work
enforcing a decision §2 already states, which §4 item 3 permits without an ADR.

**And the generated documents were under-reporting.** `CI_Inventory.md` and
`Policy_Gates.md` read the self-test by parsing `expect_violation` lines, plus two inline
cases listed by hand. The third inline case — `gate-coverage`, asserted against a doctored
copy of the suite because the gate needs `--suite` — was never added to that list, so both
documents said `23/23` for a run that reported `24/24`. `generated-docs` could not catch it:
the documents matched what the generator produced, and the generator was wrong. Fixed by
listing all three inline cases, with a comment saying why the two counts can drift apart.

**A bug the self-test caught in its own new assertion.** The first draft of assertion 17b
described the plant as ``"an MCP server pinned to nothing but `npx -y`"``. Backticks inside
a double-quoted bash string are command substitution, so the suite *ran* `npx -y` — a
network fetch, in the offline-first project's own test harness, which then hung. It was
found because the run stopped, not because anything checked for it. `SH-EVAL` and friends
police `ci/` for injection shapes; command substitution in a description string is not one
of them.

---

### 9.9 Version 1.5.0 — ADR-0033, and a working gate removed before it could decide anything

`gate_doc_claims` was written, wired into `ORDER` and `ci.yml`, given a planted violation,
and run. It worked. On its first execution against the 1.4.0 tree it reported

```
CLAIM-001  `CLAUDE.md` claims `20/20, 0 broken`; the pipeline reports gates = 21
           at CLAUDE.md:84
```

— four gates out of date, under a heading reading **"Verify before you claim anything"**, in
the file every session loads first.

Then ADR-0030's Costs section turned out to have already answered the question:

> Closing the rest is a larger question than this ADR answers. It means either generating
> those documents too — which would cost the prose that makes them worth reading — or **a
> narrower check over count-shaped claims, which is a different decision needing its own
> ADR.**

That is exactly what had just been built. The reasoning available at that moment — *"this
only enforces ADR-0030 more completely, which §4 item 3 permits"* — is the reasoning §4
exists to prevent, and it is at its most persuasive when the thing already works and is
already green.

So the implementation was **removed from the repository**, and `ADR-0033` written as
`Proposed` instead. Efe accepted it the same day, and it went back in. The round trip cost
an hour and produced a decision with a record behind it rather than a gate with an
implementer behind it.

**What landed**

| | |
|---|---|
| `ci/gates/gate_doc_claims.py` | `CLAIM-001` count disagrees with measurement · `CLAIM-002` registered document or region missing · `CLAIM-003` exclusion missing `why`/`owner`/`unblocked_by`, or matching nothing |
| `ci/policy/policy.yaml` | `doc_claims:` — seven claim patterns, three registered regions, three out-of-scope documents each with an owner and a route in |
| `ci/self_test.sh` | Assertion 19b plants a wrong count in `CLAUDE.md` and asserts `CLAIM-001`. 25/25 |
| Meta-gate group | Now four rather than three: `checksum`, `generated-docs`, `doc-claims`, `gate-coverage` |

The gate measures rather than remembers: gate, rule, job, ADR and assertion counts come from
`scripts/generate_ci_docs.py`, imported rather than reimplemented — the `_checksum.py`
precedent, for the same reason. It reads a number out of a document only in order to
disagree with it.

**Most numbers here are supposed to be stale**, which is why this is a registry and not a
sweep. §9.x above, the superseded-checksum block and `Phase0_Final_Signoff.md`'s evidence
tables are dated records; ADR-0029 is why they are appended rather than rewritten, and a
gate that flagged them would be arguing with the archive. Three documents are registered.
The other three are named as out of scope, with owners — the gap is now a list rather than
an absence.

**It does not close the class.** A current-state claim in a document nobody registered is
still unchecked, and rule 4 can police the entries that exist but not the entry nobody
wrote. ADR-0033's Costs section says so, and `doc-claim-auditor` still earns its keep on
the judgements a gate cannot make — a risk row reading OPEN next to the gate that closed it
is not arithmetic.

**The third withholding.** Worth naming as a pattern rather than three coincidences:

| | Withheld | Released |
|---|---|---|
| ADR-0029 | `ADR-009`, the errata-shape rule | 1.2.0, on acceptance |
| ADR-0032 | `.mcp.json` and `gate_mcp` | 1.4.0, on acceptance |
| ADR-0033 | `gate_doc_claims` | 1.5.0, on acceptance |

---

### 9.10 Version 1.6.0 — Phase 1 opens, and the first runtime code

`STRUCT-004` forbade `.py` under `src/lionel/` for the whole of Phase 0. It is now
**dormant**: `repository.runtime_code_forbidden_until` is `null`.

**This is not a relaxation, and it is worth being precise about why.** §4 requires an ADR
for any relaxation of a gate, and that rule is doing real work here — the temptation is to
treat "the gate is in my way" as sufficient. It is not what happened. `STRUCT-004` was
always conditional, its condition was G0, and its own fix text names the mechanism:

> Remove them, or sign off G0 and update `repository.runtime_code_forbidden_until` in
> ci/policy/policy.yaml.

G0 was signed off on 2026-08-10 — `Phase0_Final_Signoff.md`, and `Phase1_Entry_Checklist.md`
at 9 of 9 with 0 blocking. The gate was reporting a condition, and the condition is met.
The version still moves, because `ci/policy/policy.yaml` is in the checksum set.

**The rule is dormant rather than deleted.** Setting that value back to a gate name re-arms
the ban, which is the right move if a later phase needs a code freeze; deleting the rule
would mean rewriting the gate to get it back. `structure` keeps its self-test coverage
through `STRUCT-003` (`forbidden_paths`) — assertion 4 now asserts both `architecture`
/`ARCH-001` and `structure`/`STRUCT-003` against the same planted `capabilities/shell`
directory. A gate that has never rejected anything is unproven whichever of its rules
happens to be reachable today.

**What landed under `src/lionel/`**

| | ADR | G1 DoD clause |
|---|---|---|
| `secrets/` — `SecretStr`, `SecretResolver` | ADR-0015 | *"a `secret://` URI resolves and its value redacts in log output"* |
| `platform/process_supervisor.py` | ADR-0014 | *"Job Object kill-tree verified by terminating a parent and confirming zero orphaned children"* |

Both DoD clauses are now executable tests rather than intentions. The kill-tree test spawns
a parent, which spawns a grandchild that would outlive it, shuts the supervisor down, and
asserts the grandchild is gone. **Stopping one level up would have passed against the
implementation ADR-0014 rejected**, so the test deliberately goes two.

That test was then falsified before being trusted: the same fixture, killed with a plain
`Popen.terminate()`, leaves the grandchild running and the detector reports it. The green
test means something because the red one was observed first.

`SecretStr` redacts through `__str__`, `__repr__`, `__format__`, `%`-formatting and a real
`logging` call, and **refuses `==` against a plain `str`** — that comparison's failure
message would print the secret, at the moment something is already going wrong.

**Two decisions taken by not taking them.** `pytest` is not a dependency: ADR-0027 defines
five test *layers* and names no runner, so the suite uses the standard library's
`unittest`. Adding pytest is a §4 dependency decision needing an ADR, and "obviously
needed" is exactly the reasoning §4 exists to catch. Likewise ADR-0014's `dpapi` and `k8s`
secret backends raise `BackendNotAvailable` naming the tier that brings them, rather than
falling back to `env` — a silent downgrade would move a secret from the Windows credential
store into a process listing without anyone deciding to.

**CI gains a `unit-tests` job on Linux *and* Windows.** Not symmetry for its own sake: the
Job Object code path does not execute on Linux at all, so a Linux-only run would report
success for a mechanism it never touched.

`.mcp.json`, `src/`, `tests/` and `CLAUDE.md` remain outside the checksum set. The freeze
governs the architecture; the code written against it is checked by its own tests.

---

### 9.4 If the Proposed ADRs are rejected — *historical, superseded by §9.6*

All three were accepted on 2026-08-11, so this section no longer describes a live
option. Kept because it was the basis on which they were put forward.

They are additive and nothing depends on them.

| Rejected | Effect |
|---|---|
| ADR-0029 | Nothing to unwind — `ADR-009` was deliberately **not** implemented. A gate enforcing an unapproved decision is the error ADR-0030 is about |
| ADR-0030 | Remove `checksum`, `generated-docs`, `gate-coverage` from `ORDER` and from `ci.yml`. The 21 self-test assertions stay — §4 item 3 permits them without an ADR |
| ADR-0031 | Remove `licenses.review_accepted`. `licenses` returns to failing `LIC-002` on the Turkish voice, which is a true statement about an unresolved question |

Any of those is a MINOR bump of its own, not a revert of 1.1.0.

---

*Prepared 2026-08-03. In force 2026-08-10: 1.0.0, extended to 1.1.0, corrected to 1.1.1 — all the same day.
Extended to 1.2.0 and 1.3.0 on 2026-08-11, and to 1.4.0, 1.5.0 and 1.6.0 on 2026-08-24 — the day Phase 1 opened.*
