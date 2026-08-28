# ADR-0037: A tombstone is a MemoryRecord, and the contract has no shape for one

| | |
|---|---|
| Status | **Accepted** — Efe, 2026-08-28. In force. See the Erratum |
| Date | 2026-08-28 |
| Phase | 2 |
| Related | [ADR-0010](ADR-0010-memory-service.md), [ADR-0034](ADR-0034-constraint-only-policy-rules.md), [ADR-0029](ADR-0029-adr-errata-provision.md) |

## Context

`contracts/events/v1/memory-record.schema.json` requires `text`, with `minLength: 1`. The
same schema also carries:

> `redacted` — ADR-0010's `forget(id)`. A redacted record is excluded from retrieval and
> **its text is cleared**, but the tombstone remains so consolidation cannot resurrect the
> content from an earlier summary.

Those two sentences cannot both hold. A record with `redacted: true` has no text, and a
record with no text is not a valid `MemoryRecord`. **The contract describes a state it
forbids.**

It is not a corner. `memory.forget` is required by
`contracts/mcp/v1/memory-service.schema.json` from 1.0.0 and, in that schema's own words,
*"MUST NOT become optional"* — so every conforming implementation produces records the
record contract rejects, on the one path both schemas call mandatory.

**Nothing noticed for twenty-six days**, because until 2026-08-28 the Memory Service did
not exist. The two schemas were frozen on 2026-08-02 and described an interface with no
implementation: a contract nothing tests against reality cannot be wrong, and this one was
not wrong so much as unexercised. `tests/contract/test_memory_contract.py`, the first
consumer either schema has ever had, found it on its first run.

**The schema does ship a redacted example, and it resolves the tension a third way.** Its
second example carries `"redacted": true` with `"text": "[redacted]"` — a placeholder, ten
characters long, which satisfies `minLength: 1` and validates cleanly. So the `jsonschema`
gate is green and always was: it validates each schema against its metaschema and each
schema's own examples, and both pass.

That makes this sharper rather than softer. **Three places in one frozen contract describe
three different states.** The field description says the text is cleared; the example keeps a
placeholder string; `minLength: 1` permits only the second. The implementation followed the
description, because a description is what an implementer reads. Nothing in the repository
can notice a schema whose prose and whose example disagree — the gate compares an example to
its schema, never to the sentence next to it.

## Decision

**`text` becomes `minLength: 0` when `redacted` is `true`, expressed as a conditional
rather than by relaxing the field.**

1. `MemoryRecord` gains an `if/then`: when `redacted` is `true`, `text` may be the empty
   string. When it is `false` or absent, `minLength: 1` stands unchanged.
2. `redacted_at` becomes **required** whenever `redacted` is `true`. A tombstone with no
   date cannot be ordered against a consolidation run, which is the one question anyone
   asks it.
3. `memory-record.schema.json` goes to **1.1.0**. Every record valid under 1.0.0 stays
   valid; the only instances that change status are tombstones, which were invalid and are
   now valid — a widening, not a narrowing.
4. The existing redacted example is **corrected**, not added: `"text": "[redacted]"` becomes
   `""`. It is the visible half of this change, and it reverses what the schema's author
   wrote — deliberately, and recorded here so the reversal is a decision rather than a
   tidy-up.

**Relaxing `minLength` to 0 unconditionally is rejected below.** A live memory with empty
text is a bug, and the point of the conditional is that it stays one.

## Consequences

**What gets better.** `forget` produces a record the architecture can describe. At L1 the
Memory Service moves out of process ([ADR-0020](ADR-0020-kubernetes-cloud-portable.md)) and
records cross a wire where they are validated; today the service is in-process and nothing
serialises a tombstone, so this is the last moment it costs nothing.

**What this costs.**

- `MemoryRecord` stops being a single flat shape. A consumer that pattern-matches on it now
  has two cases, and the second one has no text — which is the truth, but it is a truth
  every consumer has to hold.
- A conditional schema is harder to read than a field. That is the trade: the alternative
  is a schema that permits an empty-texted live record, and the failure it would hide is a
  memory that silently recalls nothing.

**What is deliberately not decided here.** Whether a tombstone should retain its `tags`,
`provenance` and `importance` at all, or be reduced to id-and-date. Keeping them is what the
implementation does today and it is what makes an audit of "what was forgotten and when"
possible; reducing them is a privacy argument that deserves its own hearing rather than
being settled inside an erratum about `minLength`.

**Not decided here either:** whether `redacted` should have been `required` from the start.
It has a default of `false`, so every existing record is well-defined without it, and
changing that is a narrowing this ADR does not need.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| **Relax `text` to `minLength: 0` unconditionally** | One-line change, and it makes an empty-texted *live* record valid. That record recalls nothing, matches nothing, and looks exactly like a working memory in every listing. The conditional costs four lines and keeps that a schema error |
| **Delete the record instead of tombstoning** | The schema's own reason forbids it: the tombstone exists "so consolidation cannot resurrect the content from an earlier summary". A delete makes `forget` true until the next consolidation run, which is the worst of both — it looks forgotten and is not |
| **Keep a placeholder string, e.g. `"[redacted]"`** | **What the shipped example already does**, so this is the incumbent rather than a hypothetical, and it is the closest call in the table. Rejected because it makes `redacted` a second-class discriminator: `redacted: true` already says the record is a tombstone, and a magic string means every consumer must know both, agree on the spelling, and handle a live record that legitimately contains the word. The empty string cannot be mistaken for content. *(An earlier draft of this table rejected the placeholder on the grounds that it would be embedded and searchable. That was wrong — `forget` clears the vector and recall excludes redacted records, so it is neither. The reason above is the one that survives.)* |
| **Say nothing; the implementation is in-process and nothing serialises it** | The argument ADR-0034 was written to refuse, in the same shape: the code works, the contract is merely imprecise. It is most persuasive now, when it costs nothing to be wrong, and worthless at L1 when a second implementation reads the same schema and reaches a different conclusion |
| **Widen the record schema at G4, when memory first crosses a wire** | The gap is known now and free to fix now. Deferring a known contradiction in a `stable` contract to the phase that trips over it is how ADR-0034's bound came to bound nothing for four weeks |

## Verification

**Withheld until this ADR is Accepted.** `memory-record.schema.json` is `stability: stable`
and inside the architecture checksum set, and `Architecture_Freeze.md` §4 requires an ADR
*and* Efe's approval before a stable surface moves. The schema is unchanged while this is
`Proposed`. ADR-0029, ADR-0032, ADR-0033, ADR-0034, ADR-0035 and ADR-0036 each practised
this withholding; this is the seventh.

The current behaviour is pinned rather than left drifting.
`tests/contract/test_memory_contract.py::test_a_redacted_record_still_validates` asserts
that a tombstone **does** fail validation today, and says why in the assertion message: if
it stops failing, the schema changed and the tombstone shape needs a decision rather than a
silent pass. That test is the thing that has to be rewritten on acceptance, which is the
right amount of friction.

On acceptance:

| | |
|---|---|
| `memory-record.schema.json` → 1.1.0 | the `if/then` on `redacted`; `redacted_at` required alongside it; `compatibility.minor_changes` records why this is a widening |
| its `examples` | the redacted example's `"[redacted]"` becomes `""`, so `JSON-004` exercises the shape the description has always specified |
| `test_memory_contract.py` | the pinning test inverts: a tombstone must now validate, and a live record with empty text must not |
| `ci/self_test.sh` | a planted live record with empty text, asserting `JSON-004` |

Gate **G2**, alongside the `forget(id)` clause it belongs to.

## Erratum — 2026-08-28: Accepted; the withholding is discharged, and the conditional had a trap in it

This ADR was written while `Proposed`, and its Verification section describes that pending
state as ongoing. Efe accepted it on 2026-08-28. The decision is unchanged — what follows
corrects text that has stopped being true, per ADR-0029 rule 2.

The Verification section opened:

> **Withheld until this ADR is Accepted.** `memory-record.schema.json` is `stability: stable`
> and inside the architecture checksum set, and `Architecture_Freeze.md` §4 requires an ADR
> *and* Efe's approval before a stable surface moves. The schema is unchanged while this is
> `Proposed`. ADR-0029, ADR-0032, ADR-0033, ADR-0034, ADR-0035 and ADR-0036 each practised
> this withholding; this is the seventh.

and continued:

> The current behaviour is pinned rather than left drifting.
> `tests/contract/test_memory_contract.py::test_a_redacted_record_still_validates` asserts
> that a tombstone **does** fail validation today, and says why in the assertion message: if
> it stops failing, the schema changed and the tombstone shape needs a decision rather than a
> silent pass. That test is the thing that has to be rewritten on acceptance, which is the
> right amount of friction.

Both were true and are now discharged. As of architecture 1.17.0
`memory-record.schema.json` is **1.1.0** with the `if`/`then`/`else`, `redacted_at` required
alongside `redacted: true`, and the example's `"[redacted]"` corrected to `""`. The pinning
test inverted exactly as that paragraph said it would: `test_a_redacted_record_still_validates`
became `test_a_tombstone_validates`.

### The conditional did nothing for one commit, and looked right doing it

The first version kept `minLength: 1` on the base `properties.text` and added
`then: {properties: {text: {minLength: 0}}}`. **JSON Schema applies every applicable keyword.**
A base constraint is not relaxed by a conditional; both must pass. So the tombstone example
still failed, the `then` branch was decorative, and the diff read as a correct fix.

Caught by running the validator against the two examples rather than by reading the diff —
which is the same distinction this ADR's Context is about, one level down. `minLength` now
lives only in the branches, and `test_the_conditional_actually_applies` asserts that
structurally, because the symptom of getting it wrong is silence.

On acceptance, delivered:

| | |
|---|---|
| `memory-record.schema.json` → 1.1.0 | `if`/`then`/`else`; `redacted_at` required with `redacted: true`; `minLength` moved into the branches; `compatibility.minor_changes` records why this is a widening |
| its `examples` | `"[redacted]"` → `""`, reversing what the schema's author wrote, deliberately |
| `test_memory_contract.py` | four cases: a tombstone validates, a live record with empty text does not, a tombstone without a date does not, and the conditional is structurally in the right place |
| `ci/self_test.sh` | 31 → **32**: the tombstone example with `redacted` flipped to false, asserting `JSON-004` — the smallest edit that takes the other branch, and exactly what "just relax minLength" would have permitted |
