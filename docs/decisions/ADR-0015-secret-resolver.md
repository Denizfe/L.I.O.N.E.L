# ADR-0015: Layered config and SecretResolver URIs

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 |
| Related | [ADR-0022](ADR-0022-zero-trust-runtimes.md), [ADR-0019](ADR-0019-opentelemetry.md) |

## Context

MASTER_PLAN v1.0 put `"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PAT}"` in a JSON config
file. JSON does not expand variables. Docker does not expand them in that position. No
component was named as the expander — so it would not have worked.

The natural fix is worse than the bug. Adding string interpolation to the config loader
means the resolved secret becomes an ordinary string, and ordinary strings end up in log
lines, exception messages, crash dumps, and telemetry. Every leak of this kind starts as a
convenience.

Additionally, the mechanism must span four very different environments: local Windows dev
(L0/L1) through Kubernetes (L2+).

## Decision

**No string interpolation anywhere.** Config references secrets by a **typed URI** that a
`SecretResolver` dereferences at point of use.

| Scheme | Backend | Tier |
|---|---|---|
| `secret://env/NAME` | Environment variable | Local dev |
| `secret://file/PATH` | Mounted file | Containers |
| `secret://dpapi/NAME` | Windows Credential Manager / DPAPI | L0, L1 on the host |
| `secret://k8s/SECRET/KEY` | Kubernetes Secret via External Secrets Operator | L2+ |

Resolved values are wrapped in a **`SecretStr`** type whose `__repr__` and `__str__`
redact. A secret that reaches a log line prints as `***`. **Redaction happens at the type,
not at the call site**, because call-site redaction is eventually forgotten exactly once.

### Config layering, in order

`defaults → config/lionel.toml → config/tiers/<tier>.toml → environment → CLI`

Typed and validated at load. **Unknown keys are an error**, not a silent ignore.

**`.env` is developer-local only** and is never a production mechanism.

## Consequences

### Positive
- The mechanism spans dev through cloud without a config rewrite per tier.
- Leaks are prevented by the type system rather than by discipline.
- Rotation is a backend concern, invisible to application code.

### Negative / Costs
- Every secret consumer must handle `SecretStr` rather than `str`. Mild friction, correct
  friction.
- Four resolver backends to implement and test.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| `${VAR}` interpolation in the loader (v1.0's implied fix) | Produces plain strings that leak into logs. The failure this ADR exists to prevent |
| `.env` everywhere including production | No rotation, no scoping, no audit; a file on disk in plaintext |
| Vault from day one | Operational weight far ahead of need. The URI scheme leaves the door open |
| Env vars only | Visible in process listings and crash dumps; no Windows-native option |

## Verification

Gate **G0**. Pre-commit secret scanner blocks a deliberately planted test credential.
Gate **G1**: a `secret://` URI resolves and its value **redacts in log output**.
Gate **G5**: no secrets appear in any log under a fuzzing pass.
