# ADR-0002: Project root is `C:\Users\deniz\Desktop\L.I.O.N.E.L`

| | |
|---|---|
| Status | **Accepted** — carried forward from MASTER_PLAN v1.0. See the Erratum of 2026-08-25: the root is now `Projects/`, not `Desktop/` |
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

## Erratum — 2026-08-25: the root moved to `Projects/`, and nothing noticed

This ADR's title and Decision name a directory that no longer exists. The repository
lives at `C:\Users\deniz\Projects\L.I.O.N.E.L`. The original wording, quoted so the
correction cannot be mistaken for a rewrite:

> # ADR-0002: Project root is `C:\Users\deniz\Desktop\L.I.O.N.E.L`

> **`C:\Users\deniz\Desktop\L.I.O.N.E.L` is the canonical project root.** All absolute
> paths, MCP filesystem server roots, scripts, and documentation use it.
>
> In Git Bash this is `/c/Users/deniz/Desktop/L.I.O.N.E.L`.

**Read `Projects` for `Desktop` throughout: the canonical project root is
`C:\Users\deniz\Projects\L.I.O.N.E.L`, and in Git Bash
`/c/Users/deniz/Projects/L.I.O.N.E.L`.** Everything else stands unchanged — one
canonical root, forward slashes in config values, no environment variable, and no
module building paths by string concatenation.

**Why this is an Erratum and not a supersession.** The decision here was never
"Desktop". Read the Context: the choice was between `efe` and `deniz`, and the rule it
applied was *"The directory that actually exists, and that tooling has access to."*
That rule is unchanged and still selects exactly one answer; only the answer moved.
ADR-0029 rule 3 fits — the text became wrong about a decision that was always this
one. A supersession would be the right instrument for a different decision, such as
making the root configurable, and that alternative is still rejected for the reason
already recorded: configurability for a problem with exactly one correct answer.

**What it cost.** This ADR's own Context says an unresolved path *"silently produces
two divergent trees, half-written config, and MCP filesystem roots that point at
nothing."* That is what happened, to this ADR, in this repository. The stale root was
written into `config/capabilities.registry.json` and `config/lionel.toml`, and the
`filesystem` capability — the one thing standing between a prompt going sideways and
`C:\Windows` — was scoped to a directory that did not exist. All twenty-two gates were
green throughout. A host path cannot be checked by anything that runs on another
machine, and CI runs on another machine; that is why nothing was checking it.

**What now checks it.** `scripts/check_env.sh` verifies every declared host path
exists and belongs to this checkout, on the host, on every run — it is what found
this. It scans both declaring files, because a check that read only the capability
registry would have corrected one of them and reported success. The Verification
clause below is unchanged and still owed: it needs `--live`.

**Not corrected, deliberately.** `MASTER_PLAN_v1.md` and `Phase0_Blockers.md` still
say `Desktop`. Both are frozen historical records preserved verbatim by decision
(`markdown.exempt_reasons`), and editing them to agree with the present would destroy
the thing they exist to be.
