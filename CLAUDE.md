# L.I.O.N.E.L — working rules

A local-first voice assistant whose defining constraint is an **offline autonomy guarantee**
(ADR-0007). Phase 0 is complete and frozen at `architecture-1.2.0`. Phase 1 may begin.

**Right now this repository contains no runtime code.** It is an architecture — 31 ADRs, 27
JSON Schemas + 3 protobuf contracts, a pinned artifact lock — and a policy pipeline that
enforces them: 20 gates, 137 rules, 23 CI jobs.

---

## The four rules that will bite you

These are not style preferences. Each is enforced, and the first two are enforced by a
human, not a gate.

### 1. Never commit, push or tag without being asked

`Architecture_Freeze.md` §5: **"No autonomous commit or push — ever."** This binds an agent
exactly as it binds a person. Ask once, covering the whole chain (commit + push + tag), so
the work is not interrupted at each step.

Commits use the `[LIONEL-CORE]` prefix.

### 2. A new dependency needs an ADR and Efe's approval

`Architecture_Freeze.md` §4. Also: any new subsystem or technology, any change to a
contract's `stable` surface, the tier/trust/plane models, capability governance fields, any
**relaxation** of a gate, and the phase plan.

`pyproject.toml` declares only packages an Accepted ADR already chose, each naming its ADR
in a comment. Adding one because it is obviously needed is precisely the failure §4 exists
to prevent.

**Permitted without an ADR:** implementation under `src/lionel/` conforming to frozen
contracts · tests · gate work that enforces an *existing* decision more completely ·
regenerating generated documents · errata · artifact version bumps within an existing
artifact.

### 3. An Accepted ADR is append-only

`ADR-0029`. The `Status` line may be edited. **The body may not.** Three operations:

| | When | How |
|---|---|---|
| **Supersede** | The decision changes | New ADR; original's `Status` gets a forward link. Original text untouched |
| **Amend** | Adds scope, contradicts nothing | Append `## Amendment — YYYY-MM-DD` |
| **Erratum** | Text was wrong; the decision was always this | Append `## Erratum — YYYY-MM-DD`, **quoting the original verbatim in a blockquote** |

The quote is the mechanism, not decoration — it is the only thing separating a correction
from a rewrite. `ADR-009` checks the shape. Rule 2's quote requirement is enforced from
`adr.errata_quote_required_from` (2026-08-11); two earlier sections are grandfathered and
reported as notes on every run.

If a sentence in an Accepted ADR becomes false — **including its own `Status`** — append an
Erratum. Do not edit the sentence. (Every ADR accepted on 2026-08-11 needed exactly this.)

### 4. Changing the architecture moves the checksum

`Architecture_Freeze.md` §2 records a SHA-256 over 72 files in five groups. Touch any of
them and `gate_checksum` goes red until §2 is updated and the version bumped (§5 step 7).

**The checksum set:**

```
docs/decisions/ADR-*.md            contracts/{core,mcp,events,media}/v1/*.schema.json
contracts/grpc/v1/*.proto          contracts/MANIFEST.json
config/**/*.toml   config/*.json   ci/policy/policy.yaml
artifacts.lock.yaml                MASTER_PLAN_v2.md
```

`Architecture_Freeze.md` is **not** in the set, so recording the new value does not perturb
it — no fixed point to chase. Record it **last**.

> Line endings are part of the checksum. `.gitattributes` sets `* text=auto eol=lf`. That
> line is load-bearing: before it existed, `*.proto` was unpinned, a Windows clone got CRLF,
> and the same commit produced two different checksums for eight days.

---

## Verify before you claim anything

```bash
bash ci/run_gates.sh                    # 20/20, 0 broken
bash ci/run_gates.sh <gate>             # one gate
bash ci/self_test.sh                    # 22/22 assertions, 20/20 gates covered
python3 scripts/architecture_checksum.py --verify
python3 scripts/generate_ci_docs.py --check
```

Requires `pyyaml`, `jsonschema` and **`grpcio-tools`**. Without the last one the `protobuf`
gate exits **2** — a *broken gate*, not a passing repository, and the runner says so.

**Exit codes are a contract:** `0` pass · `1` policy violation (fix the repo) · `2` the gate
itself is broken (fix the gate). Never collapse 1 and 2.

---

## Phase 0 discipline

`STRUCT-004` forbids `.py` under `src/lionel/`. That ban lifts when Phase 1 starts; until
then a stray runtime file fails the build. `ci/` and `scripts/` are tooling, not runtime, and
are unaffected.

`ARCH-001` forbids `src/lionel/capabilities/shell/` from ever existing again (ADR-0011).

---

## Generated documents — do not hand-edit

`CI_Inventory.md` and `Policy_Gates.md` come from `scripts/generate_ci_docs.py`. Run it after
changing any gate; `gate_generated_docs` fails otherwise.

Both documents said "regenerate rather than hand-edit" for months while no generator existed.
They drifted to 16 gates against 17, 88 rules against 127, and `l0-conformance` — the
keystone gate — absent from the rule catalogue entirely.

**Hand-written documents that assert counts are still unenforced**, and they go stale fast:
`CI_Architecture.md` §8, `Architecture_Risk_Register.md`, `Phase0_Final_Signoff.md`,
`Phase1_Entry_Checklist.md`, `Architecture_Freeze.md`. ADR-0030's Costs section records this
as an open gap. Use the `doc-claim-auditor` agent before a version bump.

---

## Adding a gate

`CI_Architecture.md` §7 — seven steps, of which step 6 is the one that gets skipped:

1. ADR first · 2. config in `ci/policy/policy.yaml` · 3. `ci/gates/gate_<name>.py` using
`_lib.Gate` · 4. add to `ORDER` in `ci/run_gates.sh` · 5. job in `.github/workflows/ci.yml` ·
6. **planted violation in `ci/self_test.sh`** · 7. regenerate the docs

`gate-coverage` now fails if step 6 is skipped. The `/add-gate` skill walks the whole thing.

Every `Finding` carries four things: what is wrong, where, **why the rule exists** (cite the
ADR), and how to fix it. A gate that prints `FAIL: rule R-014` has moved the work of
understanding onto whoever reads the log, at the least convenient moment.

---

## Platform

Windows + Git Bash is the **host runtime**, not a developer convenience (ADR-0002,
ADR-0014). Turkish is a first-class locale (ADR-0023) — `tr`, `grep -i` and `[[ = ]]` consult
`LC_CTYPE`, so shell code is where the dotted/dotless `İ`/`ı` failure lives. Python's
`str.lower()` is Unicode-based and safe.

CI covers `ubuntu-latest`, `windows-latest` (Git Bash) and `tr_TR.UTF-8`. **If the Turkish
job fails, the shell is wrong. Do not relax the locale.**

Gates must not assume a UTF-8 console: `ci/gates/_lib.py` reconfigures stdout, because
Windows defaults to cp1252 and every gate used to die in `report_and_exit` *after* passing
its checks.

---

## Known open items

| | |
|---|---|
| **Turkish TTS blocks distribution** | `tr_TR-dfki-medium` is **CC-BY-NC-SA-4.0** and is the only Turkish voice. Personal use is unaffected. Replacing it needs an ADR amending ADR-0017. Risk **R-A15**, Major |
| **ADR-0029 rule 1 has no gate** | The append-only rule is enforced by a `PreToolUse` hook, which sees `Edit`/`Write` but not `sed` through `Bash`. A guardrail, not a proof |
| **Hand-written count claims** | See above. `generated-docs` covers only documents that have a generator |

---

## Where things are

```
docs/decisions/          31 ADRs + README index (ARCH-016 requires the index be complete)
contracts/               27 JSON Schemas + 3 protobuf, 5 planes, MANIFEST.json
ci/gates/                20 gates + _lib.py (Finding, exit codes) + _checksum.py
ci/policy/policy.yaml    ALL thresholds, allowlists and registries
ci/run_gates.sh          ORDER is the canonical gate list
ci/self_test.sh          plants violations; proves the gates bite
scripts/                 architecture_checksum.py · generate_ci_docs.py · verify_artifacts.sh
MASTER_PLAN_v2.md        11 gated phases, G0–G10. Phase 1 scope is §10
Architecture_Freeze.md   the frozen state, the checksum, and the change-control rules
```

Every exemption anywhere in this repo carries an **owner** and a **route to removal**. One
with neither is not an exemption; it is a silently lowered standard.
