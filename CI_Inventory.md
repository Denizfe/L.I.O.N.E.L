# CI Inventory

**L.I.O.N.E.L policy pipeline** — Phase 0 / M3. Generated 2026-08-02.

| | |
|---|---|
| Gates | **16** |
| Workflow jobs | **18** (16 gates + self-test + L0 stub) |
| Current state | **15 pass · 1 fail by design · 0 broken** |
| Runner | `bash ci/run_gates.sh [gate]` |
| Self-test | `bash ci/self_test.sh` — 8/8 planted violations caught |
| Runtime code | **0 files** — Phase 0 discipline machine-checked |

---

## 1. The gates

Every gate is a standalone script. None depends on another, so a failure never cascades
and never hides the other fifteen results.

| # | Gate | Enforces | Rules | Status |
|---|---|---|---|---|
| 1 | [`structure`](ci/gates/gate_structure.py) | Repository layout, Phase 0 code ban | STRUCT-001…004 | PASS |
| 2 | [`adr`](ci/gates/gate_adr.py) | ADR-0016 | ADR-001…008 | PASS |
| 3 | [`contracts`](ci/gates/gate_contracts.py) | ADR-0003, ADR-0009 | CONTRACT-001…010 | PASS |
| 4 | [`jsonschema`](ci/gates/gate_jsonschema.py) | ADR-0027 | JSON-001…006 | PASS |
| 5 | [`protobuf`](ci/gates/gate_protobuf.py) | ADR-0028, ADR-0006 | PROTO-001…004 | PASS |
| 6 | [`artifacts`](ci/gates/gate_artifacts.py) | ADR-0013 | ART-000…016 | **FAIL — by design** |
| 7 | [`docker-digests`](ci/gates/gate_docker_digests.py) | ADR-0013, ADR-0020 | DOCKER-001…006 | PASS |
| 8 | [`no-latest`](ci/gates/gate_no_latest.py) | ADR-0013 | DOCKER-002 | PASS |
| 9 | [`no-pending`](ci/gates/gate_no_pending.py) | ADR-0013 | PLACEHOLDER-001 | PASS |
| 10 | [`no-todo`](ci/gates/gate_no_todo.py) | MASTER_PLAN_v2 §12 | TODO-001, TODO-002 | PASS |
| 11 | [`secrets`](ci/gates/gate_secrets.py) | ADR-0015, ADR-0022 | SEC-* | PASS |
| 12 | [`licenses`](ci/gates/gate_licenses.py) | ADR-0013 | LIC-001…005 | PASS |
| 13 | [`markdown`](ci/gates/gate_markdown.py) | — | MD-LINK, MD-HEADING, MD-WS | PASS |
| 14 | [`dependencies`](ci/gates/gate_dependencies.py) | ADR-0013 | DEP-001, DEP-002 | PASS |
| 15 | [`shell`](ci/gates/gate_shell.py) | ADR-0011, ADR-0014 | SH-* | PASS |
| 16 | [`architecture`](ci/gates/gate_architecture.py) | **11 ADRs** | ARCH-001…016 | PASS |

### The one that is red on purpose

`artifacts` fails because one image digest is unresolved. **That is the gate working.**
ADR-0013 blocks G0 while any artifact is unpinned, and a gate that went green anyway
would be decoration. See [Artifact_Verification_Report.md](Artifact_Verification_Report.md) §5
for the blocker and four reproducible alternatives.

---

## 2. ADR coverage

Which decisions have an executable test, and which do not.

| ADR | Decision | Enforced by |
|---|---|---|
| 0003 | MCP-first capability model | `contracts` |
| 0006 | Control/data plane separation | `architecture` ARCH-003, `protobuf` |
| 0007 | Degradation ladder, L0 guarantee | `architecture` ARCH-011…013 |
| 0008 | Coordinator decomposition | `architecture` ARCH-015 |
| 0009 | Extended BrainProvider contract | `architecture` ARCH-002, `contracts` |
| 0010 | Memory Service | `architecture` ARCH-010 |
| 0011 | Shell execution abolished | `architecture` ARCH-001, `shell`, `structure` |
| 0012 | Policy Engine, default-deny | `architecture` ARCH-004, 006, 007, 009 |
| 0013 | Artifact pinning | `artifacts`, `docker-digests`, `no-latest`, `no-pending`, `licenses`, `dependencies` |
| 0014 | ProcessSupervisor | `shell` |
| 0015 | SecretResolver, no interpolation | `secrets` |
| 0016 | ADRs replace `<thought>` | `adr`, `architecture` ARCH-016 |
| 0018 | Multilingual STT mandatory | `architecture` ARCH-014, `artifacts` ART-016 |
| 0020 | Kubernetes, cloud-portable | `docker-digests` |
| 0022 | Zero trust between runtimes | `secrets` |
| 0025 | Cancellation & backpressure | `architecture` ARCH-008 |
| 0026 | Side-effect classification | `architecture` ARCH-005 |
| 0027 | Testing strategy | `jsonschema` |
| 0028 | Data-plane transport | `protobuf` |

**Not yet enforced, and honest about it:**

| ADR | Why not | Enforced at |
|---|---|---|
| 0001 | Provider swap needs a running system | G3 replay tests |
| 0005 | Dual runtime needs deployable services | G7 |
| 0017 | Dual TTS needs the audio pipeline | G6c |
| 0019 | Telemetry needs emitting code | G5 |
| 0021 | Eval harness needs a model to evaluate | G8 |
| 0023 | Turkish locale needs comparison code | G6c (a CI job under `tr_TR.UTF-8` is already specified) |
| 0024 | Robotics — provisional, uncommitted | G10 |

19 of 28 ADRs have an executable test today. The remaining 9 need running code, and
each names the gate that will cover it — a decision with no test is a preference, and
this table is where that would otherwise hide.

---

## 3. Workflow jobs

`.github/workflows/ci.yml` — 18 jobs.

| Job | Type | Notes |
|---|---|---|
| 16 policy gates | one per gate | **No `needs:` between them.** Independent by design |
| `gate-self-test` | meta | Plants 8 known violations, asserts each is caught |
| `l0-conformance` | standing stub | `needs: [structure, contracts, architecture]`. ADR-0007 |

### Why no `needs:` between gates

A dependency chain means one early failure marks fifteen jobs "skipped" and you learn
one thing per push. Independent jobs give the whole picture in a single run. The cost is
some duplicated setup; the benefit is that fixing CI takes one afternoon instead of five.

### The self-test job

A gate that passes a clean repository but would miss a real violation is decoration.
`ci/self_test.sh` plants a known violation for eight gates and asserts each is rejected,
then **verifies its own cleanup** — a self-test that leaves litter turns every later run
red for the wrong reason, and the first person to see it will fix the gate rather than
the litter.

| Planted | Gate | Rule |
|---|---|---|
| AWS access key | `secrets` | SEC-AWS |
| `qdrant/qdrant:latest` | `no-latest` | DOCKER-002 |
| `sha256: PENDING` | `no-pending` | PLACEHOLDER-001 |
| `capabilities/shell/` | `architecture` | ARCH-001 |
| `.py` under `src/lionel/` | `structure` | STRUCT-004 |
| Unregistered TODO | `no-todo` | TODO-001 |
| Script without strict mode | `shell` | SH-STRICT |
| Broken internal link | `markdown` | MD-LINK |

**8/8 caught.**

---

## 4. Running gates

```bash
bash ci/run_gates.sh                 # all 16, with a summary
bash ci/run_gates.sh architecture    # one
bash ci/run_gates.sh --list          # names and paths
python3 ci/gates/gate_adr.py         # fully standalone, no runner needed
bash ci/self_test.sh                 # do the gates catch anything?
```

Requirements: Python 3.11, `pyyaml`; plus `jsonschema` for the schema gate and
`grpcio-tools` for protobuf. No gate needs Docker, network, or the project's own
dependencies — CI validates the repository, it does not build or run it.

---

## 5. Files

```
ci/
├── run_gates.sh                 runner: one gate or all
├── self_test.sh                 plants violations, asserts they are caught
├── policy/
│   └── policy.yaml              ALL thresholds, allowlists, registries
└── gates/
    ├── _lib.py                  Finding model, exit-code contract, reporting
    └── gate_*.py                16 gates

.github/workflows/ci.yml         18 jobs
scripts/verify_artifacts.sh      thin wrapper → gate_artifacts.py
```

`scripts/verify_artifacts.sh` used to carry its own copy of the artifact rules. It now
delegates. Duplicated policy across two files is how the two quietly disagree, and the
disagreement is discovered during an incident.

---

## 6. Registered exemptions

Every exemption carries an owner and the gate that removes it. An exemption with no
route to removal is not an exemption, it is a silently lowered standard.

| Kind | Item | Owner | Removed at |
|---|---|---|---|
| TODO | `l0-conformance` stubs in `ci.yml` | platform | G6 |
| Licence | `models.piper_tr_dfki` + config | sensory | G6c |
| Licence | `models.wake_bootstrap` (NC ambiguity) | sensory | G6a — self-liquidating |
| Markdown | `MASTER_PLAN_v1.md` | architecture | never — frozen record |
| ADR shape | `ADR-0004` | architecture | never — superseded record |
| Shell strict | `run_gates.sh`, `verify_artifacts.sh` | platform | never — must survive non-zero exits |

Shell exemptions use an inline pragma with a **mandatory reason**:

```bash
# ci-policy: allow SH-STRICT — this runner MUST survive non-zero gate exits …
```

---

*Regenerate rather than hand-edit. A stale inventory is worse than none, because it is trusted.*
