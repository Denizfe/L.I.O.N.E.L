# ADR-0035: A document that quotes a file is checked against that file

| | |
|---|---|
| Status | **Accepted** — Efe, 2026-08-28. In force. See the Erratum |
| Date | 2026-08-27 |
| Phase | 1 |
| Related | [ADR-0033](ADR-0033-hand-written-claim-checking.md), [ADR-0030](ADR-0030-self-enforcing-ci.md), [ADR-0029](ADR-0029-adr-errata-provision.md) |

## Context

ADR-0033 made count-shaped claims measurable: a document saying *"22 gates"* is now compared
against the pipeline that knows how many there are. Its Costs section named what it did not
close, and the G1 sign-off audit named the same thing again from the other direction:

> Claims about what a file **contains** are unchecked.

It has now cost twice.

**2026-08-24.** `Architecture_Freeze.md` §9.11 recorded five Git Bash hazard rows as
*"recorded in `check_env.sh`"*. Nothing was there. Found by opening the file.

**2026-08-25.** ADR-0034 and §9.14 both quoted the last rule of `config/policy/default.toml`
in a fenced block, and both omitted its `match.any = true` line — then argued from the
absent `match`. The conclusion held; the premise was not in the file. Corrected at
architecture 1.9.1, §9.15. **Twenty-two gates were green through both.**

The second one is the tractable half, and it is the more dangerous half. A prose claim is
read as a summary; a **fenced block is read as the file**. Nobody re-opens the file to check
a block that is right there on the page — that is the entire reason to paste one. A wrong
block is therefore believed more readily than a wrong sentence, and by exactly the readers
who matter: the ones who are reading the document *instead of* the repository.

`gate_checksum` cannot help. It proves the architecture has not drifted from a recorded
value; it has no opinion about whether a document *describing* the architecture describes it
correctly. Those are different claims, and the second is currently checked by nobody.

## Decision

**A fenced block in an architecture document, written in a configuration language, must
appear verbatim in a repository file — or be marked as not being a quote.**

1. **Scope.** Every `docs/decisions/ADR-*.md` and `Architecture_Freeze.md`, expressed as a
   glob rather than a list, so the registry cannot go stale as ADRs are added.
2. **Which blocks.** Fences tagged `toml`, `json`, `yaml`, `yml` or `proto`, with at least
   two non-blank lines. Configuration languages only: a `bash` block is a command someone
   runs, not a quotation, and a single line is an identifier.
3. **The match.** The block's non-blank lines, each right-stripped and collectively
   dedented, must appear as a contiguous run in some non-markdown repository file, itself
   dedented the same way. Contiguous and verbatim: an excerpt may start and stop anywhere,
   and may be indented differently, but may not elide a middle.
4. **The marker.** A block that is deliberately not a quotation — an illustration, a
   proposal, a deliberately wrong example — carries an HTML comment on the line before the
   fence, invisible to every markdown renderer:

   ```text
   <!-- lionel:illustration — why this block is not from the repository -->
   ```

   The reason after the marker is required and may not be empty. A marker with no reason is
   a silently lowered standard, which this repository does not permit anywhere else.
5. **Three rules**, in `gate_doc_quotes.py`:

| | |
|---|---|
| `QUOTE-001` | an unmarked block matching no repository file |
| `QUOTE-002` | a marker carrying no reason |
| `QUOTE-003` | a marker on a block that *does* match — a stale escape hatch, the shape `COV-003` already polices |

**Frozen historical documents are permanently out of scope.** `MASTER_PLAN_v1.md` and
`Phase0_Blockers.md` are preserved verbatim by decision, and their blocks quote a repository
that no longer exists. A gate that asked them to agree with the present would be asking them
to stop being records.

## Consequences

**Measured before deciding.** Run against the repository as it stands, the rule produces
**two findings, and both are true**: the deliberately wrong TOML in `Architecture_Freeze.md`
§9.14 and §9.15, kept because §9.15 is the correction that quotes it. Three other blocks
match a file — one of them only because the match is dedent-normalised, since ADR-0031
quotes `ci/policy/policy.yaml` at a shallower indent than the file uses. The rollout cost is
two markers.

Five blocks is a small corpus, and that is itself worth stating: the exposure is small
today, and the mechanism is being installed while it is cheap rather than after the
document set has grown.

**What this does not close.** Prose claims. *"Five hazard rows are recorded in
`check_env.sh`"* is a sentence, not a fenced block, and this gate would have walked past it.
Half the recorded instances of this defect stay uncaught, and the honest summary is that
this closes the half that can be closed mechanically. Inline single-backtick quotations are
also out of scope: too short to distinguish a quotation from a name.

**The cost of contiguity.** An excerpt that skips a middle section fails, and the remedy is
to split it into two blocks or mark it. This is deliberate: an elision syntax is a place to
hide a changed line, and a gate that accepts *"the parts I chose to show you"* checks
nothing worth checking.

**A marker is a load-bearing statement, not a mute button.** `QUOTE-003` makes it fail once
it stops being true, so a block that later becomes a real quotation cannot keep an
exemption. This is the one property that separates a marker from a suppression comment.

**This ADR is subject to its own rule.** Its only fenced block is tagged `text`, which is
outside the language set, so it needs no marker. That was a design constraint while writing
it, and it is the correct amount of friction: a rule its own ADR could not satisfy would be
a rule nobody else can either.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| **Opt-in: annotate a block with the file it quotes, and check only annotated blocks** | It checks the quotations someone remembered to annotate. The ADR-0034 misquote would have sailed through, because the author who quoted the rule wrongly is exactly the author who would not have annotated it. Presuming a config block *is* a quotation, and making the exception explicit, is the only default that catches the case that has actually happened |
| **Extend `gate_doc_claims` (ADR-0033) rather than add a gate** | The closest call here. Its registry is region-scoped over three named documents; this one is a glob over thirty-five, and its corpus is every file in the repository rather than the pipeline's own measurements. Sharing buys one fewer CI job and costs a gate whose exit-2 takes out two unrelated checks. The usual argument against a second registry — two registries drift — does not apply to a glob, which has nothing to drift from. On acceptance, ADR-0033 gets an Amendment recording that its Costs gap is half closed |
| **Generate the blocks from the files, as `generate_ci_docs.py` does** | Right for a generated document and wrong for an ADR. An Accepted ADR is append-only and dated; a block that silently re-generated would rewrite the record of what was decided, which is the failure ADR-0029 exists to prevent |
| **Widen `doc-claim-auditor` to read quotations** | An agent a human runs when they remember it is what was in place for both recorded instances, and it caught neither at the time. It found the second one eventually, which is worth something — but "eventually, if someone runs it" is the definition of the gap, not a fix for it |
| **Check prose claims too, with a model** | Not reproducible, and a gate that gives a different answer on two runs of the same commit is worse than no gate: it teaches everyone to re-run until it passes |
| **Do nothing; it has only cost twice** | It has cost twice in four days, in the documents that carry the architecture, with every gate green. The second instance was inside the ADR written about the first class of defect |

## Verification

**Withheld until this ADR is Accepted.** `gate_doc_quotes.py` is not in the repository while
this is `Proposed`. `CI_Architecture.md` §7 step 1 puts the ADR before the gate, and
`Architecture_Freeze.md` §4 requires Efe's approval before a new gate exists — shipping a
working gate alongside the proposal would make the approval ceremonial. ADR-0029, ADR-0032,
ADR-0033 and ADR-0034 each practised this withholding; this is the fifth.

The feasibility numbers in Consequences come from a throwaway scan run outside the
repository, not from a gate. They are a measurement, not an implementation.

On acceptance:

| | |
|---|---|
| `ci/gates/gate_doc_quotes.py` | `QUOTE-001`–`QUOTE-003`, built on `_lib.Gate` |
| `ci/policy/policy.yaml` → `doc_quotes` | the glob, the language set, `min_lines`, and the marker token |
| `ci/run_gates.sh` → `ORDER` · `.github/workflows/ci.yml` | steps 4 and 5 of `CI_Architecture.md` §7 |
| `ci/self_test.sh` | a planted block that quotes a real file with one line altered — the defect's actual shape, not a block of nonsense |
| `Architecture_Freeze.md` §9.14, §9.15 | the two markers the rollout requires |
| `ADR-0033` | an Amendment recording that its Costs gap is half closed, and which half |

The planted violation matters more than usual here. A gate proved against a block of
gibberish proves it can tell text apart from a file; the failure this exists to catch is a
block that is *almost* right, differing by one line — which is precisely what §9.15 records.

Gate **G1**, immediately. This defect has no later phase in which it becomes cheaper: every
version adds documents, and every document adds quotations.


## Erratum — 2026-08-28: Accepted; the withholding it describes has been discharged

This ADR was written while `Proposed`, and its Verification section describes that pending
state as ongoing. Efe accepted it on 2026-08-28. The decision is unchanged — what follows
corrects text that has stopped being true, per ADR-0029 rule 2.

The Verification section opened:

> **Withheld until this ADR is Accepted.** `gate_doc_quotes.py` is not in the repository while
> this is `Proposed`. `CI_Architecture.md` §7 step 1 puts the ADR before the gate, and
> `Architecture_Freeze.md` §4 requires Efe's approval before a new gate exists — shipping a
> working gate alongside the proposal would make the approval ceremonial. ADR-0029, ADR-0032,
> ADR-0033 and ADR-0034 each practised this withholding; this is the fifth.

and continued:

> The feasibility numbers in Consequences come from a throwaway scan run outside the
> repository, not from a gate. They are a measurement, not an implementation.

Both were true and are now discharged. As of architecture 1.12.0 the gate exists, is the
**23rd** in `ORDER`, and the numbers in Consequences are no longer a scan's output but the
gate's: five blocks across thirty-six documents, three matching a file, two marked.

Two things the scan could not tell and the implementation settled:

- **The marker is accepted on either of the two lines before the fence**, so that a blank
  line between the comment and the fence — which markdown renders identically — does not
  change whether the rule applies. A check that depends on invisible whitespace is a check
  that fails for reasons nobody can see.
- **Markdown files are excluded from the corpus.** Without that, one document quoting
  another would satisfy the rule, and two documents could agree with each other while both
  disagreed with the file. The corpus is 105 non-markdown files.

All three rules were falsified before being trusted: `QUOTE-001` against the §9.15 block
with one number changed, `QUOTE-002` against a marker stripped of its reason, `QUOTE-003`
against a marker moved onto a block that does match. `ci/self_test.sh` plants the first of
those permanently, and the plant is a real quotation minus one correct line rather than a
block of nonsense — a gate proved against gibberish proves only that it can tell text from
a file.
