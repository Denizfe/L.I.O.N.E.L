# ADR-0033: Count-shaped claims in hand-written documents are measured, not remembered

| | |
|---|---|
| Status | **Accepted** 2026-08-24 — see the Erratum of the same date |
| Date | 2026-08-24 |
| Phase | 1 |
| Related | [ADR-0030](ADR-0030-self-enforcing-ci.md), [ADR-0016](ADR-0016-adr-driven-decisions.md), [ADR-0029](ADR-0029-adr-errata-provision.md) |

## Context

ADR-0030 made the pipeline enforce its own invariants, and its Costs section says plainly
what it did not do:

> **The class is narrowed, not closed, and the ADR should not be read as claiming
> otherwise.** `generated-docs` covers documents that HAVE a generator — currently two.
> Every hand-written document that asserts a count about this repository is still
> unenforced prose […] Closing the rest is a larger question than this ADR answers. It
> means either generating those documents too — which would cost the prose that makes them
> worth reading — or **a narrower check over count-shaped claims, which is a different
> decision needing its own ADR.**

This is that ADR.

The gap has produced a defect on every architecture version since ADR-0030 was accepted.
Not "could produce" — has produced, each one found by a human reading carefully at the
moment they were least likely to:

| Version | Claim | Actual | Found by |
|---|---|---|---|
| 1.2.0 → 1.3.0 | `Phase1_Entry_Checklist.md` header: `architecture 1.1.0` | 1.2.0 | reading, an hour after building the agent that looks for this |
| 1.3.0 | `Architecture_Freeze.md` §3: `Self-test 21/21` | 22/22 since 1.2.0 | reading, during the 1.4.0 bump |
| 1.3.0 | `Architecture_Freeze.md` §3: `policy.yaml — 16 sections` | 15 | reading, during the 1.4.0 bump |
| 1.4.0 | `CI_Inventory.md` / `Policy_Gates.md`: `23/23` | 24/24 | reading, during the 1.4.0 bump |
| 1.4.0 | `CLAUDE.md`: `bash ci/run_gates.sh  # 20/20, 0 broken` | 21/21 | reading, after the 1.4.0 tag |

The last one is the one that settles the question. It sat four gates out of date under a
heading reading **"Verify before you claim anything"**, in the file every session loads
first, in a repository whose stated doctrine is *"a decision with no test is a preference."*

**A stale count is harmless. A document that is wrong about something checkable teaches
readers not to trust the parts that are not checkable** — and those are the parts carrying
the architecture.

### Why the existing mitigations are not enough

`doc-claim-auditor` is a read-only agent that measures ground truth and reports drift. It
works. It is also invoked by a human who remembers to invoke it, which is the property that
produced every row in the table above. `/bump-architecture` step 2 says to run it; step 2
is to this ritual what step 6 was to §7 of `CI_Architecture.md`, and `CI_Architecture.md`
was right about step 6.

## Decision

**A registry names where current-state count claims live. A gate measures whether they are
true. No number inside a registered region is maintained by hand.**

Four rules:

1. **Measured, never remembered.** The gate computes gate count, rule count, workflow-job
   count, ADR count and self-test assertion count from the pipeline itself, and compares.
   It reads a number out of a document only in order to disagree with it.

2. **Registry, not sweep.** Most numbers in this repository are *supposed* to be stale.
   `Architecture_Freeze.md` §9.x, `Phase0_Final_Signoff.md`'s evidence tables and the
   superseded-checksum block are dated records; this project appends corrections rather
   than rewriting history (ADR-0029), and a gate that flagged those would be arguing with
   the archive. So the registry names the regions holding claims presented as *currently
   true*, and nothing else is checked.

3. **One implementation of each fact.** The rule and gate counts come from
   `scripts/generate_ci_docs.py`, imported rather than reimplemented — the `ci/gates/_checksum.py`
   precedent. A second definition of "how many rules are there" would keep producing a
   confident number while meaning something slightly different, and the disagreement would
   surface as one document contradicting another.

4. **The exclusions are policed like every other exemption here.** A line excluded as
   historical carries a `why` and an `owner` and must still match text in the document; a
   document left out of scope carries `why`, `owner` and `unblocked_by`. An exemption with
   neither is not an exemption, it is a silently lowered standard.

### Initial scope

| Registered | Region |
|---|---|
| `CLAUDE.md` | whole file, one historical line excluded |
| `CI_Architecture.md` | §8 Current state |
| `Architecture_Freeze.md` | §3 Frozen scope |

| Out of scope | Why | Unblocked by |
|---|---|---|
| `Phase1_Entry_Checklist.md` | Per-item records and current claims are interleaved — *"Counts when this item landed"* sits two lines above *"Current:"* | Splitting the current-state table into its own section |
| `Phase0_Final_Signoff.md` | A dated audit record. Its numbers describe what was true at sign-off and must not move | Nothing — correct as an exclusion, listed so the omission is visible rather than implied |
| `Architecture_Risk_Register.md` | Status and severity claims, not counts | A rule that can read a risk's closure evidence, if one is ever possible |

**Three documents is deliberately not all of them.** The registry is where coverage grows,
one reviewable policy diff at a time.

## Consequences

### Positive

- The numbers in the three most-cited current-state documents cannot go stale again. Not
  "are unlikely to" — cannot, because nothing writes them by hand.
- A version bump stops depending on someone remembering step 2.
- The registry makes the *uncovered* documents visible. Today the gap is implied by absence;
  after this it is a list with owners.
- It composes with `doc-claim-auditor` rather than replacing it. The agent judges statuses
  ("OPEN" for a closed risk), which no gate can evaluate; the gate handles the arithmetic,
  which no human reliably does.

### Negative / Costs

- **A claim in an unregistered document is still unchecked**, and the registry can go stale
  in the other direction — someone adds a current-state table nobody registers. Rule 4
  polices the entries that exist; it cannot police the entry nobody wrote. This is a real
  residual gap and should not be read as closed.
- **Regex over prose is crude.** `(\d+) gates` will match a sentence that meant something
  else. The mitigation is narrow regions and an explicit historical list, and the failure
  mode is a false positive — loud and cheap — rather than a false negative.
- **It couples `ci/gates/` to `scripts/`.** Rule 3 says why that is the lesser evil, but it
  is a coupling, and a change to `generate_ci_docs.py`'s shape now breaks a gate. The gate
  reports that as exit 2 — a broken gate, not a failing repository.
- **A gate that reads documents will be tempted to grow.** It checks counts. Extending it to
  judge whether prose is *true* would be claiming a capability it does not have, which is
  the failure ADR-0030 warns about in its own Verification section.
- **One more gate to run**, and one more thing to keep green during a bump — at exactly the
  moment the bump is already fiddly.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| **Generate the hand-written documents too** | ADR-0030 named this and it is still wrong. `CLAUDE.md`, `CI_Architecture.md` and `Architecture_Freeze.md` are worth reading *because* they are written; generating them would cost the reasoning and keep only the arithmetic, which is the half already solved |
| **Rely on `doc-claim-auditor`** | It is a good agent and it is invoked by someone who remembers. Five stale claims across three versions is the measurement of how well that works. Keep it for the judgements a gate cannot make |
| **Sweep every document, no registry** | Fails immediately: §9.x and the sign-off evidence tables are *meant* to hold old numbers. A gate that fought the archive would be turned off within a week, and turning a gate off is worse than never adding it |
| **Mark historical regions inline in the documents** | `<!-- claims: historical -->` around every dated section. Puts the burden in the right place in principle, but it means editing the archive to accommodate a checker, and `Architecture_Freeze.md` §9 alone would need a dozen markers |
| **Do nothing; accept it as a known gap** | The honest option, and ADR-0030 took it once already, explicitly and with reasons. What has changed since is the evidence: the gap has cost a defect on every version bump since, and the most recent one was in the file that tells every session how to verify claims |

## Verification

**Not yet implemented — deliberately.** ADR-0030's own Costs section says this needs its own
ADR, so building it first and reasoning about it afterwards would be the exact move this
document exists to interrupt. A working implementation exists and is held back; it is not in
`ci/gates/`, not in `ORDER`, and not in `ci.yml`.

On acceptance:

- **`CLAIM-001`** — a count claim in a registered region disagrees with measurement.
- **`CLAIM-002`** — a registered document or region does not exist. A registry entry
  pointing at a renamed section checks nothing and reports success, which is worse than not
  registering it: the list says the document is covered.
- **`CLAIM-003`** — an exclusion is missing `why` / `owner` / `unblocked_by`, or matches
  nothing any more. The escape hatch is policed exactly as `coverage.exempt`,
  `todo.registry` and `licenses.unresolved_registry` are.
- `ci/self_test.sh` plants a wrong count in a registered region and asserts `CLAIM-001`.
- The gate runs with the meta-gates, last, after the findings about the repository.

**Standing criterion:** the registry only grows. An entry removed from `documents` without
a corresponding `out_of_scope` entry is coverage being deleted rather than declared, and
that is the shape to look for in review.

**What the implementation already demonstrated.** Run against the tree at architecture
1.4.0, it reported one violation on its first execution:

```
✗ CLAIM-001  `CLAUDE.md` claims `20/20, 0 broken`; the pipeline reports gates = 21
    at    CLAUDE.md:84
```

That correction is a plain factual fix and does not wait on this ADR; it landed at 1.5.0.
The mechanism that found it does.

## Erratum — 2026-08-24: Accepted; the withheld implementation has landed

Efe accepted this ADR on the day it was written. Two passages describe it as pending and
have stopped being true. The decision is unchanged; this corrects the text, per ADR-0029
rule 2.

The Verification section opened:

> **Not yet implemented — deliberately.** ADR-0030's own Costs section says this needs its
> own ADR, so building it first and reasoning about it afterwards would be the exact move
> this document exists to interrupt. A working implementation exists and is held back; it is
> not in `ci/gates/`, not in `ORDER`, and not in `ci.yml`.

and closed:

> That correction is a plain factual fix and does not wait on this ADR; it landed at 1.5.0.
> The mechanism that found it does.

Both are discharged. As of architecture 1.5.0:

- `ci/gates/gate_doc_claims.py` implements **`CLAIM-001`**, **`CLAIM-002`** and
  **`CLAIM-003`**, configured from `doc_claims:` in `ci/policy/policy.yaml`.
- It runs with the meta-gates, last, after the findings about the repository — the group is
  now four rather than three.
- `ci/self_test.sh` plants a wrong count in `CLAUDE.md`'s verification block and asserts
  `CLAIM-001`. The suite verifies the plant did not survive, because `CLAUDE.md` is outside
  the architecture checksum set and the closing checksum assertion would not have noticed.
- Registered: `CLAUDE.md` (whole file, one historical line excluded), `CI_Architecture.md`
  §8, `Architecture_Freeze.md` §3. Out of scope with owners: `Phase1_Entry_Checklist.md`,
  `Phase0_Final_Signoff.md`, `Architecture_Risk_Register.md`.

**The withholding was still the right sequence, and it is worth saying so where it will be
read later.** The gate was written, wired, and green before ADR-0030's Costs section was
re-read. The argument for keeping it — *"this only enforces an existing decision more
completely"* — was available, was plausible, and was wrong; §4 exists precisely because that
argument is most persuasive when the work is already done. Removing a working, passing gate
from the repository in order to write this document first is the cost of the rule, and it is
a small one against the alternative, which is a repository whose decisions are made by
whoever implemented fastest.
