# CI Execution Report

**Full pipeline execution from a genuine clean clone.** Audit only — nothing was fixed.

| | |
|---|---|
| Date | 2026-08-03 |
| Method | `git clone` → declared deps only → every gate, every job, from the clone |
| Repository | 4 commits · `main` · remote `origin` → `github.com/Denizfe/L.I.O.N.E.L` |
| Gates executed | **17 / 17** |
| Workflow jobs simulated | **18 / 18** |
| Checks run | **788** |
| Repository modified | **No** — execution in `/tmp/cc/repo`; three reports overwritten in place |

## Headline

| | |
|---|---|
| **Gates** | **13 pass · 4 fail · 0 broken** |
| **Workflow jobs** | **14 pass · 4 fail · 0 stub** |
| **Self-test** | **9 / 9 planted violations caught** |
| **Clean `git clone`** | **161 files — works** |

---

## 1. The blocker that dominated the last report is gone

Previous run: `git init` had executed but there were **0 commits and 0 tracked files**, so a
clean clone yielded nothing and every workflow job would have failed at checkout.

**That is resolved.**

```
$ git rev-list --count HEAD   → 4
$ git ls-files | wc -l        → 161
$ git status --porcelain      → (clean)
$ git clone . /tmp/cc/repo    → 161 files
$ git rev-parse @{u}          → origin/main
```

Commit history:

```
30285c0  2026-08-03  Merge remote repository
352bc12  2026-08-03  Phase 0: Architecture Baseline
69d0234  2026-08-03  Initial commit
0b51e4d  2026-08-03  First commit
```

### What this unlocked, verified rather than assumed

| Control | Previous | **Now** |
|---|---|---|
| Clean clone yields a working tree | ❌ 0 files | ✅ **161 files** |
| `.gitattributes` LF normalisation | never applied | ✅ **applied — `git ls-files --eol` reports 161/161 `i/lf`, 0 CRLF** |
| `.gitignore` exercised | never | ✅ **`__pycache__` 0 · `models/` 0 · `data|logs|backups` 0 · `.env` absent** |
| Every CI-required file tracked | unknown | ✅ 17 gates, policy, workflow all present in the clone |
| Remote configured | none | ✅ `origin` + upstream `origin/main` |

**AUD-C01 is substantively addressed.** The repository is committed, pushed, and a clean
contributor receives a working tree. §6 records the one residual part.

---

## 2. Method — a real clean-contributor run

Unlike the previous report, no simulation was needed.

1. `git clone` the repository into a scratch directory → 161 files
2. Installed **only** what the workflow declares: `pyyaml`, `jsonschema`, `grpcio-tools`
3. Executed all 17 gates from the clone
4. Executed `ci/self_test.sh`
5. Executed the L0 egress-guard proof
6. Executed every `run:` step of all 18 workflow jobs

No gate required network, Docker, or any project dependency. **The pipeline is hermetic.**

---

## 3. Gate execution — all 17

| Gate | Exit | Violations | Checks | Result |
|---|---|---|---|---|
| `structure` | 0 | 0 | 24 | ✅ PASS |
| `adr` | 0 | 0 | 195 | ✅ PASS |
| `contracts` | 0 | 0 | 34 | ✅ PASS |
| `jsonschema` | 0 | 0 | 155 | ✅ PASS |
| `protobuf` | 0 | 0 | 25 | ✅ PASS |
| **`artifacts`** | **1** | **1** | 16 | ❌ FAIL |
| `docker-digests` | 0 | 0 | 11 | ✅ PASS |
| `no-latest` | 0 | 0 | 1 | ✅ PASS |
| `no-pending` | 0 | 0 | 1 | ✅ PASS |
| **`no-todo`** | **1** | **33** | 34 | ❌ FAIL |
| `secrets` | 0 | 0 | 159 | ✅ PASS |
| `licenses` | 0 | 0 | 13 | ✅ PASS |
| **`markdown`** | **1** | **1** | 52 | ❌ FAIL |
| `dependencies` | 0 | 0 | 1 | ✅ PASS |
| `shell` | 0 | 0 | 4 | ✅ PASS |
| `architecture` | 0 | 0 | 19 | ✅ PASS |
| **`l0-conformance`** | **1** | **6** | 44 | ❌ FAIL |

**788 checks · 41 violations · 0 gate errors.**

Detail in `Failed_Gates.md`. Roll-up in `Gate_Summary.md`.

---

## 4. Workflow jobs — all 18

| Job | Result |
|---|---|
| `structure` `adr` `contracts` `jsonschema` `protobuf` | ✅ PASS |
| **`artifacts`** | ❌ FAIL |
| `docker-digests` `licenses` `dependencies` | ✅ PASS |
| `no-latest` `no-pending` | ✅ PASS |
| **`no-todo`** | ❌ FAIL |
| `secrets` | ✅ PASS |
| **`markdown`** | ❌ FAIL |
| `shell` `architecture` | ✅ PASS |
| `gate-self-test` | ✅ PASS — 9/9 |
| **`l0-conformance`** | ❌ **FAIL — and this is progress** |

**14 pass · 4 fail · 0 stub.**

### 4.1 `l0-conformance` is no longer hollow

The previous report's headline observation was that this job ran two `echo` statements,
exited 0, and reported a green checkmark for asserting nothing.

**It now runs a real gate.** Two steps:

```
Prove the network egress guard blocks outbound connections  → exit 0
  egress guard active: outbound connection blocked: ('example.invalid', 80)
  recorded attempts: ["socket.create_connection(('example.invalid', 80))"]

L0 offline conformance                                       → exit 1
  6 violations across 44 checks
```

The guard is proven armed **before** the gate's findings are trusted. **A job that was
falsely green is now honestly red** — that is the single most valuable delta in this run.

---

## 5. Change since the previous execution report

| Measure | Previous | Now | |
|---|---|---|---|
| Gates | 16 | **17** | L0 gate added |
| Gates passing | 14 | **13** | |
| Gates failing | 2 | **4** | |
| Jobs passing | 15 | **14** | |
| Jobs failing | 2 | **4** | |
| Jobs stubbed | 1 | **0** | ✅ stub eliminated |
| `no-todo` violations | 10 | **33** | ⚠️ +23 |
| `markdown` violations | 0 | **1** | ⚠️ new |
| `l0-conformance` | STUB (green) | **FAIL (real)** | ✅ |
| Clean clone | 0 files | **161 files** | ✅ |

**Two of the four failures are new, and both were caused by this audit process.** §5.1.

### 5.1 The audit output is now the largest source of CI noise

Every `no-todo` and `markdown` violation is in a document **produced by the audit or review
process itself**:

| File | `no-todo` hits | Origin |
|---|---|---|
| `Failed_Gates.md` | **21** | audit output (previous run) |
| `Phase0_Audit_Report.md` | 6 | audit output |
| `Architecture_Risk_Register.md` | 2 | audit output |
| `Phase0_Blockers.md` | 1 | audit output |
| `Gate_Summary.md` | 1 | audit output |
| `CI_Execution_Report.md` | 1 | audit output |
| `ADR0013_Review.md` | 1 | review output |

The single `markdown` violation is `Failed_Gates.md:199` — a heading jump in a file this
process generated.

**This is a feedback loop, and it is compounding.** Each audit round produces documents that
discuss `TODO` governance and forbidden tokens as their subject matter. Those documents are
scanned. Violations rise. The next round documents the rise, adding more prose. `no-todo`
went 10 → 33 in one cycle, and 21 of the 33 come from a single generated file.

This is not a defect in the gate — it is correctly reporting what it was scoped to scan. It
is a **scoping gap**: `no-latest` and `no-pending` both exclude `.md` wholesale on the
stated rationale that *"gates police executable config, not prose that documents a rejected
practice."* `no-todo` and `markdown` never received that treatment.

Left unaddressed, these two gates become permanently red and stop being read — the exact
failure mode `CI_Architecture.md` warns about when it argues against a warnings tier.

**Not fixed here.** Remediation in `Failed_Gates.md`.

---

## 6. Verdict on G0

**Four gates fail. Two block G0.**

| Gate | Blocks G0? | Authority |
|---|---|---|
| `artifacts` | **YES** | ADR-0013 `[RECORD]`: fails closed at G0 on any `UNRESOLVED` entry |
| `l0-conformance` | **YES** | ADR-0007: L0 conformance is a blocking gate on every release |
| `no-todo` | No | No G0 criterion references TODO hygiene |
| `markdown` | No | No G0 criterion references heading structure |

MASTER_PLAN_v2's Phase 0 DoD requires *"CI runs and reports"* and states *"failing is fine;
present is mandatory"*. **A green pipeline is not a G0 requirement** — only the criteria the
DoD and individual ADRs name.

### Blocker status

| ID | Blocker | Previous | **Now** |
|---|---|---|---|
| **AUD-C01** | Repository uncommitted; CI never run | OPEN | ⚠️ **Mostly resolved** — committed, pushed, clean clone works. Residual: no evidence of an actual GitHub Actions *run* (no run URL, no status checks observable from here) |
| **AUD-M01** | `images.github_mcp` digest unresolved | OPEN | **OPEN** — `artifacts` red |
| **NEW** | L0 conformance violations | n/a (stub was green) | **OPEN** — 6 violations, see below |

### The new L0 blocker is a discovery, not a regression

`l0-conformance` reports 6 violations, and 5 of them are one finding:

**No capability in `config/capabilities.registry.json` declares `requires_network`.**

ADR-0007's exclusion of network-dependent capabilities at L0 exists in the ADR, in the
lockfile notes, and in three audit reports — **and nowhere machine-readable**. Absence of a
field is not a declaration of `false`.

Every prior audit, including mine, repeated "the GitHub capability is excluded at L0" as
established fact. **Nothing in the repository established it.** The stub concealed this
entirely; the real gate found it on first execution.

---

## 7. What this run establishes and what it does not

**Establishes:**
- A clean contributor can clone and run the entire pipeline with three pip packages
- `.gitattributes` and `.gitignore` now demonstrably work — 161/161 LF, no build artefacts
- The pipeline is hermetic: no network, no Docker, no project dependencies
- The self-test proves 9 gates reject planted violations
- The L0 egress guard is armed and provably blocks outbound connections

**Does not establish:**
- **That GitHub Actions has run.** Commits are pushed to `origin/main`, but no run URL or
  status check is observable from here. This is the residual half of AUD-C01
- **Windows or Turkish-locale behaviour** — all jobs are `ubuntu-latest` (AUD-M05)
- Runtime L0 behaviour — the gate is static conformance only

**Not re-examined:** AUD-M02, M03, M04, M06, M07 and the Minor findings. This was an
execution run, not a re-audit.

---

*Nothing was fixed. `CI_Execution_Report.md`, `Gate_Summary.md` and `Failed_Gates.md` were
overwritten with this run's results; no other repository file was modified.*
