# ADR-0030: The pipeline enforces its own invariants

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-10 · **Accepted 2026-08-11** |
| Phase | 0 |
| Related | [ADR-0016](ADR-0016-adr-driven-decisions.md), [ADR-0013](ADR-0013-artifact-pinning.md), [ADR-0027](ADR-0027-testing-strategy.md) |

## Context

Clearing the Phase 1 entry checklist on 2026-08-10 surfaced five defects. They looked
unrelated. They were the same defect five times.

| The repository states | Enforced by | What was actually true |
|---|---|---|
| "Regenerate rather than hand-edit" — in both generated documents | nothing | 16 gates claimed against 17 on disk; 88 rules against 127; **`l0-conformance` absent from the rule catalogue entirely** |
| "Deterministic checksum over the architecture-defining set" — `Architecture_Freeze.md` §2 | nothing | Not reproducible from a clone for eight days. `*.proto` was unpinned in `.gitattributes`, so a Windows clone hashed CRLF and computed a different value from the same commit |
| "A gate that has never rejected anything is unproven" — `CI_Architecture.md` §7 step 6 | nothing | 8 of 17 gates had never rejected anything |
| Windows + Git Bash is the host runtime — ADR-0002, ADR-0014 | nothing | Every gate died with `UnicodeEncodeError` on a cp1252 console, *after* its checks passed, reporting "broken gate" on a clean repository |
| "verify per MODEL_CARD before release" — `artifacts.lock.yaml` | a registered deferral | The MODEL_CARD said CC-BY-NC-SA-4.0, on the only Turkish voice the project has. Nobody had read it |

Every one of these is a rule the project wrote down, believed, cited in other documents —
and never gave a test. The project's own doctrine names the failure exactly:

> A decision with no test is a preference. — `CI_Architecture.md`

**The doctrine had never been applied to itself.** Seventeen gates enforced invariants about
the repository. Zero enforced invariants about the gates, the documents that describe them,
or the freeze that claims to pin them.

This is not a discipline problem, and adding discipline will not fix it. Each of the five
was written by someone doing careful work who believed the rule they were writing. The gap
opens later, silently, in a commit that had a different purpose — and nothing goes red,
because nothing is watching. The audit that found all five ran eight days after the
architecture was frozen. Eight days is fast. It is also five defects.

## Decision

**Every invariant this repository records about itself gets a gate — including invariants
about the gates.**

Three meta-gates, run after the seventeen that check the repository, because a finding in
this class is about the checks above it and reading it first invites fixing the wrong thing.

| Gate | Enforces | Would have caught |
|---|---|---|
| **`checksum`** | `Architecture_Freeze.md` §2's checksum reproduces, and the checksum set has not changed shape | the CRLF defect, on the first Linux run |
| **`generated-docs`** | Every generated document matches what its generator produces | N1 and N2, the day they appeared |
| **`gate-coverage`** | Every gate in `ORDER` has a planted violation in `ci/self_test.sh`, or a registered exemption with an owner and a removal gate | M1, and the eight uncovered gates |

Three properties are load-bearing:

**1. `gate-coverage` counts gates, not assertions.** "10/10 planted violations caught" reads
like coverage and is not. A suite can add its tenth assertion to a gate that already had
three while another has never rejected anything, and the headline number rises. That is
precisely how `l0-conformance` — eight invariants, 24 rules, a network egress guard — sat
unproven behind a green 9/9.

**2. The escape hatch is policed like every other one.** `coverage.exempt` requires `owner`,
`unblocked_by` and `why`, checked by `COV-002`, and `COV-003` rejects an exemption for a
gate that is in fact covered. An exemption mechanism nobody checks becomes the loophole,
which is the usual way this pattern dies. The correct state of that list is empty, and it is.

**3. The meta-gates are themselves covered.** Each plants a violation in `ci/self_test.sh`
and is asserted to catch it. A meta-gate that cannot fail is the exact thing this ADR
exists to prevent, and it would be invisible: nothing else in CI would notice.

**Scope.** This ADR does not say every sentence in every document must be executable. It
applies to invariants the repository asserts **about itself** — its checksum, its generated
artefacts, its own test coverage. Statements about the world (a licence, a latency budget)
are governed by ADR-0013 and ADR-0021.

## Consequences

### Positive

- Three of the five defects now fail the build rather than waiting for an audit. `checksum`
  fails on any unaccompanied change to the architecture; `generated-docs` fails the commit
  that skips regeneration; `gate-coverage` fails the gate added without a test. (The other
  two — the Windows crash and the unread MODEL_CARD — were closed by the `windows-latest`
  job and by reading it. See the last item under Costs for what is **not** closed.)
- `CI_Architecture.md` §7's seven-step procedure becomes checkable at step 6 — the step the
  document itself calls "the one that gets skipped and the one that matters."
- Gate coverage went 9/17 → 20/20 in the course of implementing this, which is the evidence
  for the claim: the rule existed, was believed, and was not being followed.
- The freeze's central claim becomes falsifiable. §2's checksum is now recomputed on every
  push, on Linux, having been first computed on Windows — the boundary it was wrong across.

### Negative / Costs

- Three more gates and three more workflow jobs. Roughly 20 seconds of CI.
- **`checksum` will fail on every legitimate architecture change** until the new value is
  recorded. That is the intended cost, not a defect: Architecture_Freeze.md §5 step 7
  already requires recomputing the checksum and bumping the version, and this gate is what
  makes skipping it impossible rather than merely discouraged.
- `gate-coverage` reads `ci/self_test.sh` as text. A gate covered in a way the parser does
  not recognise needs the `# selftest-covers:` pragma. Explicit by design: inferring
  coverage from "the script mentions this gate" would let a comment count as a test.
- Adding a gate is now genuinely more work — a plant is mandatory, not aspirational. This is
  the point, and it will be irritating exactly when someone is in a hurry, which is when the
  step was being skipped.

- **The class is narrowed, not closed, and the ADR should not be read as claiming otherwise.**
  `generated-docs` covers documents that HAVE a generator — currently two. Every hand-written
  document that asserts a count about this repository is still unenforced prose:
  `CI_Architecture.md` §8, `Phase0_Final_Signoff.md`, `Architecture_Risk_Register.md`, and
  this freeze document itself. That is not hypothetical: within an hour of these gates going
  green, four of those documents were found stale — including risk register rows **R-A05**
  ("silent CI coverage loss: counter ≠ coverage") and **R-A08** ("untested gates fail
  silently"), still marked OPEN while sitting next to the gates that close them, and three
  rows still reading "blocks G0" after G0 was signed off.

  Closing the rest is a larger question than this ADR answers. It means either generating
  those documents too — which would cost the prose that makes them worth reading — or a
  narrower check over count-shaped claims, which is a different decision needing its own
  ADR. **What this ADR buys is that the invariants with a mechanical definition now have a
  mechanism.** The rest still depends on someone noticing, which is exactly the property
  that produced the five defects.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| **Review discipline** | The five defects were written by careful people who believed the rules they were writing. Review catches what a reviewer thinks to check; none of these was in anyone's head at review time |
| **Periodic audit** | This session **was** the periodic audit. It found five, eight days after the freeze, and only because someone happened to re-run a checksum on a different machine. Audits find defects after they have been trusted |
| **A linter over the documentation** | Would catch "this number is stale" only where a number exists. It cannot know the checksum should reproduce, or that a gate needs a test — those are semantic invariants, and each needs its own check |
| **Warnings rather than blocking** | `Policy_Gates.md` already answers this: "A warning is a rule nobody enforces." The defects being fixed here are what happens when a rule is unenforced — a warning tier would reproduce the failure and call it progress |
| **One gate for all three** | They fail for unrelated reasons and are fixed by unrelated people. Collapsing them costs the diagnostic value the exit-code contract in `_lib.py` exists to preserve |
| **Fix the five and stop** | Fixes the instances, leaves the class. The sixth would arrive the same way, and the audit that finds it is not scheduled |

## Verification

Gates **`checksum`**, **`generated-docs`** and **`gate-coverage`**, wired into `ORDER` in
`ci/run_gates.sh` and into `.github/workflows/ci.yml` as independent jobs.

Each is verified by breaking what it guards:

| Break | Expected |
|---|---|
| A file added to `config/**/*.toml` (inside the checksum set) | `CHECKSUM-001` |
| A hand-edited line in `CI_Inventory.md` | `GEN-001` |
| One `expect_violation` line deleted from a copy of the suite | `COV-001` |

All three assertions are in `ci/self_test.sh` and run on every push, on `ubuntu-latest`,
`windows-latest` and under `tr_TR.UTF-8`.

**Standing criterion:** `gate-coverage` reports 20/20 with an empty `coverage.exempt`. A
non-empty exemption list is a gate that has never proven it can reject anything, and it
carries an owner and the gate that removes it.

**This ADR was `Proposed` when written — see the Erratum below.** The gates are implemented and green, but under
Architecture_Freeze.md §5 step 4 the decision is not in force until Efe accepts it. If it is
rejected, the three gates come out of `ORDER` — they are additive and nothing depends on
them.

## Erratum — 2026-08-11

**Nature of change: ERRATUM.** No policy changed. The closing paragraph described this
document's own status, and that status changed when Efe accepted it. The original wording
is preserved below rather than overwritten, per rule 1 of the Decision above.

### What the closing paragraph originally said

> **This ADR is `Proposed`.** The gates are implemented and green, but under Architecture_Freeze.md §5 step 4 the decision is not in force until Efe accepts it. If it is rejected, the three gates come out of `ORDER` — they are additive and nothing depends on them.

### The correction

This ADR was **Accepted on 2026-08-11**. The `Status` row records it; ADR-0016 has always
permitted the Status line to be edited in place, and this erratum exists because the *body*
also asserted the status and the body is append-only.

The rejection path described above is now moot. `checksum`, `generated-docs` and
`gate-coverage` are in force.
