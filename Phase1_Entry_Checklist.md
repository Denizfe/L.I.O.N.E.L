# Phase 1 Entry Checklist

**Implementation prerequisites only.** No architecture work. No planning. No research.

| | |
|---|---|
| Gate | G0 → G1 |
| Status | **UNBLOCKED** — item 1 closed 2026-08-10 |
| Items | 9 |
| Done | 8 |
| Blocking | 0 |

---

## BLOCKING — must complete before any Phase 1 work

### ☑ 1. Commit and push the Phase 0 architecture — **DONE 2026-08-10**

```
commit 0066cb23c0447070714ab11df270c2c955ac35c1
        [LIONEL-CORE] Phase 0: architecture freeze 1.0.0
tag     architecture-1.0.0
```

Twelve paths — exactly the set `Phase0_Final_Signoff.md` §2.1 enumerated. Verified against
a clean clone:

| Acceptance criterion | Result |
|---|---|
| Clean clone → 17/17 gates | ✅ 17 / 17, 0 broken |
| `artifacts.lock.yaml` reads 13/0 | ✅ 13 resolved / 0 unresolved |
| 5 of 5 capabilities declare `requires_network` | ✅ 5 / 5 |
| Self-test | ✅ 10 / 10 |
| Architecture checksum reproduces | ✅ `sha256:fab0610a…` |

Commit SHA and checksum recorded in `Architecture_Freeze.md` §8. **Clone the tag, not the
commit** — §8.3 explains why.

> Requires `pyyaml`, `jsonschema` and **`grpcio-tools`**. Without the last one the
> `protobuf` gate exits 2, which the runner correctly reports as a broken gate rather than
> a passing repository.

---

## NON-BLOCKING — required during Phase 1, before G1

### ☑ 2. Create `pyproject.toml` — **DONE 2026-08-10, deliberately minimal**

`bash ci/run_gates.sh dependencies` passes. Every dependency carries a bound (`DEP-001`);
`requests` is absent (`DEP-002`) and `httpx` is declared.

**Read this before adding to it.** MASTER_PLAN_v2 has no §3.1 dependency list — the
reference in the original checklist pointed at a section that does not exist, and the plan
names *technologies* (Qdrant, Kokoro, Piper, faster-whisper, openWakeWord, Ollama) whose
Python client libraries have never been chosen. Choosing them here would have been a
technology decision, and `Architecture_Freeze.md` §4 requires an ADR and Efe's approval for
any new dependency.

So the manifest declares only what an Accepted ADR already decided, each entry naming its
ADR:

| Package | Decided by |
|---|---|
| `opentelemetry-{api,sdk,exporter-otlp-proto-grpc}` | ADR-0019 |
| `structlog` | ADR-0019 |
| `grpcio`, `protobuf` | ADR-0028, ADR-0006 |
| `psutil` | ADR-0014 |
| `httpx` | ADR-0015; named by `DEP-002` |
| `pyyaml`, `jsonschema`, `grpcio-tools` | `[project.optional-dependencies].ci` — what the gates need |

The memory and sensory clients arrive with the phases that build against them, G2 and G6,
each with its ADR. **A package appearing here without an ADR is the failure mode `§4`
exists to prevent.**

### ☑ 3. Generate `uv.lock` — **DONE 2026-08-10**

```bash
uv lock              # 27 packages resolved
uv sync --extra ci   # reproduces the environment, including the gates' dependencies
```

Verified: `bash ci/run_gates.sh` → 17/17 and `bash ci/self_test.sh` → 10/10 against the
synced environment. Policy's `lockfile_required_at: G1` is satisfied.

### ☐ 4. Resolve the Piper voice licence

`artifacts.lock.yaml` → `models.piper_tr_dfki.license` reads *"verify per MODEL_CARD before
release"*. Registered to `sensory` for G6c, but the MODEL_CARD is readable now.

**Acceptance:** an SPDX identifier replaces the deferral, or the artifact is replaced.

### ☑ 5. Add `l0-conformance` to `ci/self_test.sh` — **DONE 2026-08-10**

Plants `network_allowed = true` in `config/tiers/l0.toml`, asserts `L0-OFFLINE-002`.
Self-test **10/10**. Closes Finding M1.

`config/tiers/l0.toml` is inside the architecture checksum set, so the test restores it from
a byte-exact backup and verifies the restoration rather than assuming it.

**Still open, tracked into Phase 1:** the self-test covers 9 of 17 gates. Every gate should
eventually have to reject something.

### ☑ 6. Regenerate the drifted generated documents — **DONE 2026-08-10**

`scripts/generate_ci_docs.py` derives both from source and takes `--check`. Both documents
ended with "Regenerate rather than hand-edit" while no generator existed, which is why they
drifted in the first place.

Authoritative counts: **17 gates · 127 rules · 20 workflow jobs.**

> 127 supersedes 88, 90 and 116. Rule IDs read off `g.fail(...)` call sites miss the 24
> rules `l0-conformance` emits through one table-driven call — which is how the keystone
> gate came to be missing from the catalogue entirely. See `Architecture_Freeze.md` §8.4.

### ☑ 7. Add a Windows CI job — **DONE 2026-08-10**

`windows-policy-gates` runs the whole suite — `run_gates.sh` **and** `self_test.sh` — on
`windows-latest` under Git Bash. Landed before the `ProcessSupervisor` code it protects.

It earned its place immediately: it fails on the cp1252 crash in `ci/gates/_lib.py` where
every gate died *after* passing its checks. Fixed in `b2e0b94`; the job is green.

### ☑ 8. Add a Turkish-locale CI job — **DONE 2026-08-10**

`turkish-locale` runs the whole suite under `LANG=LC_ALL=tr_TR.UTF-8`. Green.

Python's `str.lower()` is Unicode-based and locale-independent, so the gates were never at
risk; the **shell** is where `tr`, `grep -i` and `[[ = ]]` consult `LC_CTYPE`. That is what
this job covers today. The dotted/dotless `İ`/`ı` comparison in application code arrives
with the identifier comparisons at G6c — ADR-0023.

**If this job ever fails, the shell is wrong. Do not relax the locale.**

### ☑ 9. Confirm a GitHub Actions run exists — **DONE 2026-08-10**

[Run 31368654264](https://github.com/Denizfe/L.I.O.N.E.L/actions/runs/31368654264) —
**20 of 20 jobs green**, including `artifacts`, `l0-conformance`, `windows-policy-gates` and
`turkish-locale`.

The three pushes before the freeze commit are red in the same history. That is the 13/17
`Phase0_Final_Signoff.md` §2.2 recorded, independently confirmed.

---

## Ready — no action required

| | |
|---|---|
| ✅ 28 ADRs, no contradictions, all cross-references resolve |
| ✅ Contract set 1.1.0 — 27 schemas + 3 protobuf, all valid, 45 examples validate |
| ✅ Capability registry — 5 capabilities, all governance fields, consistent with ADR-0007 |
| ✅ Artifact lock — 13/13 resolved, tiers declared, digest matches registry |
| ✅ Trust model — vocabularies identical across contracts and registry |
| ✅ 17 gates, 127 rules, 20 workflow jobs, 0 stubs |
| ✅ Repository hygiene — 0 CRLF, 0 runtime `.py`, ignore rules exercised |
| ✅ Security assumptions documented — ADR-0011, 0012, 0015, 0022 |
| ✅ Ownership defined for every contract and capability |
| ✅ Architecture checksum reproducible from a clean clone on Windows and Linux |

---

## What remains

```
4            Piper licence resolution       ← G6c, resolvable now
```

**Item 4 is the only one left, and it does not block Phase 1.** It is registered to
`sensory` for G6c; the MODEL_CARD is readable today, so it can be closed early, but nothing
in Phase 1 depends on it.

Items 2 and 3 are landed but are deliberately **outside** `architecture-1.0.0`:
`Phase0_Final_Signoff.md` I1 records their absence as correct for Phase 0, and policy
declares `lockfile_required_at: G1`. Putting G1 deliverables inside the Phase 0 tag would
blur what the tag certifies.

### Carried into Phase 1, not on this checklist

| | |
|---|---|
| Self-test covers 9 of 17 gates | Every gate should have to reject something |
| ADR-0016 has no erratum provision, while practice has diverged three times | `Architecture_Freeze.md` §6 records the gap; closing it needs an ADR |

---

*Implementation prerequisites only. Phase 1 scope is defined in MASTER_PLAN_v2 §10.*
