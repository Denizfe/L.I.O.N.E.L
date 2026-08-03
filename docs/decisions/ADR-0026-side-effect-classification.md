# ADR-0026: Side-effect classification on every tool

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 |
| Related | [ADR-0012](ADR-0012-policy-engine.md), [ADR-0025](ADR-0025-cancellation-backpressure.md), [ADR-0011](ADR-0011-capability-tools-no-shell.md) |

## Context

Several behaviors in this system need to know whether an operation has consequences:

- **Retry.** Retrying a read is free. Retrying a write may duplicate it.
- **Cancellation.** A read aborts cleanly; a write must complete or roll back
  ([ADR-0025](ADR-0025-cancellation-backpressure.md)).
- **Confirmation.** Some operations warrant a human in the loop.
- **Audit.** Some operations must be recorded permanently.
- **Trust.** Untrusted content must not reach consequential operations
  ([ADR-0012](ADR-0012-policy-engine.md)).

Without a declared classification, each of these behaviors ends up inferring intent from
tool names — `delete_*` heuristics — which is guesswork that fails on the first tool named
`cleanup` or `sync`.

## Decision

**Every tool declares a `side_effect` class. The registry rejects tools that do not.**

| Class | Meaning | Retry | On cancel | Confirm | Audit |
|---|---|---|---|---|---|
| `read` | No state change | Free | Abort freely | No | No |
| `write` | Reversible state change | Only if idempotency key present | Complete or roll back | No | Yes |
| `destructive` | **Irreversible** — or reversible only with effort | Never automatically | Complete or roll back | **Yes** | Yes |

### Rules

- **Classification is declared, never inferred.** No name heuristics.
- **When in doubt, classify higher.** Mis-classifying a read as a write costs a
  confirmation prompt. The reverse costs data.
- `write` tools that support retry must accept an **idempotency key**; without one they are
  not retried.
- `destructive` requires explicit confirmation, and confirmation is **per invocation** —
  never a session-wide "yes to all," which is how confirmation prompts become rubber stamps.

## Consequences

### Positive
- Retry, cancellation, confirmation, audit, and trust policy all read one declared field
  instead of each inventing a heuristic.
- Tool authors are forced to think about consequences at authoring time, which is when it
  is cheapest.
- Provides the natural hook for physical actuation later
  ([ADR-0024](ADR-0024-robotics-capability-safety.md)) — physical actions are `destructive`
  by default precisely because irreversibility is what the category encodes.

### Negative / Costs
- One more mandatory field per tool. Trivial.
- Idempotency keys are real work for `write` tools that want retry. Optional per tool.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Infer from tool name | Fails on the first ambiguously named tool. Guessing about destructive operations is not acceptable |
| Binary safe/unsafe | Collapses `write` and `destructive`, which need different retry and confirmation behavior |
| Per-call-site policy | Duplicated and drifting; the tool knows its own consequences, the caller does not |
| Confirm everything | Confirmation fatigue. The prompt stops being read |

## Verification

Gate **G4**. The registry rejects a tool with no `side_effect`; a `destructive` tool
requires explicit per-invocation confirmation; retry behavior matches class in contract
tests.
