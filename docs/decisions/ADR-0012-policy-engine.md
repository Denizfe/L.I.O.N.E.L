# ADR-0012: Policy Engine — default-deny tool authorization

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 (design), 4 (build) |
| Related | [ADR-0011](ADR-0011-capability-tools-no-shell.md), [ADR-0026](ADR-0026-side-effect-classification.md), [ADR-0024](ADR-0024-robotics-capability-safety.md) |

## Context

[ADR-0011](ADR-0011-capability-tools-no-shell.md) removes shell execution, but typed tools
still have real power — writing files, restarting services, pushing to GitHub. "Which tool
may run, when, on whose authority" is a policy question, and policy scattered across tool
implementations drifts, is untestable, and is invisible in review.

Prompt injection remains live even without a shell: content read from a document should
never be able to authorize a write.

## Decision

A **Policy Engine** inside `ToolRouter`, evaluating every invocation *before* dispatch.
Rules are **declarative** (`config/policy/`), not code. **Default is deny.**

Each tool declares metadata the engine evaluates:

| Field | Values | Drives |
|---|---|---|
| `side_effect` | `read` \| `write` \| `destructive` | Retry safety, confirmation ([ADR-0026](ADR-0026-side-effect-classification.md)) |
| `trust_required` | `any` \| `user_originated` \| `operator` | Blocks injected content from reaching write tools |
| `rate_limit` | per-tool budget | Runaway loop containment |
| `audit` | boolean | Immutable audit-log entry |

### Trust propagation

Every piece of context carries a trust level. Text spoken by Efe is `user_originated`. Text
read from a file, a web page, or a tool result is **untrusted** and stays untrusted through
the turn. A tool marked `trust_required: user_originated` **cannot be invoked on a turn
whose triggering content is untrusted.**

This is the mechanism that makes injection structurally unable to escalate, rather than
filtered and hoped about.

### Auditing

The engine logs **every decision — allows and denies alike.** A log that only records
refusals cannot answer "what did it actually do last Tuesday."

## Consequences

### Positive
- One chokepoint, guaranteed by [ADR-0003](ADR-0003-mcp-first-capability-model.md) to see
  100% of invocations.
- Policy is reviewable as a diff and testable without running the agent.
- Default-deny means a forgotten tool registration fails closed.
- Provides the natural home for robotics safety interlocks
  ([ADR-0024](ADR-0024-robotics-capability-safety.md)) — outside the model, where they belong.

### Negative / Costs
- Every tool needs complete metadata, and the registry rejects tools that lack it. Friction
  by design.
- Trust propagation must thread through `ContextAssembler` and `TurnExecutor`; a gap in the
  chain is a silent hole. Covered by contract tests.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Checks inside each tool | Duplicated, drifts, unreviewable, and impossible to audit centrally |
| Prompt-level rules ("never delete without asking") | A model is not a security boundary. Injection targets exactly this |
| Allow-by-default with a denylist | A forgotten tool becomes an open door. Fails open |
| Human confirmation for everything | Confirmation fatigue converts the prompt into a rubber stamp |

## Verification

Gate **G4**. Registry rejects a tool with incomplete metadata; a `destructive` tool requires
explicit confirmation; **a simulated injection payload in a file read cannot reach a `write`
tool**; rate limiting contains a deliberate runaway loop; every allow and deny appears in
the audit log.
