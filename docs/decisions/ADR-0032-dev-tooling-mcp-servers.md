# ADR-0032: Developer-tooling MCP servers are declared, pinned, and disclosed

| | |
|---|---|
| Status | **Accepted** 2026-08-24 — see the Erratum of the same date |
| Date | 2026-08-11 |
| Phase | 1 |
| Related | [ADR-0013](ADR-0013-artifact-pinning.md), [ADR-0015](ADR-0015-secret-resolver.md), [ADR-0007](ADR-0007-degradation-ladder.md), [ADR-0022](ADR-0022-zero-trust-runtimes.md) |

## Context

MCP servers are currently configured **per machine**, in each developer's user-level Claude
Code settings. No `.mcp.json` exists in the repository. Two consequences:

1. **The tooling is not reproducible.** This is a project whose central claim is that a clean
   clone reproduces a verified state — 20 gates, a checksum over 72 files, three CI platforms.
   The tools used to work on it are the one part that lives only on one machine.
2. **There is no place to put the question.** Adding a server is a technology choice with an
   egress profile and a supply-chain profile, and there is no shape in the repo for recording
   either.

The immediate case is **context7**, which serves live library documentation. Phase 1 writes
the first code against `grpcio`, `opentelemetry-sdk`, `structlog` and `psutil`, and recalled
API surfaces are a known source of confidently wrong code.

Three facts make this more than a convenience question:

| | |
|---|---|
| **It is a network service** | Queries go to Context7's servers. The local `@upstash/context7-mcp` package is a client, not a local index |
| **`npx -y <pkg>` resolves latest at every launch** | Precisely the failure ADR-0013 names: *"A rebuild in three months produces a different system"* |
| **The hosted endpoint takes an API key** | `Authorization: Bearer …` against `https://mcp.context7.com/mcp` — ADR-0015 territory |

**The offline objection deserves a direct answer, because it looks fatal and is not.**
ADR-0007's L0 guarantee constrains **the product at runtime**, not the workstation it is
written on. A developer reading documentation over the network no more breaks the autonomy
guarantee than reading it in a browser does. `l0-conformance` enforces the boundary on
`config/`, `contracts/` and the runtime surface; `.mcp.json` is in none of them.

What would break it is a *runtime* dependency on a documentation service, and nothing here
proposes one.

## Decision

**Developer-tooling MCP servers live in a checked-in `.mcp.json`, are version-pinned, and
declare what leaves the machine.**

Four rules:

1. **Declared, not ambient.** A server the team is expected to have goes in `.mcp.json`.
   Personal servers stay in user settings. A tool that only some contributors have produces
   results others cannot reproduce.
2. **Pinned.** Package-backed servers pin an exact version — `@upstash/context7-mcp@4.0.0`,
   never bare `npx -y @upstash/context7-mcp`. ADR-0013's reasoning is about supply chains,
   and an MCP server is code that runs on a developer machine with the repository open.
3. **Egress disclosed.** Each entry records, in `.mcp.json` alongside it, what it sends off
   the machine and to whom. "Library names and version strings" and "the contents of files
   you ask it about" are different answers and must not be collapsed.
4. **No secrets in `.mcp.json`.** ADR-0015 forbids interpolated credentials. An MCP server
   needing a key reads it from the environment via the SecretResolver scheme; a literal key
   in a checked-in file is a committed secret, and `gate_secrets` scans that file with no
   path exclusions.

### First entry

| | |
|---|---|
| Server | `context7` |
| Package | `@upstash/context7-mcp@4.0.0` — **MIT** |
| Transport | stdio, local client process |
| Egress | library / package names and documentation queries → Context7's servers |
| Secrets | **none.** Use the keyless stdio path. The hosted endpoint's API key buys rate limit, not capability, and is not worth introducing a credential for |
| Scope | **documentation lookup only.** Not a source of runtime behaviour, not a dependency of any gate |

**It never becomes a runtime or CI dependency.** No gate may require it — CI validates the
repository with `pyyaml`, `jsonschema` and `grpcio-tools`, and that list is the whole
contract. A gate that needed a documentation service would fail offline, which is the one
thing this project does not permit.

## Consequences

### Positive

- The toolchain becomes part of the clone, like everything else here. A contributor gets the
  same tools, not an approximation of them.
- The egress question gets asked once, in writing, instead of never.
- Pinning means a developer-machine supply-chain compromise has a version to point at. `npx
  -y` resolves latest silently, and the compromise window is "whenever anyone next started
  their editor."
- `.mcp.json` gives future servers — a database inspector at G2, Playwright at G6 — a place
  to be reviewed rather than accumulated.

### Negative / Costs

- **A network service enters the workflow of an offline-first project.** The distinction
  between the workstation and the runtime is real, and it is also exactly the kind of
  distinction that erodes. MASTER_PLAN_v2 §W1 describes that erosion as this project's
  characteristic failure mode: *"Nobody decides to abandon offline operation. It erodes."*
  The mitigation is rule 4's hard line — no gate, no runtime path, ever — and it is a line,
  not a mechanism.
- **Documentation queries reveal what is being built**, before it is public. Library names
  and version strings are not nothing.
- **Pinning has a cost.** Pinned servers go stale and someone must bump them; the whole point
  is that bumping is a visible act.
- **A third-party process runs with the repository open.** `.mcp.json` is a review surface,
  and it needs to be reviewed like one — this ADR does not make that automatic.
- **One entry is a policy; three is a habit.** The second addition is the one to scrutinise.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| **Leave MCP servers user-level** | The status quo, and it is the one part of this project that is not reproducible. It also leaves no place to record the egress question, so it never gets asked |
| **Add `context7` with no ADR — "it's just dev tooling"** | The shortcut §4 exists to prevent. The answer might well be yes; the objection is to reaching it without a record. This ADR exists because that reasoning was available and declined |
| **`npx -y @upstash/context7-mcp` unpinned** | Convenient, and it makes every developer machine resolve a different version at every launch. ADR-0013 rejected exactly this for images and models; the argument does not weaken because the code runs locally |
| **The hosted endpoint with an API key** | Adds a credential, a rotation duty and a `.mcp.json` secret risk, in exchange for rate limit. Rate limit is not the constraint |
| **Vendor documentation into the repo** | Genuinely offline, and stale within a release. Also enormous |
| **Ban network-backed dev tooling outright** | Consistent, and it would also ban the browser. The line that matters is runtime, not workstation |

## Verification

**Not yet implemented — deliberately.** ADR-0029's precedent: a gate enforcing an unapproved
decision is the error ADR-0030 is about.

On acceptance:

- **`MCP-001`** — every `.mcp.json` entry with a package-backed command pins an exact
  version. Bare `npx -y <pkg>` fails.
- **`MCP-002`** — every entry declares an `x-lionel.egress` note saying what leaves the
  machine.
- **`MCP-003`** — no entry references a literal credential. `gate_secrets` already scans
  `.mcp.json` with no path exclusions; this makes the intent explicit rather than incidental.
- **`l0-conformance`** continues to prove that nothing in `config/`, `contracts/` or the
  runtime surface depends on any of it.
- `ci/self_test.sh` plants an unpinned `npx -y` entry and asserts `MCP-001`.

**Standing criterion:** `.mcp.json` holds **one** entry. A second is a decision, not a
routine addition, and this line is where that gets noticed.

**Until this ADR is Accepted, `.mcp.json` is not created.** The mechanism is the thing being
proposed, so shipping it early would be deciding by doing — which is the practice this
document exists to interrupt.

## Erratum — 2026-08-24: Accepted; the deferral it describes has been discharged

This ADR was written while Proposed, and two of its paragraphs describe that pending state
as if it were ongoing. Efe accepted it on 2026-08-24. The decision is unchanged — what
follows corrects text that has stopped being true, per ADR-0029 rule 2.

The Verification section opened:

> **Not yet implemented — deliberately.** ADR-0029's precedent: a gate enforcing an
> unapproved decision is the error ADR-0030 is about.

and closed:

> **Until this ADR is Accepted, `.mcp.json` is not created.** The mechanism is the thing
> being proposed, so shipping it early would be deciding by doing — which is the practice
> this document exists to interrupt.

Both were true and are now discharged. As of architecture 1.4.0:

- `.mcp.json` exists at the repository root and holds exactly one entry, `context7`,
  pinned to `@upstash/context7-mcp@4.0.0`, with an `x-lionel` block declaring its licence,
  its scope and its egress. It carries no credential.
- `ci/gates/gate_mcp.py` implements **`MCP-001`** (exact version pin), **`MCP-002`**
  (declared egress) and **`MCP-003`** (no literal credential), configured from
  `mcp:` in `ci/policy/policy.yaml`.
- `ci/self_test.sh` plants an unpinned `npx -y` entry and asserts `MCP-001`, as this
  section required.
- `repository.required_paths` now names `.mcp.json`, so its deletion fails `structure`
  rather than silently disarming the gate. Existence is the structure gate's business;
  `gate_mcp` checks content.

One rule was added beyond the three named above. **`MCP-000`** fires when `.mcp.json` is
not valid JSON. It is mechanical necessity rather than a new decision: without it a
malformed manifest would have to be reported through `gate_error`, which means exit 2 —
"the gate is broken" — for a file the repository owns and a human must fix. The exit-code
contract does not permit that confusion.

The standing criterion — one entry, and a second is a decision rather than a routine
addition — is **not** enforced as a blocking rule. `gate_mcp` reports the entry count as a
note on every run, restating the criterion. Turning it into a gate would decide, by
implementation, a question this ADR deliberately left to a reviewer.
