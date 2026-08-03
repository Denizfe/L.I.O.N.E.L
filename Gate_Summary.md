# Gate Summary

**Execution date:** 2026-08-02 · **Source:** clean-checkout simulation (`/tmp/ci_sim`, 156 tracked files)
**Dependencies:** `pyyaml`, `jsonschema`, `grpcio-tools` — exactly as the workflow declares

## Result

```
16 gates   ·   14 PASS   ·   2 FAIL   ·   0 BROKEN
18 jobs    ·   15 PASS   ·   2 FAIL   ·   1 STUB (reports green)
self-test  ·   9/9 planted violations caught
```

**Only one of the two failures blocks G0.**

---

## Per-gate results

| # | Gate | Exit | Checks | Violations | Enforces | Result |
|---|---|---|---|---|---|---|
| 1 | `structure` | 0 | 24 | 0 | ADR-0011, MASTER_PLAN §8 | ✅ PASS |
| 2 | `adr` | 0 | 195 | 0 | ADR-0016 | ✅ PASS |
| 3 | `contracts` | 0 | 34 | 0 | ADR-0003, ADR-0009 | ✅ PASS |
| 4 | `jsonschema` | 0 | 155 | 0 | ADR-0027 | ✅ PASS |
| 5 | `protobuf` | 0 | 25 | 0 | ADR-0028, ADR-0006 | ✅ PASS |
| 6 | **`artifacts`** | **1** | 16 | **1** | ADR-0013 | ❌ **FAIL** |
| 7 | `docker-digests` | 0 | 11 | 0 | ADR-0013, ADR-0020 | ✅ PASS |
| 8 | `no-latest` | 0 | 1 | 0 | ADR-0013 | ✅ PASS |
| 9 | `no-pending` | 0 | 1 | 0 | ADR-0013 | ✅ PASS |
| 10 | **`no-todo`** | **1** | 11 | **10** | MASTER_PLAN §12 | ❌ **FAIL** |
| 11 | `secrets` | 0 | **154** | 0 | ADR-0015, ADR-0022 | ✅ PASS |
| 12 | `licenses` | 0 | 13 | 0 | ADR-0013 | ✅ PASS |
| 13 | `markdown` | 0 | 48 | 0 | — | ✅ PASS |
| 14 | `dependencies` | 0 | 1 | 0 | ADR-0013 | ✅ PASS |
| 15 | `shell` | 0 | 4 | 0 | ADR-0011, ADR-0014 | ✅ PASS |
| 16 | `architecture` | 0 | 19 | 0 | 11 ADRs | ✅ PASS |

**Totals:** 552 checks · 11 violations · 0 gate errors

---

## Workflow jobs

| Job | Result |
|---|---|
| `structure` `adr` `contracts` `jsonschema` `protobuf` | ✅ PASS |
| `artifacts` | ❌ **FAIL** |
| `docker-digests` `licenses` `dependencies` | ✅ PASS |
| `no-latest` `no-pending` | ✅ PASS |
| `no-todo` | ❌ **FAIL** |
| `secrets` `markdown` `shell` `architecture` | ✅ PASS |
| `gate-self-test` | ✅ PASS — 9/9 |
| `l0-conformance` | ⚠️ **STUB — exits 0, reports SUCCESS, asserts nothing** |

---

## G0 impact

| Gate | Blocks G0? | Authority |
|---|---|---|
| `artifacts` | **YES** | ADR-0013 `[RECORD]`: fails closed at G0 on any `UNRESOLVED` entry |
| `no-todo` | **No** | No G0 criterion references TODO hygiene |

MASTER_PLAN_v2's Phase 0 DoD requires **"CI runs and reports"** and states *"failing is
fine; present is mandatory"*. **A green pipeline is not a G0 requirement.** Only the
criteria named in the DoD and in individual ADRs are.

---

## Notable observations

**`secrets` scanned 154 checks.** Under a clean checkout with no path exclusions, confirming
the AUD-C02 remediation holds. Before that fix the gate reported 7.

**No gate exited 2.** Every gate ran to completion using only `pyyaml`, `jsonschema` and
`grpcio-tools`. The pipeline is hermetic — no network, no Docker, no project dependencies.

**Job independence works.** Only `l0-conformance` declares `needs:`. Both failures surfaced
in one run rather than masking the other fourteen.

**Four gates report ≤ 1 check** — `no-latest`, `no-pending`, `dependencies`, and `no-todo`
when clean. This is `AUD-M02`: the counter increments on violations, not files examined, so
a gate that scanned nothing is indistinguishable from one that scanned everything cleanly.
`secrets` is the exception — its counter was corrected during the AUD-C02 work, which is why
it reports 154.

**`l0-conformance` is green and hollow.** See `CI_Execution_Report.md` §4.1.

---

*Detail on both failures: `Failed_Gates.md`. Full execution narrative: `CI_Execution_Report.md`.*
