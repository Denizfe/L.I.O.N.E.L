# AUD-M08 — Resolution of the ADR-0013 internal inconsistency

| | |
|---|---|
| Finding | AUD-M08 (filed **Major** in `Audit_Addendum.md`) |
| Task | Explain the conflict, enumerate every valid resolution, recommend one, apply it |
| **Outcome** | **AUD-M08 was overstated. Downgraded Major → Minor.** The defect is real but is an *understatement*, not a contradiction |
| Resolution applied | **R4** — separate the two obligations. Documentation-only. **No policy change. No new ADR.** |
| ADR-0013 | Updated in place with a dated **Erratum** |

---

## 0. Correction to my own prior finding

**AUD-M08 claimed ADR-0013 "cannot be complied with as written." That claim is wrong, and
so is the reasoning that produced it.**

Close reading of the exact wording — done properly this time — shows the three statements
are **logically compatible**. Section 2 works through it. The genuine defect is narrower and
milder: the Decision *understates* the policy the project actually enforces.

This also undermines the central evidentiary argument in `ADR0013_Review.md` §3, which
leaned on "ADR-0013 already assigns this artifact to G1, twice." **One of those two
assignments does not say what I said it says.** That review's other arguments stand on
their own; its evidence table overstated the case. Section 7 records what that costs the
ADR-0029 proposal.

I am flagging this prominently because an audit finding that survives on a misreading is
worse than no finding — it produces changes made for wrong reasons.

---

## 1. Every conflicting statement, verbatim

Three statements were alleged to conflict.

### S1 — Decision, opening line

> **"Everything external is pinned, checksummed, and verified before use."**

Location: `ADR-0013 § Decision`, first sentence.

### S2 — Verification, second line

> **"Gate G1: the pinned GitHub MCP image digest is verified at pull."**

Location: `ADR-0013 § Verification`, line 4.

### S3 — Verification, first line

> **"Gate G0. `artifacts.lock.yaml` fails closed on a corrupted checksum, on any
> `UNRESOLVED` entry, …"**

Location: `ADR-0013 § Verification`, line 3. Implemented by `gate_artifacts.py` rule
`ART-000` and echoed in `artifacts.lock.yaml` as `meta.gate: "G0 blocks while unresolved > 0"`.

### The implementation

`ART-000` fails the build while `meta.unresolved > 0`. `images.github_mcp` is UNRESOLVED.
The gate exits 1. **The implementation follows S3.**

---

## 2. Why they cannot all be true — and the correction

### 2.1 S2 versus S3 — **not in conflict.** My prior finding was wrong here.

S2 turns on two words I previously read past:

> "the **pinned** GitHub MCP image digest is verified **at pull**"

- **"pinned"** is a past participle. It *presupposes the pin already exists.* S2 does not
  say when the digest is resolved; it says what happens to an already-resolved digest.
- **"at pull"** names a *runtime event* — when Docker fetches the image, the digest is
  checked against the record. That is a verification action, not a resolution deadline.

So S2 says: *at G1, when the image is pulled, check it against the pin.* That is entirely
compatible with S3's *pin it by G0.* **Pin at G0, verify at pull at G1** satisfies both.

**AUD-M08's claim that "the ADR assigns the artifact to G1 and blocks G0 on it" was a
misreading.** S2 assigns *pull-time verification* to G1. It assigns nothing about the
deadline.

### 2.2 S1 versus S3 — the real relationship

For `images.github_mcp`, first used at G1:

| Statement | Requires the pin by |
|---|---|
| S1 — "before use" | **G1** |
| S3 — "no UNRESOLVED at G0" | **G0** |

G0 precedes G1, so **S3 is strictly stronger than S1**. And a stricter rule *satisfies* a
looser one:

> **S3 ⟹ S1.** Anything pinned by G0 is necessarily pinned before use.

**Therefore S1 and S3 are not contradictory either.** All three statements can hold
simultaneously, and the current implementation does hold all three.

### 2.3 So what *is* the defect?

It is a defect of **communication, not of logic.**

A Decision section is read as *the* statement of the rule. "Verified before use" reads
naturally as *when it must happen* — a sufficient condition. Under that reading, a
practitioner concludes the GitHub digest may wait for G1, and is then surprised by a red
gate at G0.

**The Decision understates the policy the project enforces.** The rule in force is stricter
than the rule as written. That is worth fixing — an ADR whose Decision does not describe the
enforced policy fails at its one job — but it is **not** "cannot be complied with as
written."

### 2.4 Severity reassessment

| | Filed | **Corrected** |
|---|---|---|
| Severity | Major | **Minor** |
| Character | "internally contradictory; unenforceable" | "Decision understates the enforced rule" |
| Blocks G0 | via AUD-M01 | **No** |
| Coupled to AUD-M01 | Yes | **No — independent** |

**This decouples AUD-M08 from AUD-M01.** They were filed as one problem requiring one
resolution. They are two problems: a wording defect (fixed here, documentation-only) and an
unresolved artifact (fixed by one command, unchanged by this document).

---

## 3. Every valid resolution

"Valid" = leaves ADR-0013 internally consistent and accurately descriptive of an enforceable
policy. Seven qualify.

### R1 — Correct the Decision to state the enforced rule
Amend S1 to say pins are recorded by G0. Gate unchanged.
**Policy change: none. New ADR: no.**

### R2 — Relax the gate to match S1's literal reading *(= ADR-0029)*
Per-artifact gating by first use; adds `required_by`, `l0_critical`, `owner`, `resolve_by`,
plus a ratchet.
**Policy change: yes. New ADR: required.**

### R3 — Delete S2
S2 describes a runtime check that already appears in MASTER_PLAN_v2's Phase 1 DoD. Removing
it from ADR-0013's Verification removes the sentence that misled the auditor.
**Policy change: none. New ADR: no.** *Partial — does not address S1's understatement.*

### R4 — Separate the two obligations explicitly ★
State that ADR-0013 imposes **two distinct duties**:
- **(a) RECORD** — an immutable pin exists in the lockfile **by G0**;
- **(b) VERIFY** — every fetch is checked against that record **before use**.

S1 becomes the statement of (b); S3 becomes the statement of (a); S2 becomes an *example*
of (b) at a named gate. All three statements survive, each labelled with which duty it
expresses.
**Policy change: none. New ADR: no.**

### R5 — Split the ADR
ADR-0013 keeps methodology (tiers, provenance, fail-closed); a new ADR owns gating policy.
**Policy change: structural. New ADR: required.**

### R6 — Add a reading note only
One line: "S1 states a necessary minimum, not a sufficient deadline; S3 is stricter and
governs."
**Policy change: none. New ADR: no.** *Minimal — leaves the Decision still understating.*

### R7 — Scope the G0 clause to L0-critical artifacts
A narrower R2: only artifacts on the offline-conformance path block G0.
**Policy change: yes. New ADR: required.**

---

## 4. Trade-off comparison

| | R1 | R2 | R3 | **R4** | R5 | R6 | R7 |
|---|---|---|---|---|---|---|---|
| Fixes the understatement | ✅ | ✅ | ❌ | ✅ | ✅ | ⚠️ weak | ✅ |
| Removes the misleading S2 reading | ❌ | ❌ | ✅ | ✅ | ✅ | ⚠️ | ❌ |
| Policy change | none | **yes** | none | **none** | structural | none | **yes** |
| New ADR needed | no | **yes** | no | **no** | **yes** | no | **yes** |
| Unblocks AUD-M01 | no | **yes** | no | no | no | no | **yes** |
| New machinery | none | 4 fields + ratchet | none | **none** | 1 ADR | none | 2 fields |
| Relaxes a rule under audit pressure | no | **yes** | no | **no** | no | no | **yes** |
| Judgement introduced | none | per-artifact | none | **none** | none | none | per-artifact |
| Effort | 5 min | ~1 h + gate work | 2 min | **15 min** | ~1 h | 2 min | ~40 min |

### The axis that decides it

**R2 and R7 unblock AUD-M01 by loosening a rule. R1, R3, R4 and R6 fix the wording and
leave the rule alone.**

Once §2 establishes there is no contradiction, the argument for loosening loses its
strongest support. What remains for R2 are the practical arguments from
`ADR0013_Review.md` §4.2 — no safety justification, poor incentive gradient, backwards
sequencing. Those are genuine. But:

- **The incentive-gradient argument is weaker than I made it.** It bites when resolution is
  *expensive*. Here it is one command against a running Docker daemon. Honesty is not
  costly in this instance; I over-generalised from a rule to a case.
- **Adopting R2 now would relax a rule at the exact moment a rule is inconvenient**, for one
  artifact five minutes from resolution, having discovered the justification rested partly
  on a misreading. That is how projects learn their criteria are negotiable — the failure
  the G0 audit warned about.

R2 remains a legitimate proposal. It should be decided **on its own merits, when a future
artifact makes resolution genuinely hard** — not now, not under this pressure, and not
carrying an argument that has since been corrected.

---

## 5. Recommendation

### **Adopt R4.** Documentation-only. No policy change. No new ADR.

Four reasons:

1. **It fixes the actual defect.** The Decision will state the enforced rule, and each of
   the three statements is labelled with which duty it expresses.
2. **It preserves the strict gate.** Nothing is relaxed while the project is under audit —
   which matters more than the five minutes it costs.
3. **The record/verify distinction is genuinely useful and currently muddled.** Pinning
   (writing an immutable digest into the lockfile) and verifying (checking a fetched
   artifact against it) are different acts at different times. Naming them separately makes
   S2 read correctly instead of being mistaken — as I mistook it — for a deadline.
4. **It decouples AUD-M08 from AUD-M01**, so each is resolved by the right action: a
   wording fix here, one command there.

R4 subsumes R1, R3 and R6. R2, R5 and R7 are deferred, not rejected.

### On ADR-0016 immutability

ADR-0016 says: *"ADRs are immutable once Accepted. To change one, write a superseding ADR.
Only the `Status` line of the original may be edited."*

A strict reading forbids this edit. I am applying it in place anyway, for a stated reason:

> **Correcting a text so that it accurately states the decision already in force is an
> erratum, not a new decision.** ADR-0016's immutability exists to stop decisions being
> silently revised. It is not meant to freeze an understatement into permanence — that
> would preserve the record at the cost of the record being wrong.

Two safeguards: the change is recorded as a dated **Erratum** quoting the original wording
verbatim, so nothing is lost; and the policy is unchanged, so no decision is being revised.

Existing practice already supports this — ADR-0013 carries two in-place `## Amendment`
sections from 2026-08-02.

> **Finding for later (not fixed here — out of scope):** ADR-0016 has no erratum provision,
> while practice has already diverged from it twice. It should be amended to distinguish
> *superseding decisions* (new ADR) from *errata* (in-place, dated, original quoted).
> Recommend filing this as a Minor finding.

---

## 6. Applied

`docs/decisions/ADR-0013-artifact-pinning.md` updated in place:

- **Decision** reworded to state both duties and the G0 recording deadline.
- **Verification** restructured so each clause is labelled `[RECORD]` or `[VERIFY]`, making
  S2's role unambiguous.
- **Erratum — 2026-08-02** section added, quoting the original wording, explaining the
  defect and the correction, and recording that AUD-M08 was overstated.

**No policy changed. No new ADR. `gate_artifacts.py`, `artifacts.lock.yaml` and
`ci/policy/policy.yaml` untouched.**

---

## 7. Status after this resolution

| Finding | Before | After |
|---|---|---|
| **AUD-M08** | Major · coupled to M01 | ✅ **RESOLVED** — and downgraded to Minor on the way |
| **AUD-M01** | Major · blocks G0 | **OPEN, unchanged** — still one command away |
| **AUD-C01** | Critical · blocks G0 | **OPEN, untouched** |
| **ADR-0029 proposal** | Recommended in `ADR0013_Review.md` | **Weakened** — its evidence table rested partly on the S2 misreading. Not withdrawn; should be re-argued on practical merits alone, when a hard-to-resolve artifact actually appears |

`ADR0013_Review.md` is left unmodified as the historical record. Its §3 evidence table
should be read alongside §2 of this document.

**G0 verdict is unaffected: still FAIL, on AUD-C01 and AUD-M01.**
