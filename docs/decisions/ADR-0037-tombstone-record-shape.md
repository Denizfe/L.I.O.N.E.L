# ADR-0037: A tombstone is a MemoryRecord, and the contract has no shape for one

| | |
|---|---|
| Status | **Proposed** — awaiting Efe. `Architecture_Freeze.md` §4 and §5 step 4 |
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

The `jsonschema` gate did not, and could not. It validates each schema against its
metaschema and each schema's own `examples` against itself. Both schemas are valid, and
neither ships an example of a redacted record — which is the only kind of example that
would have failed.

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
4. The schema gains a redacted record to its `examples`, so the `jsonschema` gate exercises
   the shape on every push. The absence of that example is why this survived a freeze.

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
| **Keep a placeholder string, e.g. `"[redacted]"`** | Satisfies the schema by writing text into a record whose entire purpose is to have none, and every consumer then has to know one magic string. It would also be embedded and searchable, so a query for "redacted" would rank every forgotten memory first |
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
| its `examples` | gain a redacted record, so `JSON-004` exercises the shape on every push — the absence of one is why this survived a freeze |
| `test_memory_contract.py` | the pinning test inverts: a tombstone must now validate, and a live record with empty text must not |
| `ci/self_test.sh` | a planted live record with empty text, asserting `JSON-004` |

Gate **G2**, alongside the `forget(id)` clause it belongs to.
