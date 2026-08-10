# ADR-0016: ADRs replace `<thought>` as the decision artifact

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 |
| Related | [ADR-0010](ADR-0010-memory-service.md) |

## Context

The original working method called for design reasoning inside `<thought>` tags before
non-trivial modules. The reasoning is useful. The **artifact** is not:

- **Ephemeral.** Gone when the session ends.
- **Ungreppable.** Cannot be searched six weeks later.
- **Undiffable.** Cannot be reviewed, cited in a PR, or shown to be stale.
- **Not stored.** The project's own project-memory rule requires decisions to be persisted.
  `<thought>` cannot satisfy a rule it is structurally incapable of meeting.

The result is predictable: rationale evaporates, and the same debates recur every few weeks
with no record of what was already settled.

## Decision

**Exploratory reasoning stays internal. The durable output is an ADR.**

- Any decision that **constrains future work** produces an ADR in `docs/decisions/`.
- Smaller calls produce a short **Decision Summary** in the response — context, choice,
  one-line rationale.
- Format: Status / Context / Decision / Consequences / Alternatives Rejected / **Verification**.
- **Alternatives Rejected is mandatory.** A decision without rejected alternatives is a
  preference wearing a decision's clothes.
- **Verification is mandatory.** Every ADR names the gate criterion that checks it.
- ADRs are **immutable once Accepted**. To change one, write a superseding ADR. Only the
  `Status` line of the original may be edited.
- **On merge, every ADR is indexed into the Memory Service** ([ADR-0010](ADR-0010-memory-service.md)),
  so `memory.recall` retrieves it later. This is what actually satisfies the project-memory
  rule.
- **Query before deciding.** Before proposing a change to a module, search existing ADRs and
  memory. Settled decisions are not relitigated silently.

## Consequences

### Positive
- Rationale survives, is searchable, and is reviewable as a diff.
- The project can answer "why is it like this?" without archaeology.
- ADR-0004 in this very repository demonstrates the value: a superseded decision keeps its
  reasoning, and the parts worth carrying forward are explicitly identified.

### Negative / Costs
- Writing ADRs takes time, and there is a temptation to write them for trivial choices. The
  Decision Summary tier exists to absorb that.
- Immutability means a wrong ADR stays visible. Correct: the history is the point.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Keep `<thought>` | Ephemeral, unreviewable, and does not satisfy the project-memory rule |
| Code comments | Explain *what*, not *why not*. Rejected alternatives have nowhere to live |
| Commit messages | Better, but scattered and hard to browse as a decision set |
| A design wiki | Drifts from the code; not diffable alongside it |

## Verification

Gate **G0**. Every ADR has all six sections. Gate **G2**: ADRs are indexed into the Memory
Service and retrievable by semantic query.

## Amendment — 2026-08-11: modification procedure is governed by ADR-0029

**Nature of change: AMENDMENT.** It adds the procedure this ADR left implicit. The
immutability principle below is unchanged; what changes is that "immutable" now has a
written definition instead of one inferred from a single sentence.

The Decision above says:

> ADRs are **immutable once Accepted**. To change one, write a superseding ADR. Only the
> `Status` line of the original may be edited.

**[ADR-0029](ADR-0029-adr-errata-provision.md) now governs how an Accepted ADR may be
modified.** It keeps the principle — the *Decision* is immutable, and the body is never
edited in place — and names three append-only operations: **Supersede**, **Amend**,
**Erratum**.

This is a widening, not a reversal. The sentence above was written as though supersede were
the only instrument, and practice had already diverged from it three times — ADR-0013 twice,
ADR-0017 once — every time correctly. ADR-0029 §Context sets out why.

**This section is itself the first use of the mechanism it points to.** Adding it under the
old rule would have been forbidden; adding it any other way would have meant editing the
Decision above. That it can be written at all is the evidence for ADR-0029.

Shape is enforced by **`ADR-009`**.

