# ADR-0011: Capability tools; shell execution abolished

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 |
| Related | [ADR-0012](ADR-0012-policy-engine.md), [ADR-0026](ADR-0026-side-effect-classification.md) |

## Context

MASTER_PLAN v1.0 named `shell_server.py` "the sharpest edge in the entire project" — a
correct diagnosis — and then reached for an allowlist, `shell=False`, timeouts, and output
truncation. Its own risk register (R6) rated this as sufficient mitigation for prompt
injection.

It is not sufficient. An allowlist gates the **verb** and leaves the **arguments** open:

- **Argument injection.** `git` is allowlisted; `git --upload-pack=<command>` executes it.
- **Path traversal.** A validated command with an unvalidated path escapes any root.
- **TOCTOU.** Validate a path, then the filesystem changes before use.
- **Prompt injection.** This is the one that matters. L.I.O.N.E.L reads documents. A
  document containing instructions can steer a tool call. With shell available, injected
  text becomes arbitrary code execution on Efe's primary machine.

The threat model is not "the agent decides to do something bad." It is "someone else's text
decides for it."

## Decision

**`shell_server.py` is deleted from the plan.** Not constrained. Removed. No module in
`src/lionel/capabilities/` may invoke a shell, and no tool accepts free text destined for
an interpreter.

Capabilities are **typed tools**: narrow, single-purpose, fully schema'd, with no
passthrough.

| Instead of | Use |
|---|---|
| `run_command("systemctl restart x")` | `service.restart(name: ServiceName)` — an enum |
| `run_command("cat file")` | `fs.read(path: ProjectRelativePath)` — a validated type |
| `run_command("ps aux")` | `process.list()` — no arguments at all |
| `run_command("docker ps")` | `container.list()` — typed filters only |

**The rule:** if a capability cannot be expressed as a typed schema over a closed set of
values, it does not become a tool. That constraint is doing real work — it is what forces
each capability to be small enough to reason about.

`capabilities/shell/` is listed as deleted in the repository layout so its absence reads as
a decision rather than an oversight.

## Consequences

### Positive
- The prompt-injection path to code execution is closed **structurally**, not by filtering.
- Every capability has a schema, which is what makes
  [ADR-0012](ADR-0012-policy-engine.md) enforceable.
- Tools become self-documenting and individually testable.

### Negative / Costs
- Every new operation requires a purpose-built tool. This is slower than exposing a shell,
  and that slowness is the security property.
- Some genuinely ad-hoc operations become unavailable to the agent. **Efe runs those in a
  terminal.** A human at a keyboard is an acceptable answer.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Allowlist with argument validation (v1.0) | Validation must be perfect forever against an adversary who supplies the input. Any gap is RCE |
| Shell in a sandboxed container | Better, but still full RCE inside the sandbox, plus escape risk and a mount that reaches the real filesystem to be useful |
| Shell gated on human confirmation | Confirmation fatigue makes this a rubber stamp. Also unusable for autonomous operation |
| Read-only shell | "Read-only" is not decidable from a command string |

## Verification

Gate **G4**. **No shell execution path exists anywhere in the capability surface**, checked
statically. A simulated prompt-injection payload embedded in a file read fails to reach any
`write` tool.
