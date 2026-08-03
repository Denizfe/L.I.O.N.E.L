# CI Execution Report

**Full pipeline execution as a clean contributor.** Audit only — nothing was fixed.

| | |
|---|---|
| Date | 2026-08-02 |
| Method | Clean-clone simulation + full gate execution from a reconstructed checkout |
| Gates executed | **16 / 16** |
| Workflow jobs simulated | **18 / 18** |
| Self-test | executed |
| Repository modified | **No** — all execution in `/tmp/ci_sim`; three report files added |

## Headline

| | |
|---|---|
| **Gates** | **14 pass · 2 fail · 0 broken** |
| **Workflow jobs** | **15 pass · 2 fail · 1 stub (reporting green)** |
| **Self-test** | **9 / 9 planted violations caught** |
| **Clean `git clone`** | **Yields 0 files** |

---

## 1. The finding that dominates everything below

**`git init` has run. There are 0 commits and 0 tracked files.**

```
$ git rev-list --count HEAD     → 0
$ git ls-files | wc -l          → 0
$ git ls-files --others | wc -l → 156
$ git clone . /tmp/x
  warning: You appear to have cloned an empty repository.
  files in clone: 0
```

**A clean contributor cloning this repository receives nothing.** Every workflow job begins
with `actions/checkout@v4`; against an empty repository each would check out an empty tree
and fail at the first `run:` step — not because a gate found a problem, but because there
are no files to examine.

This means:

- **GitHub Actions has still never executed.** Workflows trigger on `push`; nothing has been
  pushed.
- **`.gitattributes` has still never been applied.** LF normalisation takes effect on first
  `git add`. The tree happens to be clean (0 CRLF files, verified) but that is the authoring
  environment behaving, not the control working.
- **`.gitignore` has still never been exercised.**

`AUD-C01` is therefore **partially addressed**: the `.git` directory now exists, which was
the smaller half. The repository is still empty, which was the substantive half.

Everything in §3–§5 is therefore reported as **what CI will do once the tree is committed**,
not what it has done.

---

## 2. Method

Two execution modes, run separately.

### Mode A — true clean contributor

`git clone` into a scratch directory. **Result: 0 files.** Nothing further could be run.

### Mode B — post-commit simulation

Because Mode A yields nothing, I reconstructed the tree CI *would* see after a commit:

1. `git add -A --dry-run` (non-mutating) to enumerate exactly what git would track — **156 files**
2. Copied only those files into `/tmp/ci_sim`, honouring `.gitignore`
3. Installed only the dependencies the workflow declares: `pyyaml`, `jsonschema`, `grpcio-tools`
4. Executed all 16 gates, the self-test, and every workflow job's `run:` steps from that tree

This is the closest faithful reproduction of a clean CI run available without pushing.

### Checkout hygiene — verified clean

| Check | Result |
|---|---|
| `__pycache__` in the checkout | **0** — correctly ignored |
| `models/` in the checkout | **0** — correctly ignored |
| `data/`, `logs/`, `backups/` ignored | ✅ |
| Any CI-required file excluded by `.gitignore` | **none** — all 11 critical paths committable |
| Hardcoded machine paths in gate code | **none** — all paths repo-relative |
| Script executable bits | all `+x`; workflow invokes via `bash` regardless |

`vendor/` is **not** ignored (only `vendor/whisper.cpp/` is). Harmless today — the directory
is empty — but it will track the submodule parent once whisper.cpp lands. Informational.

---

## 3. Gate execution — all 16

| Gate | Exit | Violations | Checks | Result |
|---|---|---|---|---|
| `structure` | 0 | 0 | 24 | PASS |
| `adr` | 0 | 0 | 195 | PASS |
| `contracts` | 0 | 0 | 34 | PASS |
| `jsonschema` | 0 | 0 | 155 | PASS |
| `protobuf` | 0 | 0 | 25 | PASS |
| **`artifacts`** | **1** | **1** | 16 | **FAIL** |
| `docker-digests` | 0 | 0 | 11 | PASS |
| `no-latest` | 0 | 0 | 1 | PASS |
| `no-pending` | 0 | 0 | 1 | PASS |
| **`no-todo`** | **1** | **10** | 11 | **FAIL** |
| `secrets` | 0 | 0 | **154** | PASS |
| `licenses` | 0 | 0 | 13 | PASS |
| `markdown` | 0 | 0 | 48 | PASS |
| `dependencies` | 0 | 0 | 1 | PASS |
| `shell` | 0 | 0 | 4 | PASS |
| `architecture` | 0 | 0 | 19 | PASS |

**No gate exited 2.** Every gate ran to completion with only the declared dependencies —
the pipeline is self-contained and hermetic, as designed.

`secrets` reporting **154 checks** confirms the AUD-C02 remediation holds under a clean
checkout: it is scanning the full tree with no path exclusions.

Full detail in `Failed_Gates.md`. Per-gate roll-up in `Gate_Summary.md`.

---

## 4. Workflow job simulation — all 18

| Job | Result | Note |
|---|---|---|
| `structure` `adr` `contracts` `jsonschema` `protobuf` | PASS | |
| **`artifacts`** | **FAIL** | red by design (ADR-0013) |
| `docker-digests` `licenses` `dependencies` | PASS | |
| `no-latest` `no-pending` | PASS | |
| **`no-todo`** | **FAIL** | 10 violations, all in audit prose |
| `secrets` `markdown` `shell` `architecture` | PASS | |
| `gate-self-test` | PASS | 9/9 planted violations caught |
| **`l0-conformance`** | **STUB → reports SUCCESS** | see below |

**15 pass · 2 fail · 1 stub.**

### 4.1 `l0-conformance` reports green while asserting nothing

```yaml
- name: Assert no network egress during the L0 suite
  run: echo "STUB — needs the sensory harness (ADR-0027)…"
- name: Wake → STT → brain(ollama) → tools → TTS, EN and TR, no microphone
  run: echo "STUB — Phase 6…"
```

Every step is `echo`, so the job exits 0 and GitHub reports **SUCCESS**.

This is the keystone gate of ADR-0007 — the one whose entire purpose is that offline
operation cannot erode unnoticed — and it currently produces a **green checkmark for doing
nothing.**

The intent was right and is documented in the workflow comments (*"failing later is fine —
ABSENT is not"*). But there is a third state the comment does not consider: **present,
green, and vacuous**, which is worse than absent. An absent gate is visibly missing; a green
stub is indistinguishable from a passing gate, and after a few months nobody remembers it is
hollow.

Recorded as an observation, not a gate failure. **Recommend the stub steps `exit 1` with a
clear "not implemented until Phase 6" message**, so the job is honestly red until it is
real. That matches `l0.toml`'s own stance — `network_allowed: false` is described there as
*"asserted by the conformance suite, not merely documented"*, and no suite currently asserts it.

### 4.2 Job independence confirmed

Only `l0-conformance` declares `needs:`. The 16 policy gates are independent, so both
failures surfaced in a single run rather than masking the other fourteen results.

---

## 5. Self-test

```
SELF-TEST PASS  9/9 planted violations caught
```

Executed from the simulated checkout. Covers 8 of 16 gates plus the secrets regex
self-test. `AUD-M06` (8 gates untested) remains open and was not re-examined here.

---

## 6. Verdict on G0

**Two gates fail. Only one of them blocks G0.**

| Gate | Blocks G0? | Authority |
|---|---|---|
| `artifacts` | **YES** | ADR-0013 `[RECORD]` clause: the lockfile fails closed at G0 on any `UNRESOLVED` entry |
| `no-todo` | **No** | No G0 criterion references TODO hygiene |

The distinction rests on MASTER_PLAN_v2's Phase 0 DoD, which says **"CI runs and reports"**
and **"CI skeleton with the L0 gate wired (failing is fine; present is mandatory)"**.

**G0 does not require a green pipeline.** It requires a pipeline that runs, plus the
specific criteria named in the DoD and in individual ADRs. `no-todo` is hygiene; its failure
is noise against the G0 question. `artifacts` is a named G0 criterion; its failure is a
blocker.

### Remaining G0 blockers

| ID | Blocker | Status |
|---|---|---|
| **AUD-C01** | Repository is empty — 0 commits, CI has never run | **OPEN** — `git init` done, nothing committed |
| **AUD-M01** | `images.github_mcp` digest unresolved | **OPEN** — `artifacts` gate red |

Both were open before this execution and remain open. **This run produced no new blocker.**

That is the useful result: the pipeline is sound and self-contained, 14 of 16 gates pass
from a clean checkout with only declared dependencies, and the two failures are the two
already-known items — one deliberate, one cosmetic.

---

## 7. What this run does not tell you

- **It is a simulation, not a CI run.** I reconstructed the checkout faithfully and
  installed only declared dependencies, but no GitHub Actions run exists. Until one does,
  runner-specific behaviour — `actions/checkout`, Python setup, the `ubuntu-latest` image —
  is unverified.
- **No Windows or Turkish-locale execution.** All jobs are `ubuntu-latest` (`AUD-M05`).
- **`AUD-M02`, `M03`, `M04`, `M06`, `M07` and the Minor findings were not re-examined.**
  This was an execution run, not a re-audit.

---

*Nothing was fixed. `CI_Execution_Report.md`, `Gate_Summary.md` and `Failed_Gates.md` are
new files; no existing repository file was modified.*
