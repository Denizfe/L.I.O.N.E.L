# Policy Gates

**The complete rule catalogue.** Phase 0 / M3. Generated 2026-08-02.

Every rule below is enforced by a gate that runs on every push and every pull request. Each entry names the decision it protects — a rule whose reason is invisible looks arbitrary, and arbitrary rules get deleted by the next person in a hurry.

| | |
|---|---|
| Rules | **88** |
| Gates | **16** |
| Severity | **All rules are blocking.** There is no warnings-only tier |
| Exit codes | `0` pass · `1` violation · `2` gate itself broken |

## Why there is no warning tier

A warning is a rule nobody enforces. Within a few sprints the log is full of them, people stop reading, and a real violation scrolls past unseen. If a rule is not worth blocking on, it is not worth checking; if it is worth checking but cannot block yet, it belongs in a **registry** with an owner and a removal gate — see §Exemptions.

---

## `adr` — ADR validation

**Enforces:** ADR-0016

**Run:** `python3 ci/gates/gate_adr.py`

| Rule | Triggers when |
|---|---|
| `ADR-001` | expected {cfg['expected_count']} ADRs, found {len(files)} |
| `ADR-002` | numbering gap: ADR-{expect:04d} missing |
| `ADR-003` | no Status row |
| `ADR-004` | missing section `{sec}` |
| `ADR-005` | malformed ADR filename `{f.name}` |
| `ADR-006` | unrecognised status `{val[:60]}` |
| `ADR-007` | superseded without naming the successor |
| `ADR-008` | dangling reference to ADR-{m.group(1)} |

## `architecture` — Architecture conformance

**Enforces:** ADR-0006, ADR-0007, ADR-0009, ADR-0010, ADR-0011, ADR-0012, ADR-0025, ADR-0026

**Run:** `python3 ci/gates/gate_architecture.py`

| Rule | Triggers when |
|---|---|
| `ARCH-001` | `src/lionel/capabilities/shell/` exists |
| `ARCH-002` | branching on provider name |
| `ARCH-003` | media payload key `{key}` in a control-plane schema |
| `ARCH-004` | MCPTool exposes `{bad}` |
| `ARCH-005` | ToolSpec does not require `{field}` |
| `ARCH-006` | `{Path(path).name}` does not require `{field}` |
| `ARCH-007` | MemoryQueryResult does not require `trust_floor` |
| `ARCH-008` | ProviderRequest does not require `cancellation_token_id` |
| `ARCH-009` | policy default is not pinned to `deny` (found {const!r}) |
| `ARCH-010` | `memory.forget` is not a required tool |
| `ARCH-011` | L0 tier config missing: `{cfg['l0_tier_file']}` |
| `ARCH-012` | L0 `{key}` is not `{want}` |
| `ARCH-013` | L0 selects network provider `{bad}` |
| `ARCH-014` | English-only `.en` whisper model referenced |
| `ARCH-015` | `src/lionel/host/loop.py` exists |
| `ARCH-016` | ADR(s) not listed in the index: {sorted(missing)} |

## `artifacts` — Artifact lock validation

**Enforces:** ADR-0013

**Run:** `python3 ci/gates/gate_artifacts.py`

| Rule | Triggers when |
|---|---|
| `ART-000` | {unres} artifact(s) unresolved |
| `ART-001` | `{name}` missing `{f_}` |
| `ART-002` | `{name}` missing `verification.{f_}` |
| `ART-003` | `{name}` invalid tier `{v['tier']}` |
| `ART-004` | `{name}` invalid provenance `{v['provenance']}` |
| `ART-005` | `{name}` pinned-model-id without `pinned_by` |
| `ART-006` | `{name}` is RESOLVED with no pin |
| `ART-007` | `{name}` malformed hash `{h}` |
| `ART-008` | `{name}` verification.method too thin to audit |
| `ART-009` | `{name}` blocker not classified |
| `ART-010` | `{name}` blocker does not say what is blocked |
| `ART-011` | `{name}` proposes no alternative |
| `ART-012` | `{name}` has no REPRODUCIBLE alternative |
| `ART-013` | `{name}` unknown status `{st}` |
| `ART-014` | [meta] drift: declared {m.get('resolved')}/{m.get('unresolved')}, actual {res}/{unres} |
| `ART-015` | {tiers['D']} tier-D artifacts, policy allows {cfg['max_tier_d']} |
| `ART-016` | an English-only `.en` whisper model is pinned |

## `contracts` — Contract metadata

**Enforces:** ADR-0003, ADR-0009

**Run:** `python3 ci/gates/gate_contracts.py`

| Rule | Triggers when |
|---|---|
| `CONTRACT-001` | no `x-lionel` block |
| `CONTRACT-002` | `x-lionel.{k}` missing |
| `CONTRACT-003` | `compatibility.{k}` missing |
| `CONTRACT-004` | invalid plane `{x.get('plane')}` |
| `CONTRACT-005` | invalid stability `{x.get('stability')}` |
| `CONTRACT-006` | invalid owner `{x.get('owner')}` |
| `CONTRACT-007` | empty `consumers` |
| `CONTRACT-008` | manifest missing: {cfg['manifest']} |
| `CONTRACT-009` | manifest/disk mismatch in `{plane}` |
| `CONTRACT-010` | Contract_Inventory.md missing |

## `dependencies` — Dependency policy

**Enforces:** ADR-0013

**Run:** `python3 ci/gates/gate_dependencies.py`

| Rule | Triggers when |
|---|---|
| `DEP-001` | `{base}` has no version bound |
| `DEP-002` | forbidden package `{base}` |

## `docker-digests` — Docker image digest pinning

**Enforces:** ADR-0013, ADR-0020

**Run:** `python3 ci/gates/gate_docker_digests.py`

| Rule | Triggers when |
|---|---|
| `DOCKER-001` | malformed digest `{m.group(0)}` |
| `DOCKER-003` | image `{name}` is RESOLVED without a digest |
| `DOCKER-004` | image `{name}` digest malformed |
| `DOCKER-005` | image `{name}` `pull_as` is not digest-pinned |
| `DOCKER-006` | image `{repo_}:{tag}` referenced without a digest |

## `jsonschema` — JSON Schema validation

**Enforces:** ADR-0027

**Run:** `python3 ci/gates/gate_jsonschema.py`

| Rule | Triggers when |
|---|---|
| `JSON-001` | invalid JSON: {e.msg} (line {e.lineno}) |
| `JSON-002` | not a valid JSON Schema 2020-12: {str(e)[:120]} |
| `JSON-003` | unresolvable $ref `{m}` |
| `JSON-004` | example[{i}] fails its own schema: {'.'.join(map(str, err.path)) or '(root)'} — {err.messa |
| `JSON-005` | no examples |
| `JSON-006` | malformed ULID `{v}` ({'; '.join(why)}) |

## `licenses` — Licence policy

**Enforces:** ADR-0013

**Run:** `python3 ci/gates/gate_licenses.py`

| Rule | Triggers when |
|---|---|
| `LIC-001` | `{sec}.{name}` declares no licence |
| `LIC-002` | `{sec}.{name}` licence needs review: {lic} |
| `LIC-003` | `{sec}.{name}` licence is unresolved: “{lic[:80]}” |
| `LIC-004` | `{sec}.{name}` licence `{lic}` is not on the allowlist |
| `LIC-005` | licence registry entry `{e.get('artifact')}` has no owner or resolve_by |

## `markdown` — Markdown lint

**Run:** `python3 ci/gates/gate_markdown.py`

| Rule | Triggers when |
|---|---|
| `MD-HEADING` | heading jumps from h{prev} to h{lvl} |
| `MD-LINK` | broken link `{tgt}` (text: “{text[:40]}”) |
| `MD-WS` | {n} line(s) with trailing whitespace |

## `no-latest` — Forbidden mutable image tags

**Enforces:** ADR-0013

**Run:** `python3 ci/gates/gate_no_latest.py`

| Rule | Triggers when |
|---|---|
| `DOCKER-002` | mutable tag `:{m.group(2)}` on `{m.group(1)}` |

## `no-pending` — Forbidden placeholder values

**Enforces:** ADR-0013

**Run:** `python3 ci/gates/gate_no_pending.py`

| Rule | Triggers when |
|---|---|
| `PLACEHOLDER-001` | placeholder `{m.group(0)}` present |

## `no-todo` — Forbidden TODO markers

**Enforces:** MASTER_PLAN_v2 §12

**Run:** `python3 ci/gates/gate_no_todo.py`

| Rule | Triggers when |
|---|---|
| `TODO-001` | unregistered `{m.group(0)}` |
| `TODO-002` | registry entry `{e.get('pattern')}` has no owner or no unblocked_by |

## `protobuf` — Protobuf validation

**Enforces:** ADR-0028, ADR-0006

**Run:** `python3 ci/gates/gate_protobuf.py`

| Rule | Triggers when |
|---|---|
| `PROTO-002` | duplicate field number(s) {dup} in `{msg.name}` |
| `PROTO-003` | enum `{en.name}` does not reserve 0 |
| `PROTO-004` | `{name}` imports `{dep}` |

## `secrets` — Secret scanning

**Enforces:** ADR-0015, ADR-0022

**Run:** `python3 ci/gates/gate_secrets.py`

| Rule | Triggers when |
|---|---|
| `SEC-INTERP` | `${...}` interpolation in a config file |
| `SEC-URI` | malformed secret URI `{m.group(0)}` |

## `shell` — Shell script policy

**Enforces:** ADR-0011, ADR-0014

**Run:** `python3 ci/gates/gate_shell.py`

| Rule | Triggers when |
|---|---|
| `SH-ADR0011` | shell execution in the capability surface |
| `SH-CRLF` | CRLF line endings |
| `SH-STRICT` | missing `set -euo pipefail` |

## `structure` — Repository structure

**Enforces:** ADR-0011, MASTER_PLAN_v2 §8

**Run:** `python3 ci/gates/gate_structure.py`

| Rule | Triggers when |
|---|---|
| `STRUCT-001` | required file missing: `{path}` |
| `STRUCT-002` | required directory missing: `{d}` |
| `STRUCT-003` | forbidden path exists: `{entry['path']}` |
| `STRUCT-004` | {len(offenders)} runtime source file(s) present during Phase 0 |

---

## Exemptions

Three mechanisms. One rule: **an owner and a route to removal, or it is not an exemption.**

| Mechanism | Config | Requires |
|---|---|---|
| TODO registry | `todo.registry` | `pattern` · `path_glob` · `owner` · `unblocked_by` |
| Licence registry | `licenses.unresolved_registry` | `artifact` · `owner` · `resolve_by` |
| Shell pragma | inline in the script | `# ci-policy: allow RULE — reason` (reason mandatory) |

`TODO-002` and `LIC-005` exist to police the escape hatches themselves: a registry entry
missing `owner` or its removal gate fails the build. Otherwise the exemption mechanism
becomes the loophole, which is the usual way this pattern dies.

### Currently registered

| Item | Owner | Removed at |
|---|---|---|
| `l0-conformance` stubs in `ci.yml` | platform | G6 |
| `models.piper_tr_dfki` licence | sensory | G6c |
| `models.piper_tr_dfki_config` licence | sensory | G6c |
| `models.wake_bootstrap` licence (NC ambiguity) | sensory | G6a — self-liquidating |
| `MASTER_PLAN_v1.md` markdown lint | architecture | never — frozen record |
| `ADR-0004` section shape | architecture | never — superseded record |
| `run_gates.sh` / `verify_artifacts.sh` strict mode | platform | never — must survive non-zero exits |

---

## Scope exclusions

Two directories are excluded from the hygiene gates, for one reason each.

| Excluded | From | Why |
|---|---|---|
| `ci/` | `no-latest`, `no-pending`, `no-todo`, `shell` | Gates and their self-test necessarily **contain** the strings they hunt. Flagging them would invite weakening the pattern — which is how a gate quietly stops catching real violations |
| **`ci/`** | ~~`secrets`~~ | **REMOVED — AUD-C02.** A secret-scanning gate needs the *pattern*, never a *matching literal*. The exclusion was proven to hide AWS keys, GitHub tokens and PEM private keys placed anywhere under `ci/`. `gate_secrets` now has **no path exclusions at all** and scans its own source and its own policy file. See [Secret_Scanning_Design.md](Secret_Scanning_Design.md) |
| `*.md` | `no-latest`, `no-pending`, `docker-digests` | Prose must be able to quote a rejected practice. `MASTER_PLAN_v2` §3 discusses `:latest` precisely to explain why it is banned |

Both exclusions narrow *where* a rule applies, never *what* it forbids. The gates police
what runs; documentation about what runs is a different concern.

---

## Proving the gates bite

`bash ci/self_test.sh` plants a known violation for eight gates and asserts each is
rejected, then verifies its own cleanup.

**8/8 caught.** Two gates had real bugs that only the self-test surfaced — a gate that has
never rejected anything is unproven, however carefully it was written.

---

## Current state

```
15 pass · 1 fail by design · 0 broken
```

`artifacts` (`ART-000`) is red: one image digest is unresolved and ADR-0013 blocks G0
until it reaches zero. See [Artifact_Verification_Report.md](Artifact_Verification_Report.md) §5.

A red build that is red for a known, owned, documented reason is a working pipeline. The
failure mode worth fearing is a green build that means nothing.

---

*Generated from the `g.fail(...)` calls in `ci/gates/`. Regenerate rather than hand-edit.*
