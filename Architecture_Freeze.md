# Architecture Freeze

| | |
|---|---|
| Architecture version | **1.12.1** |
| Freeze date | **2026-08-10** |
| Tag | **`architecture-1.12.1`** |
| Status | **FROZEN** — Phase 1 open; the freeze governs the architecture, not the code written against it |
| Previous versions | **1.12.0**, **1.11.0**, **1.10.0**, **1.9.1**, **1.9.0**, **1.8.0**, **1.7.0**, **1.6.0**, **1.5.0**, **1.4.0**, **1.3.0**, **1.2.0**, **1.1.1**, **1.1.0**, **1.0.0** — all tagged, all unchanged and still valid |
| Governance | **0 ADRs pending.** ADR-0035 accepted 2026-08-28 and in force; ADR-0034 accepted 2026-08-27 |

> **In force.** 1.1.0 is additive: it adds three decisions and three gates, and changes no
> decision already in force. `architecture-1.0.0` is untouched and remains a valid freeze of
> what it froze. **Clone the tag, not a commit** — §8.3 explains why that distinction
> matters here.
>
> **All 35 ADRs are in force.** ADR-0035 (2026-08-27) was accepted 2026-08-28 and
> implemented in the same version: `gate_doc_quotes` is the 23rd gate. For the day it was
> `Proposed`, the gate it describes was not in the repository. §9.18.
>
> ADR-0034 (2026-08-25) was accepted 2026-08-27 and
> implemented in the same version. It changes `policy-ruleset.schema.json`'s stable surface,
> so §4 required Efe's approval before the change rather than after — and for the two days it
> was `Proposed`, the schema edit it describes was deliberately absent from the repository.
> §9.16. ADR-0033 was accepted 2026-08-24 and implemented in the
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

**1.12.1** — PATCH over 1.12.0: errata only. `Phase1_Final_Signoff.md`'s state block had
gone stale across four versions while the document sat unsigned, in no registry at all. No
decision changed, no ADR added. §9.19.

**1.12.0** — MINOR over 1.11.0: ADR-0035 accepted, so a pending decision comes into force,
which §1 defines as MINOR. A 23rd gate, and no decision already in force changed. §9.18.

**1.11.0** — MINOR over 1.10.0: ADR-0035 added, `Proposed`. No decision in force changed,
and nothing it describes is implemented while it waits — §1's own definition of MINOR, and
the fifth time the implementation has been withheld from its own proposal. §9.17.

**1.10.0** — MINOR over 1.9.1: ADR-0034 accepted, so a pending decision comes into force,
which §1 defines as MINOR. `policy-ruleset.schema.json` goes to 1.1.0 — the first change to a
`stable` contract since the freeze. Nothing already in force changed: the deciding order is
untouched, and a constraint rule can only stop a call, never authorise one. §9.16.

**1.9.1** — PATCH over 1.9.0: errata only. ADR-0034 and §9.14 both misquoted the rule they
are about, omitting its `match.any = true` line and arguing from an absent `match`. The
finding is unchanged and the corrected quote sharpens it; no decision was added or changed.
§9.15.

**1.9.0** — MINOR over 1.8.0: ADR-0034 added, `Proposed`. No decision in force changed,
and nothing it describes is implemented while it waits — §1's own definition of MINOR is
"a new ADR that adds a decision", and this is the first one since 1.3.0 to arrive without
its implementation. §9.14.

**1.8.0** — MINOR over 1.7.0: the four items 1.7.0 left open are closed, and one of them
turned out to be a false claim in §9.11 rather than a deferral. ADR-0002 carries an Erratum
(the root moved to `Projects/`), the seven-row hazard table becomes a registry with four
rows now enforced by gates, `ARCH-017` lands, and the `--live` filesystem check ran on the
host. No ADR was added and no decision changed. §9.12.

**1.7.0** — MINOR over 1.6.0: v1.0's Phase 1 preflight table becomes executable, and the
two statically checkable rows of its Git Bash hazard table become gate rules. No ADR was
added and no decision changed — both tables are decisions MASTER_PLAN_v2's Phase 1 section
already carries forward in prose ("the tooling preflight table, the Git Bash hazard
rules"), and this makes them run. MINOR rather than PATCH because `ci/policy/policy.yaml`
gains a section and two enforcing rules, which is more than correcting text. §9.11 records
what the preflight found on its first run.

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
ARCHITECTURE CHECKSUM                                          architecture 1.12.1
sha256:029c9ee946a4b0cce6937939212b1a600735f56180843d49fa75fa867ba9c54e

  ADRs         35 files   sha256:90d66c463ef899dd426257ee66fdf18f…
  contracts    31 files   sha256:b86796d9e583ad2a8bcd18d03a746589…
  policy        8 files   sha256:3ba2ccb4c1a7817c1521ea5250ffcefe…
  artifacts     1 file    sha256:fc4d6a69230d0b3b5fb25d3f12b71176…
  plan          1 file    sha256:fb9f2e57f26eff1fd50854bc96680f7e…

  76 files hashed
```

Superseded values, kept so the earlier tags stay verifiable:

```
architecture 1.12.0  sha256:2901336ab884ae5d61143a72139822c05f55bb9ba55bf563031a4596cb22b141
                     76 files — ADRs 35 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.11.0  sha256:8a05103d5c9cdaaebbc637415ae70b9dc890edb3706e5274f36c1a2ef6cf5ff5
                     76 files — ADRs 35 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.10.0  sha256:11d2685e902fe03eb4d5636b81b76ab235363915289274e8ee72daebea442ff5
                     75 files — ADRs 34 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.9.1   sha256:37a2bca58042dd851a49d6127e7ffbd916c1f313f0fb49320293da738a4300c0
                     75 files — ADRs 34 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.9.0   sha256:c6da18a0ec65349925824a959d1ca5d82b0266c27b0a55664355d8bd605c9634
                     75 files — ADRs 34 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.8.0   sha256:94d264471f308811487a8e13c8de478b0ed05b7fa53194279b95dfdb7f2c46ea
                     74 files — ADRs 33 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.7.0   sha256:cd24b87f508ebcbbaf7ec588a9a4c1fe8ad9ea6b455f8cb6ffce1bb90eeb6057
                     74 files — ADRs 33 · contracts 31 · policy 8 · artifacts 1 · plan 1
architecture 1.6.0   sha256:e279470a2d42ce319437f5fd16593accf0870aca88c28ebc07ee1ed4e8aed1ba
                     74 files — ADRs 33 · contracts 31 · policy 8 · artifacts 1 · plan 1
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
python3 scripts/architecture_checksum.py --verify sha256:029c9ee946a4b0cce6937939212b1a600735f56180843d49fa75fa867ba9c54e
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
| **Architecture decisions** | **35 ADRs, 0001–0035** — 34 Accepted or Superseded, **1 pending: ADR-0035**, which adds a gate and so waits for Efe |
| **Contracts** | Contract set 1.1.0 — 27 JSON Schemas + 3 protobuf, 5 planes |
| **Capability registry** | 5 capabilities, each declaring `requires_network`, `offline_allowed`, `owner`, `phase`, `trust_level` |
| **Artifact lock** | 13 artifacts, all RESOLVED, tiers A=8 B=2 C=2 D=1 |
| **Tier model** | L0–L3 per ADR-0007; L0 conformance is a blocking gate |
| **Trust model** | 4 levels, monotonically non-increasing within a turn (ADR-0012) |
| **Plane separation** | MCP = control, gRPC = data; no PCM on the control plane (ADR-0006) |
| **Policy** | `ci/policy/policy.yaml` — 21 configuration sections (`doc_quotes` added at 1.12.0), and the count is now measured by `doc-claims` |
| **CI gates** | **23 gates, 149 rules, 27 workflow jobs** — 18 checking the repository, 5 checking the pipeline (ADR-0030, ADR-0033, ADR-0035). Self-test 30/30, gate coverage 23/23 |
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
git clone https://github.com/denizefekaracakaya/L.I.O.N.E.L.git && cd L.I.O.N.E.L
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

### 9.11 Version 1.7.0 — the preflight table runs, and finds a stale root

MASTER_PLAN_v2's Phase 1 section says, of v1.0's environment work: *"Carries forward v1.0's
environment work — the tooling preflight table, the Git Bash hazard rules."* Carried
forward, but not carried anywhere. Both were prose in a superseded plan, and both had been
prose for the whole of Phase 0.

**What 1.7.0 adds**

| | |
|---|---|
| `ci/policy/policy.yaml` → `preflight` | the six-tool table from MASTER_PLAN_v1 §1.1, the four Python packages the gates import, and two opt-in live checks. One registry |
| `scripts/check_env.sh` | runs it. Exit `0` ready · `1` the environment is wrong · `2` the preflight is broken |
| `scripts/_preflight_table.py` | reads the registry and prints TSV. A separate file so two quoting regimes never fight over the same backslashes |
| `SH-BARE-PYTHON`, `SH-MSYS-DOCKER` | the two rows of the seven-row hazard table that can be checked statically |
| `tests/unit/test_preflight.py` | 16 tests over the table's shape and the agreement between the three files |
| `doc-claims` → `policy_sections` | a measured fact behind the claim "N configuration sections" |

**Why the preflight is not a gate.** It describes the *host*, and CI is not the host runtime
(ADR-0002). A gate that went red because a laptop lacked VS Build Tools would be asserting
something true about the wrong computer. So `check_env.sh` is a script an operator runs, and
what CI checks is the table's shape — that every row has a probe naming its own tool, an
extract pattern that finds a version, and a `why` long enough to be a reason.

**What it found on its first run.** The `filesystem` capability is handed exactly one allowed
root and cannot escape it, which is the whole point of the scope note in MASTER_PLAN_v1 §1.4.
That root was `C:/Users/deniz/Desktop/L.I.O.N.E.L`. The repository is in `Projects/`. The
declared root had not existed for as long as anyone can date, and:

```
docker-digests   PASS      artifacts       PASS      l0-conformance  PASS
structure        PASS      contracts       PASS      checksum        PASS
```

Every gate green, because every gate was checking the file's *shape*. The path is a host
fact, and a host fact cannot be checked by anything that runs on a different machine — which
is exactly why nothing was checking it. The same stale root was written in **two** files:
`config/capabilities.registry.json` and `config/lionel.toml` `[project].root`. A check that
had read only the capability registry would have fixed one of them and reported success, so
the preflight scans both, and a test asserts it scans both.

This also settles what "v1.0's Phase 1 DoD in full" can mean. Two of its seven items —
the filesystem server refusing to escape its root, and `get_me` returning Efe's login —
need the network and a credential. They are `live_checks`, run only under `--live`, which
announces itself first. A preflight that quietly dialled out would be the first thing to
break ADR-0007's promise that the ordinary path works with the cable pulled.

**A hard-coded number in a generated document.** `CI_Inventory.md` read *"Runtime code | **0
files** — Phase 0 discipline machine-checked"*. It was a string literal in
`scripts/generate_ci_docs.py`, true while `STRUCT-004` forbade runtime code and false from
the moment 1.6.0 lifted it. `generated-docs` could not catch it: the document matched the
generator, and the generator was wrong — the same shape as the self-test undercount at
1.5.0. It is now measured (`7 files`). A number in a generated document is a hand-written
claim wearing a generated document's authority unless something counts it.

**The blunt rule that caught its own author.** `SH-BARE-PYTHON` is line-based and skips
comments, not strings. Its first finding was a heading inside `check_env.sh` that printed
the words "python packages". The rule was right by its own terms and the cost was one
capital letter; teaching it to parse shell string literals would mean writing a shell
parser, and a parser that is 95% correct on this class is worse than a rule that is blunt
and known to be blunt.

**Not done, and deliberately.** `contracts/mcp/v1/capabilities-registry.schema.json` carries
the same stale `Desktop/` path in its `examples` block. It is illustrative rather than part
of the stable surface — but it is inside a frozen contract, and §4 guards contract files
hardest. Raised rather than edited. Five of the seven hazard rows (`$(pwd -W)` in mounts,
`winpty` for anything that prompts, forward slashes in config values, the WSL2 backend, and
CRLF in scripts — the last already enforced as `SH-CRLF`) describe what an operator types at
a terminal and cannot be checked from a file; they are recorded in `check_env.sh` where the
operator will read them.

> **Corrected at 1.8.0 — this last sentence was not true when it was written.** Nothing was
> recorded in `check_env.sh`. The sentence is left standing rather than edited, because it
> is the record of what 1.7.0 claimed; §9.12 says what was actually there and what made the
> claim true. Two of the five rows were also checkable after all.

Self-test **27/27**. Gates **22/22**, 0 broken. Tests **102**, 1 skipped (a POSIX-only
kill-tree case). `scripts/`, `src/`, `tests/` and `CLAUDE.md` remain outside the checksum
set; the version moves because `ci/policy/policy.yaml`, `config/lionel.toml` and
`config/capabilities.registry.json` are in it.

---

### 9.12 Version 1.8.0 — the four things 1.7.0 left, and a claim that was not true

1.7.0 closed with a list of what it had deliberately not done. Working that list turned up
one item that was not a deferral at all.

**§9.11 said something that was false.** It reported that the five unenforceable hazard rows
were *"recorded in `check_env.sh` where the operator will read them"*, and the 1.7.0 commit
message said the same. They were not in `check_env.sh`. Nothing was. The sentence described
an intention, written at the point in the work where intention and completion feel identical
— and it went into the frozen record.

This is the failure `doc-claims` exists to catch, in the one shape it cannot catch: not a
count, a claim about what a file contains. Nothing checks those. `ADR-0033`'s Costs section
already records that gap; it now has an instance with a date on it.

The correction is not an edit. The claim is made true instead: all seven rows are a registry
in `ci/policy/policy.yaml` → `preflight.hazards`, `check_env.sh` prints them, and
`tests/unit/test_preflight.py` asserts all seven are present, that a row naming an enforcing
rule names one that a gate actually emits, and that the `operator` label stays capped.

**`ARCH-017` — the seventh row stopped being unenforceable.** HAZ-BACKSLASH was labelled
`operator` on the reasoning that config style is a matter of discipline. It is not: config
files are in the repository and portable, so a gate can read them. `ARCH-017` fails any
`"C:\..."` value under `config/`. The failure it prevents is silent by construction — Bash
consumes the backslash as an escape, `C:\Users\deniz` arrives as `C:Usersdeniz`, nothing
errors, and the filesystem capability is scoped to a root that does not exist. Which is very
nearly what had already happened by another route.

Four of seven rows are now gate rules, one is executed by the preflight, and two genuinely
describe what a person types at a terminal. The registry comment caps `operator` at two, and
a test enforces the cap — `operator` is the one label in this repository carrying neither an
owner nor a route to removal, so it is bounded instead.

**`docker --version` was answering the wrong question.** The 1.7.0 preflight reported a green
Docker row on a machine where no daemon was running and nothing could be launched. The CLI
being installed is not the fact anyone needs. `HAZ-DOCKER-BACKEND` now asks the daemon, and
distinguishes three answers: WSL2 (what MASTER_PLAN_v1 §2 requires), another backend, and
unreachable. The `--live` GitHub check consults it first, because "start Docker Desktop" and
"issue a PAT" are different jobs and reporting the first as an authentication failure sends
the reader to debug something that is not broken.

**ADR-0002 carries an Erratum.** Its title and Decision named `Desktop\L.I.O.N.E.L`. The
mechanism is an Erratum rather than a supersession, and the ADR's own Context is what settles
it: the rule applied there was *"The directory that actually exists, and that tooling has
access to"*, which is unchanged and still selects exactly one answer — only the answer moved.
A supersession would be right for a different decision, such as making the root
configurable, and that alternative stays rejected for the reason already recorded.

The ADR also predicted this. Its Context: *"An unresolved path ambiguity is not cosmetic — it
silently produces two divergent trees, half-written config, and MCP filesystem roots that
point at nothing."* That happened, to this ADR, in this repository, with all twenty-two gates
green. Raised as **R-A20**, Moderate, mitigated rather than closed: the residual risk is that
nothing forces the preflight to run, and nothing can — a host fact is not checkable from a
CI runner. The route to closure is a checklist step at each gate sign-off, not a gate.

**The `--live` checks ran, and one of them passed for real.** ADR-0002's Verification clause
— *"The MCP filesystem server starts scoped to this root, lists it successfully, and refuses
a read outside it"* — has been owed since 2026-08-01. On the host:

```
read C:/Users/deniz/Projects/L.I.O.N.E.L/.python-version   ->  "3.11"
read C:/Windows/System32/drivers/etc/hosts                 ->  isError: true
                     Access denied - path outside allowed directories
```

Both halves, because either alone proves nothing: a server that refuses everything also
refuses the escape, and a server that allows everything also lists the root. `github-identity`
did not run — no daemon was reachable — and is reported as a skip naming that reason, not as
a pass and not as a failed login. **It is still owed.**

> **Corrected at §9.13.** Both checks above ran through a shell pipeline that closes stdin
> before the server can answer. The `filesystem` result stands — it was re-run through a real
> client and passed both halves again — but it passed here by luck rather than by design, and
> the GitHub check in the same shape could not have passed for any input.

Self-test **28/28**. Gates **22/22**, 0 broken. Tests **106**, 1 skipped. The contract example
in `capabilities-registry.schema.json` was corrected too: it is illustrative rather than
stable surface, and an example that points somewhere non-existent is a trap for whoever
copies it. `MASTER_PLAN_v1.md` and `Phase0_Blockers.md` keep the old path — frozen historical
records, preserved verbatim by decision.

---

### 9.13 A check that could not pass, and the clause it was hiding

No version. The architecture checksum is unchanged — only `scripts/` and `tests/` moved, and
neither is in the set. Recorded here because of what it found.

**The GitHub live check reported `no login` for every input, valid credentials included.**

It was written as a shell pipeline: `printf '<init><ready><get_me>' | docker run -i …`. That
looks right. The pipe closes the instant `printf` finishes, and a server that reads EOF on
stdin as "the client hung up" tears the session down before writing a byte of response. The
GitHub MCP server does exactly that:

```
session initialized
server session disconnected
server session ended with error: server is closing: EOF
```

No JSON-RPC reached stdout at all, so the branch that looked for a login never had anything
to look at. The check was not strict; it was **inert**, and its failure message —
*"container started but get_me returned no login"* — sent the reader to audit a token that
was fine.

This is worse than an unwritten check. An unwritten check is visibly absent. This one
occupied the slot, reported a specific and plausible diagnosis, and sat on the G1 sign-off
path. It was the last thing standing between the project and a signature.

**The `filesystem` check passed through the same broken pipeline** at 1.8.0, and was recorded
in §9.12 as evidence. It passed because Node answers before its teardown reaches the write —
luck, not design, and it would have gone on being read as proof.

**What replaced it.** `MCPClient` in `scripts/_preflight_table.py`: it holds stdin open until
it has what it asked for, and matches each response **by request id**. Taking the first line
back would pair a request with whatever the server happened to print next, which for a chatty
server is a log line or an unrelated notification. Reads run on a reader thread with a
deadline, because Windows cannot `select()` on a pipe and a blocking `readline()` against a
wedged server hangs the preflight with no output and no way to tell why.

`401`, `403` and silence are now three different reports. "Start Docker Desktop", "issue a
new token" and "the container is broken" are three different jobs, and a check that collapses
them has moved the diagnosis onto the reader at the least convenient moment.

**`npx` is `npx.cmd` on Windows,** and `Popen` without a shell does no PATHEXT resolution —
`FileNotFoundError` from the bare name. `shell=True` was the one-line fix and was not
available: ADR-0011 forbids any path from text to an interpreter, and a preflight that quietly
opened one would be arguing against the thing it checks. `shutil.which()` resolves it and
execution stays argv-only. A test walks the parsed tree for a `shell=` keyword — a substring
search finds the comment explaining why it is not used, which is the same shape as
`SH-BARE-PYTHON` firing on a heading that printed the words "python packages".

**The tests need no network.** A fake server reproduces the two behaviours that mattered: it
exits on EOF, and it interleaves a log line, a notification and a response to a different id
before answering. ADR-0007's guarantee would not survive a suite that needed the network in
order to test the thing that talks to the network.

**v1.0's Phase 1 DoD is closed.** Run on the host, 2026-08-25:

```
filesystem  reads .python-version inside the root
            refuses C:/Windows/System32/drivers/etc/hosts — "path outside allowed directories"
github      get_me -> login denizefekaracakaya, from the digest-pinned container,
            credential resolved through secret://env/GITHUB_PAT
```

ADR-0002's Verification clause — *"The MCP filesystem server starts scoped to this root,
lists it successfully, and refuses a read outside it"* — has been owed since 2026-08-01 and
is now satisfied, on the host, by the ADR's own terms.

Gates **22/22**, 0 broken. Self-test **28/28**. Tests **111**, 1 skipped.

> **Erratum — 2026-08-25: the three-way diagnosis above did not work either.**
>
> The sentence *"401, 403 and silence are now three different reports"* described the
> intent. `check_env.sh` runs under `set -euo pipefail`, and the driver captured the
> check's output with a bare `out="$(...)"`. Under `set -e` that **aborts the script**
> when the command exits non-zero, before the next line can read `$?` — so every branch
> reached by a failure was unreachable. `skip`, `fail` and `broken`: all three. A failing
> live check killed the preflight silently, printing nothing at all, and the only outcome
> `live_check` could ever report was `pass`.
>
> Third time in this script that the bug was *a check that could not fail*. The evidence
> recorded above stands — it came from the passing path, on the host — but it is the only
> path that had ever been exercised. The fix is `if ! out="$(...)"`, which suspends
> `set -e` for the assignment. Verified by forcing the skip path: with no `GITHUB_PAT`
> resolvable, the run now prints `skip github not run — secret://env/GITHUB_PAT does not
> resolve (SecretNotFound)` and continues to its verdict.
>
> A test now flags any bare assignment capturing a helper that signals by exit code, and
> the verdict counts un-run live checks so `PASS` cannot be read as "the DoD clauses were
> verified". Found by a sign-off audit, which is what a sign-off audit is for.

---

### 9.14 Version 1.9.0 — ADR-0034, and a bound that bounds nothing

One ADR, `Proposed`, and none of what it describes. The first ADR since 1.3.0 to arrive
without its implementation, and for the reason §4 exists.

**The finding.** `config/policy/default.toml` ends with:

<!-- lionel:illustration — deliberately NOT from the repository. This is the misquote itself, kept because §9.15 is the correction that quotes it; the file has a `match.any = true` line this block omits -->
```toml
[[rule]]
name = "runaway containment"

max_calls_per_turn = 40
on_exceeded = "halt_turn"
```

`policy-ruleset.schema.json` says rule evaluation is *"Evaluated top to bottom. **FIRST
MATCH WINS.** Falls through to `defaults.decision`"*, and that in a `Match`, *"an absent
condition is a wildcard"*. Under those two sentences the rule above does nothing, in both
directions at once:

- No `match` means it matches everything — but it is last, and `reads are broadly permitted`
  matches any read first. For every tool the policy allows, evaluation stops before it.
- If evaluation did reach it, it "wins" carrying no `decision`, and the contract has no
  account of that state. Falling through to `defaults.decision` is the only sensible
  reading, and that path discards `max_calls_per_turn` too.

The schema permits the rule — `Rule` requires only `name` — so the file validates, and all
twenty-two gates are green. **A reviewer reading the policy sees a bound. A reviewer reading
the contract sees that the bound is unreachable. Both are reading the frozen architecture.**

**The implementation was already ahead of the contract.** `PolicyEngine._decide()` evaluates
constraint-only rules in a pass of their own, before first-match-wins, which makes the
40-call bound real — and which no contract describes. The tests assert it. The argument
*"the code works, the contract is merely imprecise"* was available and is the argument §4
refuses; it is most persuasive once the work is done, which is precisely when it is worth
the least. So the gap is closed by a decision, not by the fact that code shipped.

**Nothing was changed.** `policy-ruleset.schema.json` is `stability: stable` and inside the
checksum set, and §4 requires an ADR *and* Efe's approval before a stable surface moves.
Shipping the schema edit alongside the proposal would make the approval ceremonial. This is
the fourth time the repository has withheld the implementation of its own proposal —
ADR-0029 withheld `ADR-009`, ADR-0032 withheld `.mcp.json`, ADR-0033 withheld
`gate_doc_claims`, and now ADR-0034 withholds the 1.1.0 schema.

The engine's two-pass behaviour stays as it is meanwhile. It is the safer of the two
readings — a bound that applies beats one that does not — and reverting it to match a
contract that may be about to change would be churn toward the more dangerous state. The
ADR says so rather than leaving it to be inferred.

**Why it matters before G4 and not after.** ADR-0008 gives `ToolRouter` a single policy
chokepoint *"so it cannot be bypassed"*. A limit that silently does not apply is a bypass
that leaves nothing in the diff. The failure has no symptom until dispatch is real, and
every symptom afterwards: an API bill at best, an unattended destructive sequence at worst.

Found by the G1 sign-off audit. It is the third defect that audit surfaced whose shape was
**something that could not do its job while appearing to** — after five hazard rows recorded
nowhere, and a live check that could not fail. None of the three was caught by a gate.

`docs/decisions/README.md` records **1 ADR pending**. The version moves because
`docs/decisions/ADR-*.md` and `ci/policy/policy.yaml` are both in the checksum set: 74 files
becomes 75.

---

> **Correction, 2026-08-27 — the TOML quoted above is not what the file contains.** The
> shipped rule carries `match.any = true`; the block in this section and in ADR-0034's
> Context both omitted that line and both argued from "no `match`". §9.15 records the
> correction and what survives it, which is the whole finding.

---

### 9.15 Version 1.9.1 — the fourth instance, inside the ADR about the third

An erratum, no new decision, nothing implemented. PATCH by §1: text corrected to state a
decision already in force.

**What was wrong.** ADR-0034 and §9.14 both quoted the last rule of
`config/policy/default.toml` as:

<!-- lionel:illustration — deliberately NOT from the repository. Quoting the wrong block is the point of this section; the correct one follows below and verifies on its own -->
```toml
[[rule]]
name = "runaway containment"

max_calls_per_turn = 40
on_exceeded = "halt_turn"
```

The file says:

```toml
[[rule]]
name = "runaway containment"
match.any = true
max_calls_per_turn = 40
on_exceeded = "halt_turn"
```

Both then argued *"no `match`, so by the wildcard rule it matches everything"*. The rule has
a `match`. The argument reached the right conclusion through a premise the file does not
support.

**What survives, and why it is now stronger.** The defect is unchanged: the rule carries no
`decision`, it is last, and `reads are broadly permitted` matches any read before evaluation
reaches it. If evaluation did reach it, it "wins" carrying no decision, and the contract has
no account of that state. Nothing in ADR-0034's Decision, Consequences or Alternatives
depended on the missing line.

It is stronger because `match.any` is not an accident of omission. The schema documents it
as *"Matches everything. Use only for a terminal containment rule."* The contract has a
dedicated affordance for precisely this rule shape — and still says nothing about what such
a rule does without a `decision`. The gap was designed around, not stumbled into.

**How it was corrected.** ADR-0034 is `Proposed`, so ADR-0029's append-only rule does not
bind it: a Proposed ADR's body is editable in place, and an Erratum on a decision not yet in
force would be recording a correction to something no one has agreed to. The Context block
was rewritten. §9.14 keeps its text and carries a forward-pointing note, which is the
practice §9.12 established for this document.

**The shape, a fourth time.** The G1 sign-off audit named three defects whose shape was
*something that could not do its job while appearing to*, and named the residual gap that
let all three through: **a claim about what a file contains is checked by nobody.**
`doc-claims` measures count-shaped claims in three registered documents; a quoted code block
is not a count. This is the fourth instance, and it is in the ADR written about the third —
found the same way the other three were, by opening the file the claim was about.

`gate_checksum` does not help here. It proves the architecture has not drifted since the
recorded value; it cannot know that a document *describing* the architecture describes it
wrongly. A gate that verified fenced blocks against the files they quote would have caught
this one, and it needs an ADR — `CI_Architecture.md` §7 step 1 — so it is not in this
version.

The version moves because `docs/decisions/ADR-*.md` is in the checksum set. The file count
stays at 75; only the ADRs group digest changes.

---

### 9.16 Version 1.10.0 — ADR-0034 in force, and the first stable contract to move

Efe accepted ADR-0034 on 2026-08-27. It was `Proposed` for two days, and for those two days
the schema edit it describes was not in the repository — which is the point of the
withholding, and the fourth time this repository has practised it.

**What changed.**

| | |
|---|---|
| `contracts/mcp/v1/policy-ruleset.schema.json` | **1.0.0 → 1.1.0.** The `rule` description states both passes. `$defs.Rule` gains an `anyOf` requiring `decision`, `max_calls_per_turn` or `rate_limit_per_minute` |
| `PolicyEngine._validate()` | refuses a rule carrying neither, naming it. ADR-0034 rule 4 |
| `tests/unit/test_policy_engine.py` | `TestConstraintRules`, five cases |
| `ci/self_test.sh` | 28 → **29** assertions: a decisionless, constraintless rule planted in the schema's own `examples`, asserting `JSON-004` |

**Why MINOR, against a schema whose own note calls this MAJOR.** `compatibility.notes` has
said since 1.0.0 that *"changing rule EVALUATION ORDER is MAJOR even with no schema change —
order determines which rule matches, and a reordering silently alters every decision."* That
sentence is the reason to stop and check rather than to wave the version through.

The deciding order is not changed. Pass 2 is exactly 1.0.0's evaluation, unmodified: top to
bottom, first match wins, `defaults.decision` as the fallthrough. What is added is a pass
that runs before it and **cannot decide** — a constraint rule can stop a call, and can do
nothing else. No ruleset's decisions move. The one ruleset that behaves differently under
1.1.0 is one containing a rule that decides nothing and constrains nothing, which under
1.0.0 did nothing at all; ADR-0034 rule 4 turns that from silence into a load error. The
note now records both passes and this reasoning, so the next reader does not have to
reconstruct it.

**This is the first `stable` contract to change since the 1.0.0 freeze.** That is what §4
exists for, and the sequence it required is the whole substance of what happened here: the
implementation was already ahead of the contract, the argument *"the code works, the contract
is merely imprecise"* was available, and taking it would have meant deciding by having
shipped. The decision was made in writing, by the one person §5 gives it to, and only then
was the contract moved.

**The self-test plant cost three attempts, all to the same trap.** The plant is a Python
block inside a heredoc inside `ci/self_test.sh`, and a `
` written in that block is turned
into a real newline before Python ever sees it — first as an unterminated string, then, after
the fix, inside the comment written to explain the fix. It is the hazard this document has
recorded twice before. The block now uses `chr(10)` and says why in prose containing no
backslash.

**Falsified before trusted.** Disabling the constraint pass in `_decide()` makes
`test_a_constraint_rule_below_an_allowing_rule_still_bounds` fail with `'allow' != 'deny'`.
A bound that passes whether or not the mechanism exists is the shape of the three defects the
G1 sign-off audit found, and this one is about a bound.

One of the five new tests is not about the engine at all: it reads
`config/policy/default.toml` and asserts the last rule still has the shape ADR-0034 argues
from — terminal `match.any`, no `decision`, `max_calls_per_turn = 40`. §9.15 exists because
that claim was wrong once. It is now checked.

The version moves because `contracts/**` and `docs/decisions/ADR-*.md` are both in the
checksum set. 75 files, unchanged in count.

---

### 9.17 Version 1.11.0 — ADR-0035, and the other half of a gap named four times

One ADR, `Proposed`, and none of what it describes. The fifth time this repository has
withheld the implementation of its own proposal, and the second time in three days.

**What it is for.** ADR-0033 closed count-shaped claims. Its Costs section named what it did
not close, and §9.16 named the same thing again from the other end: *"a gate that verified
fenced blocks against the files they quote would have caught this one, and it needs an ADR."*
This is that ADR.

The gap has cost twice, four days apart, with every gate green both times:

| | The claim | What was there |
|---|---|---|
| 2026-08-24 | §9.11: five hazard rows *"recorded in `check_env.sh`"* | nothing |
| 2026-08-25 | ADR-0034 and §9.14 quoted `default.toml`'s last rule | the rule has a `match.any = true` line; both omitted it, and both argued from its absence |

**The decision is deliberately half a fix, and says so.** A fenced block in a configuration
language must appear verbatim in a repository file, or carry a marker saying it is not a
quotation. Prose claims — the first row above — stay uncaught. Half a gap closed
mechanically beats a whole gap closed by intention, and the ADR's Consequences section names
the surviving half rather than leaving it to be discovered a third time.

The reason to take the fenced half first is not that it is easier. **A prose claim is read
as a summary; a fenced block is read as the file.** Nobody re-opens a file to check a block
that is right there on the page — that is the entire reason to paste one. A wrong block is
believed more readily than a wrong sentence, and by the readers who are reading the document
*instead of* the repository.

**Measured before proposing.** A throwaway scan, run outside the repository, found five
config-language blocks of two or more lines across all 34 ADRs and this document. Three
match a file. Two do not — the deliberately wrong TOML in §9.14 and §9.15, which is correct
behaviour, since §9.15 exists to quote what was wrong. **The rollout cost is two markers.**
One of the three matches only because the comparison is dedent-normalised: ADR-0031 quotes
`ci/policy/policy.yaml` at a shallower indent than the file uses, which is a real excerpt
and must not be a finding.

Five blocks is a small corpus, and that is part of the argument. The mechanism is being
installed while it is cheap. Every version adds documents and every document adds
quotations, so there is no later phase in which this gets easier.

**Nothing was changed.** `ci/gates/gate_doc_quotes.py` does not exist, `ci/policy/policy.yaml`
gains no `doc_quotes` section, `ORDER` is unchanged, and the two markers §9.14 and §9.15 will
need are not written. `CI_Architecture.md` §7 step 1 puts the ADR before the gate, and §4
requires Efe's approval before a new gate exists. The gates count stays at **22**.

The version moves because `docs/decisions/ADR-*.md` and `ci/policy/policy.yaml` are both in
the checksum set: 75 files becomes 76.

---

### 9.18 Version 1.12.0 — the 23rd gate, and half a gap closed on purpose

Efe accepted ADR-0035 on 2026-08-28. It was `Proposed` for one day, and `gate_doc_quotes.py`
was not in the repository for that day. Fifth withholding, discharged.

**What changed.**

| | |
|---|---|
| `ci/gates/gate_doc_quotes.py` | **the 23rd gate.** `QUOTE-001` an unmarked config block matching no repository file · `QUOTE-002` a marker with no reason · `QUOTE-003` a marker on a block that does match |
| `ci/policy/policy.yaml` → `doc_quotes` | a glob, the language set, `min_lines: 2`, the marker token. 21 configuration sections |
| `ORDER`, `.github/workflows/ci.yml` | 23 gates, 149 rules, 27 jobs |
| `ci/self_test.sh` | 29 → **30** |
| §9.14, §9.15 | the two markers the rollout needed |
| `ADR-0033` | an Amendment: half its Costs gap is closed, and which half |

**The numbers the ADR predicted are the numbers the gate reports.** Five config-language
blocks of two or more lines across thirty-six documents, three matching a file, two marked —
the two deliberately wrong TOML blocks in §9.14 and §9.15, which is correct behaviour, since
§9.15 exists to quote what was wrong. The feasibility scan was run before the ADR was
written, precisely so the proposal could state a rollout cost rather than promise one.

**Two things the scan could not settle, and the implementation did.**

- The marker is accepted on **either of the two lines** before the fence. Markdown renders a
  comment with and without an intervening blank line identically, and a rule that turned on
  invisible whitespace would fail for reasons nobody can see.
- **Markdown is excluded from the corpus.** Without that, a document quoting another document
  would satisfy the rule, and two documents could agree with each other while both disagreed
  with the file. The corpus is 105 non-markdown files.

**All three rules were falsified before being trusted.** `QUOTE-001` against the §9.15 block
with one number changed; `QUOTE-002` against a marker stripped of its reason; `QUOTE-003`
against a marker moved onto a block that does match — which named
`config/policy/default.toml:41`, the line the whole affair has been about.

**The planted violation is a real quotation minus one correct line**, not a block of
nonsense. A gate proved against gibberish proves only that it can tell text apart from a
file; the failure this exists to catch is a block that is *almost* right. The first attempt
at the plant hit the §9.14 block instead — which is marked, so nothing fired — and the fix
was to anchor the plant on `match.any = true`, the line that appears only in the correct
block. That the wrong target produced silence rather than a false pass is the marker
mechanism working.

**Half the gap stays open, and it is written down rather than implied.** Prose claims are not
fenced blocks. *"Five hazard rows are recorded in `check_env.sh`"* — the 2026-08-24 instance
— would still walk past. ADR-0035's Consequences names it, ADR-0033's Amendment names it, and
this section names it. It is not closed by an intention to be careful, and nobody should read
23 green gates as saying otherwise.

**Where this leaves the meta-gates.** Five of the twenty-three now check the pipeline rather
than the repository: `checksum`, `generated-docs`, `gate-coverage`, `doc-claims`,
`doc-quotes`. ADR-0030's premise was that an invariant this repository records about itself
must have a gate, *including invariants about the gates*. Four of the five exist because
something that was written down turned out not to be true.

The version moves because `docs/decisions/ADR-*.md` and `ci/policy/policy.yaml` are both in
the checksum set. 76 files, unchanged in count.

---

### 9.19 Version 1.12.1 — the sign-off document's own numbers had gone stale

`Phase1_Final_Signoff.md` was prepared on 2026-08-25 against architecture 1.8.0 and then sat
unsigned while the repository moved through 1.9.0, 1.9.1, 1.10.0, 1.11.0 and 1.12.0. Its §5
*"State at sign-off"* block still said 22 gates, 146 rules, 28 self-test assertions, 113
tests, 33 ADRs and a 74-file checksum. **Every one of those was wrong**, and the document
they were in is the one somebody was about to sign.

Nothing it certifies moved — every DoD clause met at 1.8.0 is met now. What went stale is
the block describing the repository around them, which is worse in one specific way: it is
the part a reader checks in order to decide whether to trust the rest.

`doc-claims` was not watching, because the document was in no registry at all — not
registered, and not listed as out of scope either. That is the state ADR-0033's
`out_of_scope` list exists to make impossible: an omission that is implied rather than
written down. It now carries an entry with an owner and a route to removal, and the route is
the signature itself — a signed sign-off must **stop** tracking the present, at which point
it becomes a dated record like `Phase0_Final_Signoff.md` and this exemption becomes that
one's.

Also refreshed: §1's table, which recorded three instances of *something that could not do
its job while appearing to* and is now five, with the two that have since been closed by
machine marked as closed and the three that have not marked as not; §6's row on file-content
claims, now half closed by `doc-quotes`; and §7, which records a re-run of the live preflight
on 2026-08-28 in which the GitHub check **skipped** because no Docker daemon was running.

That skip is worth keeping in the record. The preflight refused to let it read as a pass:
`PASS everything required now is present`, and immediately beneath it, *"PASS above means the
environment is ready, not that those clauses were verified."* Three weeks earlier the same
script printed `ok github verified` for a credential it never managed to send. Clause 5's
evidence remains the witnessed run of 2026-08-25.

PATCH by §1: no ADR added, no decision changed, text corrected to state what is already in
force. Only `ci/policy/policy.yaml` is in the checksum set, so only the policy group digest
moves. 76 files.

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
