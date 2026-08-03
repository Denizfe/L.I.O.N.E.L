# ADR-0002: Project root is `C:\Users\deniz\Desktop\L.I.O.N.E.L`

| | |
|---|---|
| Status | **Accepted** — carried forward from MASTER_PLAN v1.0 |
| Date | 2026-08-01 |
| Phase | 0 |

## Context

The original project instructions specify `C:\Users\efe\Desktop\L.I.O.N.E.L`. The
directory that actually exists, and that tooling has access to, is
`C:\Users\deniz\Desktop\L.I.O.N.E.L`. Efe confirmed the `deniz` path is correct and the
instruction text is stale.

An unresolved path ambiguity is not cosmetic — it silently produces two divergent trees,
half-written config, and MCP filesystem roots that point at nothing.

## Decision

**`C:\Users\deniz\Desktop\L.I.O.N.E.L` is the canonical project root.** All absolute
paths, MCP filesystem server roots, scripts, and documentation use it.

In Git Bash this is `/c/Users/deniz/Desktop/L.I.O.N.E.L`. Config values that carry Windows
paths use **forward slashes** so Bash does not consume them as escapes.

## Consequences

- The stale `efe` path in the project instructions should be corrected at the source so it
  does not resurface in a future session.
- A single `platform/config` module owns path resolution; no module builds paths by string
  concatenation.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Use the `efe` path and ask Efe to re-point the mount | Higher friction for no benefit; the existing directory already holds the plan documents |
| Support both via an env var | Configurability for a problem that has exactly one correct answer |

## Verification

Gate **G1**. The MCP filesystem server starts scoped to this root, lists it successfully,
and refuses a read outside it.
