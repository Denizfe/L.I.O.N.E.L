# ADR-0029: Errata, Amendments and Corrections to Accepted ADRs

| | |
|---|---|
| Status | **Proposed** — awaiting Efe's approval (Architecture_Freeze.md §5 step 4) |
| Date | 2026-08-10 |
| Phase | 0 |
| Related | [ADR-0016](ADR-0016-adr-driven-decisions.md), [ADR-0013](ADR-0013-artifact-pinning.md), [ADR-0017](ADR-0017-dual-tts.md) |

## Context

ADR-0016 says:

> ADRs are **immutable once Accepted**. To change one, write a superseding ADR. Only the
> `Status` line of the original may be edited.

The rule is right about the thing it was protecting: a decision that can be quietly
rewritten is not a record, and a project that edits its history cannot answer "why is it
like this?" — which is the entire reason ADR-0016 exists.

**But practice has diverged from it three times, and every divergence was correct.**

| ADR | What happened | Was it a new decision? |
|---|---|---|
| ADR-0013 | Dated `## Erratum` (2026-08-02) plus two `## Amendment` sections | No — the erratum corrected text that misstated a decision already in force |
| ADR-0017 | `## Correction` — `rhasspy/piper-voices` ships only `tr/tr_TR/dfki`; `fettah` and `fahrettin` are training checkpoints, not distributable voices | No — the world was as it was; the ADR described it wrongly |
| ADR-0004 | Superseded by ADR-0010, forward link added | Yes — and correctly handled by the existing rule |

`Architecture_Freeze.md` §6 already documents the three-operation model the project
actually uses — Supersede / Amend / Erratum — and then says of the mismatch:

> **Open governance gap, recorded not fixed:** ADR-0016 has no erratum provision, while
> practice has diverged from it three times. Closing it requires an ADR and is a Phase 1
> item.

This is that ADR.

**Why the gap is not harmless.** A rule that correct practice violates is a rule people
learn to route around, and the routing generalises. Today it produces a well-formed dated
Erratum. The failure mode is the day someone edits a Decision in place and calls it a
correction, because the difference between the two was never written down — only
demonstrated.

Superseding is also the wrong instrument for a typo. Superseding ADR-0013 to fix a
misstated sentence would produce a second ADR whose Context is "the first one had a typo",
and readers would then have to diff two documents to learn one fact. The cost of using the
heavy instrument for light work is not effort; it is that the record gets harder to read,
which is the thing the record exists to be.

## Decision

**An Accepted ADR's Decision is immutable. Three operations may modify the document, and
each is distinguished by what it does to the decision in force.**

| Operation | Changes the decision? | Mechanism |
|---|---|---|
| **Supersede** | **Yes** | New ADR. The original's `Status` line becomes `Superseded by ADR-NNNN` with a forward link. **The original's text is never touched.** |
| **Amend** | **Adds** scope without contradicting | Dated `## Amendment — YYYY-MM-DD` appended to the original. Must not contradict any existing sentence; if it does, it is a supersede. |
| **Erratum** | **No** | Dated `## Erratum — YYYY-MM-DD` appended. Corrects text to state a decision **already in force**. **Must quote the original wording verbatim** before giving the correction. |

Rules that make the distinction checkable rather than a matter of taste:

1. **Errata and Amendments are append-only.** The original body above them is never edited.
   An Erratum that rewrites the sentence it corrects has destroyed the evidence that the
   correction was needed.
2. **An Erratum quotes what it corrects, verbatim.** This is what separates "the text was
   wrong" from "the decision changed": a reader can see both and judge.
3. **An Erratum may not change what is permitted.** If applying it would make something
   newly allowed or newly forbidden, it is a supersede, whatever it is labelled.
4. **Every Erratum and Amendment carries an ISO date** and appears in document order after
   the sections ADR-0016 requires.
5. `## Correction` is accepted as a synonym for `## Erratum` **for ADR-0017 only**, which
   used it before this ADR existed. New documents use `## Erratum`. Renaming ADR-0017's
   section would itself be an in-place edit of an Accepted ADR.

## Consequences

### Positive

- The rule now describes what the project does, so following it and doing the right thing
  stop being different activities.
- The heavy instrument stays heavy. Superseding continues to mean "the decision changed",
  which is only informative while it is not also used for typos.
- Three named operations with different obligations make "which one is this?" a question
  with an answer, asked at write time rather than discovered at review time.
- ADR-0013 and ADR-0017 become conforming documents retroactively, without editing either —
  which is itself the rule working.

### Negative / Costs

- Erratum is the operation most open to abuse: it is the cheapest, and "the text was always
  meant to say this" is available to anyone. Rules 2 and 3 are what make the abuse visible,
  and neither is machine-checkable in full. `ADR-009` below checks the shape; a human still
  has to judge whether a correction is really a correction.
- One more thing to know before writing an ADR.
- Any lightweight path invites reclassifying an awkward supersede as an amendment. The
  mitigation is that amendments must not contradict, and a contradiction is usually obvious
  to a reviewer reading both in one document.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| **Leave ADR-0016 as it is** | Preserves a rule that correct practice already violates three times. The gap does not stay in the ADR system; it teaches that the rules are aspirational |
| **Supersede for every correction** | A superseding ADR whose Context is "the previous one had a typo" makes the record harder to read to keep it formally pure. It also devalues Supersede, which is only informative while it means the decision changed |
| **Allow in-place edits with git as the audit trail** | git shows *that* text changed, never whether the decision changed. Answering "was this a correction or a reversal?" would mean archaeology through diffs — exactly the failure ADR-0016 was written to end |
| **Erratum without the verbatim quote** | Removes the only thing distinguishing an erratum from a rewrite. The quote is the mechanism, not decoration |
| **A separate ERRATA.md** | Splits a decision across two files. A reader of the ADR would have to know to look elsewhere, and would eventually not |

## Verification

Gate **`adr`**, extended with:

- **`ADR-009`** — an `## Erratum` / `## Correction` / `## Amendment` section must carry an
  ISO date in its heading, and an Erratum must contain a blockquote (the verbatim original).
  Shape only: rule 3 is a judgement no gate can make, and claiming otherwise would be worse
  than leaving it to review.
- Existing `ADR-006` continues to check `Status` against the vocabulary, which is what makes
  a Supersede visible.

`ci/self_test.sh` plants an Erratum with no date and asserts `ADR-009`.

**This ADR is `Proposed`.** Per Architecture_Freeze.md §5 step 4 it is not in force until
Efe accepts it, and `ADR-009` is not implemented until then — a gate enforcing an unapproved
decision would be the same category error this ADR is about.
