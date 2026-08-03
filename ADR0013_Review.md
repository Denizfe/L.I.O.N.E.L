# ADR-0013 Review — should the unresolved GHCR digest block Phase 0 or Phase 1?

| | |
|---|---|
| Question | Does `images.github_mcp` (UNRESOLVED, tier E) block **G0** or **G1**? |
| Method | Independent re-evaluation. The current rule was not assumed correct. |
| Finding | **The current rule is too strict — and it is too strict by accident, not by design.** |
| Verdict | **It should block G1, not G0.** |
| Proposal | Draft **ADR-0029** in §6, superseding ADR-0013's Verification clause |
| Implementation changed | **None.** This is a review. |

---

## 1. Verdict up front

**The GHCR digest should block Phase 1 (G1). It should not block Phase 0 (G0).**

This is not a judgement call about acceptable risk. **ADR-0013 already says so, twice, and
then contradicts itself in a clause added later.** Four independent documents in this
repository assign the artifact to G1; one sentence pulls it to G0.

The correct resolution is not to waive the rule for this instance. It is to fix the rule so
it matches the decision it was written to implement — and, in doing so, make it *stricter*
in three dimensions where it is currently silent.

---

## 2. What ADR-0013 actually says

### The Decision (verbatim)

> **Everything external is pinned, checksummed, and verified before use.**

The operative words are **"before use."** Not "before G0". Not "before anything is built".
Before *use*.

### The Verification (verbatim, both lines)

> Gate **G0**. `artifacts.lock.yaml` **fails closed** on a corrupted checksum, on any
> `UNRESOLVED` entry, on any hash lacking a verification tier, method or retrieval date, on
> any UNRESOLVED entry without a classified blocker and a reproducible alternative, and on
> `[meta]` drift.
>
> Gate **G1**: the pinned GitHub MCP image digest is verified at pull.

**These two sentences are in the same section of the same ADR and they disagree.**

The second sentence assigns the GitHub MCP digest to **G1** by name. The first blocks
**G0** on any unresolved entry, which necessarily includes that digest. The ADR
simultaneously says this artifact belongs to G1 and that it blocks G0.

---

## 3. The decisive finding: an internal contradiction, not a deliberate strictness

I expected to be weighing "strict but defensible" against "pragmatic but erosive." That is
not the situation. The evidence:

| # | Source | What it says | Assigns to |
|---|---|---|---|
| 1 | ADR-0013 **Decision** | "verified **before use**" | use-time |
| 2 | ADR-0013 **Verification**, line 2 | "Gate **G1**: the pinned GitHub MCP image digest is verified at pull" | **G1** |
| 3 | MASTER_PLAN_v2 **Phase 1 DoD** | "**pinned GitHub MCP image digest verified**" | **G1** |
| 4 | MASTER_PLAN_v2 **Phase 1** scope | "Carries forward … filesystem and **GitHub MCP** — onto the new spine" | **G1** |
| 5 | MASTER_PLAN_v2 **Phase 0 DoD** | "`artifacts.lock.toml` **fails closed on a corrupted checksum**" | mechanism, not coverage |
| 6 | MASTER_PLAN_v2 **G0 gate summary** | "Contracts exist; L0 CI gate is wired" | no artifact claim |
| 7 | ADR-0013 **Verification**, line 1 | "on any `UNRESOLVED` entry" | **G0** |

**Six of seven point to G1 or to no G0 requirement at all. One points to G0.**

Two further observations that settle it:

**The G0 DoD does not require full resolution.** Searching the Phase 0 section of
MASTER_PLAN_v2 for "unresolved", "every artifact" or "all artifacts" returns **zero
matches**. What G0 requires is that the *mechanism* fails closed on a corrupted checksum —
that the lockfile machinery works. It does. That has been demonstrated.

**The "any UNRESOLVED entry" clause is later drift.** It was added to ADR-0013's
Verification during the artifact-resolution work, alongside the verification-tier
amendment. It was written as an implementation note for the gate, and it landed stricter
than the Decision it implements — while sitting one line above the G1 assignment it
contradicts.

> ADR-0016 makes ADRs immutable once Accepted precisely so that this kind of drift is
> visible and correctable. This is that mechanism working.

---

## 4. Independent evaluation

I steelmanned the strict rule before concluding. It has real arguments.

### 4.1 The case FOR blocking at G0

**S1 — Zero is unambiguous.** "No unresolved artifacts" requires no judgement, no
classification, no per-artifact debate. Any threshold above zero invites the question "is
*this* one really needed yet?", and that question is where motivated reasoning enters.

**S2 — Deferral compounds.** Once an artifact can be deferred by naming a later gate, the
pressure is always to name a later gate. This project already defers to gates *without
dates* (audit finding AUD-M09), so the mechanism for unbounded slip is demonstrably present.

**S3 — G0 is the only moment the whole set is in view.** Later gates are narrow. Discipline
applied while the full artifact inventory is under review is cheaper than retrofitting it
across six phases.

**S4 — Waiving teaches that criteria are negotiable.** The G0 audit made exactly this point,
and it is correct. A project whose stated criteria bend when a finding looks small has
criteria that describe intentions rather than constraints.

### 4.2 The case AGAINST blocking at G0

**W1 — The rule enforces something with no safety justification.** An artifact that is
unresolved *and unused* is not a risk. An artifact that is unresolved and *about to be
used* is. G0 uses **zero** artifacts. The rule demands 100% resolution at the one phase
where 0% are consumed.

**W2 — It contradicts the Decision it implements.** §3. "Before use" and "before G0" are
different rules, and the ADR states the first and enforces the second.

**W3 — The sequencing is backwards, not merely early.** Phase 1 is where the GitHub MCP
capability is wired, with Docker Desktop running. **That is the natural moment to resolve
its digest** — `docker buildx imagetools inspect`, one command, in front of the person
setting it up. Blocking G0 means: you may not begin Phase 1 until you resolve an artifact
you need *at the end of* Phase 1. That is out of order, not just conservative.

**W4 — It inverts the incentive the ADR exists to create.** ADR-0013's sharpest rule is
*"never invent a hash — a fabricated checksum is strictly worse than an absent one,
because it looks verified."* That rule depends on honesty being cheap. Under the current
rule, recording `UNRESOLVED` honestly blocks the entire gate, while pasting a plausible
64-hex string turns the build green and, as the audit proved (probe 11), **would not be
detected**.

The strict rule makes honesty maximally expensive and dishonesty undetectable. That is a
badly shaped incentive gradient sitting directly on top of the project's most important
supply-chain rule.

**W5 — Artifacts have genuinely different first-use gates.**

| Artifact | First used | On the L0 path? |
|---|---|---|
| `images.qdrant` | G2 | yes |
| `models.embedding` | G2 | yes |
| whisper · kokoro · piper · wakeword · whisper.cpp | G6 | yes |
| **`images.github_mcp`** | **G1** | **no** — `requires_network: true`, excluded at L0 by ADR-0007 |

A single "all at G0" rule is uniformly earlier than any actual need, and treats an artifact
explicitly excluded from the offline guarantee identically to the STT model that guarantee
depends on.

### 4.3 Weighing

S1 and S2 are the serious objections, and they are objections to *sloppy* relaxation —
"defer when convenient." They are not objections to a rule that ties resolution to
first-use *and adds machinery to prevent accumulation*.

S3 is satisfied: the full inventory **is** under review now, all thirteen artifacts are
enumerated, and twelve are resolved. That work is done and is not undone by this proposal.

S4 is the one that matters most, and it is answered by *how* the change is made. There are
two ways to stop a rule from blocking: **waive the instance**, or **amend the rule through
review**. The first is corrosive. The second is the mechanism ADR-0016 prescribes. This
review takes the second path and produces a superseding ADR for approval.

---

## 5. Verdict

**The current rule is too strict.** Specifically, it enforces the wrong invariant.

| G0 should guarantee | Currently enforced? |
|---|---|
| The lockfile schema is complete and correct | ✅ |
| Every artifact the project will use is enumerated | ✅ |
| Every hash carries tier, provenance, method, retrieval date | ✅ |
| The mechanism fails closed on a corrupted checksum | ✅ |
| Every unresolved artifact has a plan, an owner, and a date | ⚠️ partial — no owner, no date |
| **Nothing on the L0 critical path is unresolved** | ❌ not expressed at all |
| ~~Every artifact needed at any future gate is resolved now~~ | ✅ — **and this one has no safety justification** |

The rule over-enforces the last line and *under*-enforces the two above it. The proposal in
§6 corrects both directions.

---

## 6. Proposed ADR-0029 (draft — requires Efe's approval)

> **Status:** Proposed. Supersedes the G0 clause of ADR-0013's Verification section.
> ADR-0013's Decision, tier model, and provenance requirements are **unchanged**.

### Decision

**An artifact must be resolved before the gate at which it is first used** — restoring
ADR-0013's own "verified before use" principle as the operative rule.

Three mandatory new fields per artifact:

| Field | Type | Meaning |
|---|---|---|
| `required_by` | gate id | The gate at which this artifact is first consumed |
| `l0_critical` | boolean | Whether it lies on the L0 offline-conformance path |
| `owner` | module | Accountable for resolution (on UNRESOLVED entries) |
| `resolve_by` | ISO date | Calendar deadline, **in addition to** the gate |

### Blocking rules

| Condition | Blocks |
|---|---|
| `l0_critical: true` **and** unresolved | **G0** — no exception |
| Unresolved at or after its `required_by` gate | **That gate** |
| Unresolved before its `required_by` gate, **with** owner + `resolve_by` + a reproducible alternative | **Nothing** — but counted |
| Unresolved with any of owner / `resolve_by` / alternative missing | **Every gate** |
| `required_by` absent | **Every gate** |

### The ratchet

`meta.unresolved` **may never increase between gates.** The count at each gate is recorded
in `meta.unresolved_at_gate` and compared. Deferral cannot accumulate: resolving one
artifact does not create budget to defer another.

### Moving a deadline

`required_by` and `resolve_by` may be moved **later only by a superseding ADR.** Moving a
deadline must cost as much as the deferral it enables, or the fields are decoration.

### G0's artifact criterion becomes

1. Every artifact enumerated with complete metadata
2. Every resolved hash carrying tier, provenance, method, retrieval date
3. **Zero `l0_critical` artifacts unresolved**
4. Every unresolved artifact carrying `required_by`, `owner`, `resolve_by`, and a
   reproducible alternative
5. The gate demonstrably failing closed on a corrupted checksum
6. `meta` counts matching reality

---

## 7. What this does NOT relax

Stated explicitly, because a revision that only loosens is a retreat.

The proposal is **stricter than the current rule in four ways**:

1. **`l0_critical` is a new concept.** Today the rule has no notion of the L0 path — the
   STT model the offline guarantee depends on and a network-only GitHub image are treated
   identically. Under ADR-0029, anything on the L0 path blocks **G0** with no deferral
   possible. That is a *tightening* on the artifacts that matter most.
2. **`owner` and `resolve_by` become mandatory.** Today an unresolved artifact needs
   neither — a weaker standard than this project applies to a TODO comment (audit finding
   AUD-M07). ADR-0029 closes that.
3. **The ratchet is new.** Nothing today prevents unresolved artifacts accumulating.
4. **`required_by` becomes a required field on every artifact**, resolved or not, forcing
   the first-use question to be answered once, in writing, and reviewed.

Unchanged: never invent a hash · never substitute one artifact's digest for another's ·
pin the source you actually fetch from · verification tiers A–E · fail closed on mismatch ·
licence per artifact.

**One thing is relaxed, precisely:** an artifact not needed until a later gate, carrying a
complete resolution plan, no longer blocks earlier gates.

---

## 8. Applied to today's lockfile

| Artifact | `required_by` | `l0_critical` | Status | Blocks |
|---|---|---|---|---|
| `images.github_mcp` | **G1** | **false** | UNRESOLVED | **G1** — not G0 |
| `images.qdrant` | G2 | true | RESOLVED | — |
| `models.embedding` | G2 | true | RESOLVED | — |
| whisper ×2 · kokoro ×2 · piper ×2 · wake ×3 · whisper.cpp | G6 | true | RESOLVED | — |

**Result: G0's artifact criterion is met. G1 inherits one blocker with an owner, a
command, and a date.**

Missing under the proposal and requiring one edit each: `owner: platform` and a
`resolve_by` date on the `github_mcp` entry. Both are audit finding AUD-M07, which this
proposal closes as a side effect.

Two related items become cleanly resolvable rather than awkward:

- **AUD-M03** — the invalid image reference in `config/capabilities.registry.json` is
  correctly handled by `enabled: false` until G1, which the proposal makes coherent rather
  than an exception.
- **The G1 DoD already says** "pinned GitHub MCP image digest verified", so no plan change
  is needed. The proposal makes ADR-0013 agree with a DoD that already exists.

---

## 9. Risks of the revision, and mitigations

Honest accounting. A proposal that lists no downsides has not been thought about.

| # | Risk | Mitigation | Residual |
|---|---|---|---|
| R1 | `required_by` set to a distant gate to dodge work | Moving it later needs a superseding ADR; the ratchet caps the total; `resolve_by` makes drift visible on a calendar | Low |
| R2 | Judgement enters where there was none (S1) | `required_by` is checkable against the plan's phase deliverables. A reviewer can verify it in one lookup — this is not open-ended judgement | Low–Med |
| R3 | `l0_critical` mis-set to `false` to dodge the G0 block | It is a single boolean tied to `requires_network` and tier config, both independently checkable. Recommend the gate cross-check it against `requires_network` | Low |
| R4 | Amending under pressure normalises amending under pressure (S4) | This is a reviewed superseding ADR, not a waiver — the ADR-0016 mechanism working. The record shows the reasoning and the rejected alternative | **Med — the honest residual** |
| R5 | More fields, more surface for drift | All four are machine-checked; a missing one blocks every gate | Low |

**R4 deserves to be named plainly.** The G0 auditor — correctly — warned that waiving a
self-declared criterion teaches that criteria are negotiable. Amending a rule *is*
different from waiving an instance, and the difference is review. But the difference is
only real if the amendment would have been proposed even had it been inconvenient.

The test I applied: **would this revision be worth making if the GHCR digest were already
resolved?** Yes — `l0_critical`, `owner`, `resolve_by` and the ratchet are improvements on
their own merits, and two of them close an existing audit finding. That is the check that
distinguishes a principled amendment from a convenient one.

---

## 10. If instead the strict rule is kept

The alternative is legitimate and I would not argue against it hard. Keeping "zero
unresolved at G0" costs one command and buys absolute simplicity. If Efe prefers it, then
**ADR-0013 must still be edited**, because the contradiction in §3 is real either way:

- Delete "Gate **G1**: the pinned GitHub MCP image digest is verified at pull" from the
  Verification section, and
- Amend the Decision from "verified **before use**" to "resolved **before G0**", so the
  principle matches the mechanism.

**What is not acceptable is leaving both sentences in place.** An ADR that assigns an
artifact to G1 and blocks G0 on it cannot be complied with as written, and an unenforceable
rule is worse than either alternative — it trains people to read past the parts that do not
make sense.

---

## 11. Recommendation

**Adopt ADR-0029.** The GHCR digest blocks **G1**, not G0.

Two things follow, neither of which I have done:

1. ADR-0029 requires Efe's approval before it takes effect.
2. `gate_artifacts.py` and `artifacts.lock.yaml` would need the four new fields. **No
   implementation was changed by this review.**

If adopted, G0's artifact criterion is satisfied and the G0 audit's blocker **AUD-M01**
closes — not by waiver, but because the rule it violated was found to be inconsistent with
its own Decision and was corrected through review.

**AUD-C01 (repository not under version control; CI has never executed) is unaffected and
remains a G0 blocker.**
