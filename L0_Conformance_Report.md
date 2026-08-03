# L0 Conformance Gate — Implementation Report

**The hollow gate is replaced.** ADR-0007's keystone now enforces eight invariants instead
of printing two `echo` statements.

| | |
|---|---|
| Gate | `ci/gates/gate_l0_conformance.py` |
| Policy | `ci/policy/policy.yaml` → new `l0:` section (no existing section modified) |
| Invariants | **8**, all implemented |
| Checks executed | **44** |
| Negative tests | **10 / 10 detected** |
| Current result | **FAIL — 6 violations** |
| Blocks G0 | **Yes** — and it found something the stub concealed |

---

## 1. What was wrong

```yaml
- name: Assert no network egress during the L0 suite
  run: echo "STUB — needs the sensory harness (ADR-0027)…"
- name: Wake → STT → brain(ollama) → tools → TTS, EN and TR, no microphone
  run: echo "STUB — Phase 6…"
```

Both steps `echo`. Exit 0. **GitHub reported a green checkmark for asserting nothing.**

The original comment anticipated two states — *"failing later is fine — ABSENT is not"* —
and missed the third: **present, green, and hollow.** That is worse than absent. An absent
gate is visibly missing. A green stub is indistinguishable from a passing gate, and after a
few months nobody remembers it is empty.

Meanwhile `config/tiers/l0.toml` described `network_allowed: false` as *"asserted by the
conformance suite, not merely documented"* — and no suite asserted it.

---

## 2. The eight invariants

| # | Invariant | Rules | Verified by |
|---|---|---|---|
| **I1** | Offline-only operation | `L0-OFFLINE-001/002/003` | L0 tier declares `network_allowed=false`, `mtls_required=false`; every service placement is `inproc` — a URL is a socket, and a socket means not offline |
| **I2** | No outbound network dependencies | `L0-NETDEP-001/002/003/004` | Registry parses; every capability **declares** `requires_network`; any that declares `true` is disabled |
| **I3** | No hidden shell execution | `L0-SHELL-001` | Six patterns across the runtime surface: `shell=True`, `os.system`, `subprocess(…shell…)`, `commands.getoutput`, `eval $`, `curl \| sh` |
| **I4** | No forbidden providers | `L0-PROVIDER-001` | L0 never selects a `requires_network` provider |
| **I5** | No mutable Docker tags | `L0-LATEST-001` | `latest`/`main`/`master`/`dev`/`edge`/`stable` in L0-reachable config, unless digest-pinned |
| **I6** | Artifact lock compliance | `L0-ARTIFACT-001/002/003/004` | Every L0-path artifact RESOLVED; distinguishes *on the path* from *cannot be proven off it* |
| **I7** | Contract compatibility | `L0-CONTRACT-001/002/003` | Six required contracts present and parseable; no media payload key in any control-plane schema (ADR-0006) |
| **I8** | Architecture policy compliance | `L0-ARCH-001…006` | Policy default pinned `deny`; ToolCall requires `trust`; ToolResult requires `trust_of_output`; ProviderRequest requires `cancellation_token_id`; `memory.forget` required; no `.en` whisper model |

Plus **`L0-EGRESS-001`** — see below.

---

## 3. The gate enforces offline on itself

The stub's first step was *"Assert no network egress during the L0 suite."* An assertion in
a comment is not an assertion. The gate now **installs a network egress guard on itself**
before running any check:

```python
socket.socket.connect     → raises EgressAttempt, records the address
socket.create_connection  → raises EgressAttempt, records the address
```

Every attempt is recorded and reported as `L0-EGRESS-001`. So *"no outbound network
dependency"* is **enforced during the gate's own execution**, not merely claimed about
someone else's code. A check that quietly needed the network could not pass.

The workflow proves the guard is armed **before** trusting anything the gate reports:

```yaml
- name: Prove the network egress guard blocks outbound connections
  run: python3 ci/gates/gate_l0_conformance.py --prove-egress-guard
- name: L0 offline conformance
  run: python3 ci/gates/gate_l0_conformance.py
```

A guard nobody tests is another stub.

---

## 4. Negative test suite — 10 / 10 detected

Each mutation applied to an isolated copy of the tracked tree. The repository was never
modified.

| # | Violation injected | Expected | Result |
|---|---|---|---|
| **NT1** | `network_allowed = true` in L0 tier | `L0-OFFLINE-002` | ✅ **DETECTED** |
| **NT2** | L0 `memory` service becomes `http://127.0.0.1:8081` | `L0-OFFLINE-003` | ✅ **DETECTED** |
| **NT3** | L0 `provider = "anthropic"` | `L0-PROVIDER-001` | ✅ **DETECTED** |
| **NT4** | `requires_network: true` capability left enabled | `L0-NETDEP-003` | ✅ **DETECTED** |
| **NT5** | `subprocess.run(cmd, shell=True)` in the capability surface | `L0-SHELL-001` | ✅ **DETECTED** |
| **NT6** | `qdrant/qdrant:latest` in L0-reachable config | `L0-LATEST-001` | ✅ **DETECTED** |
| **NT7** | An L0-path artifact flipped to UNRESOLVED | `L0-ARTIFACT-00*` | ✅ **DETECTED** |
| **NT8** | `payload_b64` added to a control-plane contract | `L0-CONTRACT-003` | ✅ **DETECTED** |
| **NT9** | Policy default flipped from `deny` to `allow` | `L0-ARCH-001` | ✅ **DETECTED** |
| **NT10** | Outbound connection attempted during the run | `L0-EGRESS-001` | ✅ **DETECTED** |

**Control:** the unmodified tree fails on exactly the two real findings below — no false
positives from the mutations bleeding through.

> NT5 is worth noting: it is the only test that required *creating* runtime code. The
> capability surface is empty at Phase 0, so I3 would otherwise be vacuous. Planting a file
> proved the check is live rather than merely unreachable.

---

## 5. Current result — FAIL, and the failure is a real discovery

```
  FAIL  6 violation(s) across 44 checks
```

### Finding 1 — `L0-NETDEP-004` ×5 · no capability declares `requires_network`

```
✗ L0-NETDEP-004  capability `filesystem` does not declare `requires_network`
✗ L0-NETDEP-004  capability `github`     does not declare `requires_network`
✗ L0-NETDEP-004  capability `memory`     does not declare `requires_network`
✗ L0-NETDEP-004  capability `system`     does not declare `requires_network`
✗ L0-NETDEP-004  capability `media`      does not declare `requires_network`
```

**ADR-0007's exclusion of network-dependent capabilities at L0 exists only in prose.** It
appears in the ADR, in the lockfile notes, in the audit reports — and **nowhere
machine-readable.** The schema permits the field with a default of `false`, and not one of
the five capabilities declares it.

**Absence is not a declaration of `false`.** An undeclared field means the exclusion cannot
be enforced, only asserted. Every audit so far — including mine — repeated "the GitHub
capability is excluded at L0" as established fact. **Nothing in the repository established
it.**

The stub concealed this completely. This is the single most valuable thing the real gate
found, and it was found in its first execution.

### Finding 2 — `L0-ARTIFACT-004` · `images.github_mcp` unprovable

```
✗ L0-ARTIFACT-004  cannot prove `images.github_mcp` is off the L0 path,
                   and it is UNRESOLVED
```

This is deliberately **not** phrased as "L0-path artifact is unresolved." The gate
distinguishes two different defects:

| Rule | Means |
|---|---|
| `L0-ARTIFACT-003` | Known to be on the offline path, and unpinned — a real L0 violation |
| `L0-ARTIFACT-004` | Reachability **cannot be determined**, and it is unpinned |

An unpinned artifact of unknown reachability **must be treated as reachable**. Saying so
precisely is the difference between a finding someone acts on and one they argue with.

**Interaction with AUD-M01:** the artifacts gate reports the same artifact as a G0 blocker.
The L0 gate's complaint is different — not *"it is unresolved"* but *"nothing proves it is
off my path."* Declaring `requires_network: true` on the `github` capability would satisfy
the L0 gate while leaving AUD-M01 untouched, because the two gates are asking different
questions. That separation is intentional.

---

## 6. Vacuity — reported, not hidden

Audit finding `AUD-M04` observed that a gate reporting "19 checks passed" when most examined
nothing overstates its coverage. This gate refuses to do that:

```
note  shell scan: 7 runtime-surface files examined
note  image-tag scan: 3 L0-reachable config files
note  network egress guard: active for the whole run, 0 attempts
note  13 substantive check group(s) · 0 vacuous
```

Every result is labelled **SUBSTANTIVE** or **VACUOUS**, and both counts are printed.
Today all 13 groups are substantive — the runtime surface has 7 config files to scan even
without Python. Had it been empty, the gate would have said so rather than counting the
check as a pass.

---

## 7. Changes made

| File | Change |
|---|---|
| `ci/gates/gate_l0_conformance.py` | **New.** 8 invariants, 18 rules, egress guard, `--root`, `--prove-egress-guard` |
| `ci/policy/policy.yaml` | **New `l0:` section only.** No existing section touched |
| `.github/workflows/ci.yml` | `l0-conformance` job: `echo` stubs → guard proof + real gate; renamed from "STUB until Phase 6" to "BLOCKING — ADR-0007" |
| `ci/run_gates.sh` | `l0-conformance` added to `ORDER` |
| `L0_Conformance_Report.md` | This document |

**No unrelated policy was modified.** `artifacts`, `secrets`, `architecture`, `no-todo` and
every other gate's rules are unchanged; ADR files untouched; the capabilities registry and
lockfile deliberately **left as they are** so the gate's findings stand on their own rather
than being silently made green by the person who wrote the gate.

---

## 8. Remediation for the current failures

**Not applied.** Fixing the thing a gate checks, in the same change that writes the gate, is
how a gate becomes decoration.

### For `L0-NETDEP-004` — declare network status on all five capabilities

In `config/capabilities.registry.json`:

```jsonc
"filesystem": { …, "requires_network": false },
"github":     { …, "requires_network": true  },   // ADR-0007 excludes it at L0
"memory":     { …, "requires_network": false },   // inproc; Qdrant is local
"system":     { …, "requires_network": false },
"media":      { …, "requires_network": false }
```

This converts ADR-0007's exclusion from prose into an enforceable fact. Recommend also
making `requires_network` **required** in `capabilities-registry.schema.json` so a future
capability cannot omit it — but that is a schema change and belongs in its own review.

### For `L0-ARTIFACT-004` — follows automatically

Once `github` declares `requires_network: true`, the artifact is provably off the L0 path
and this finding clears. **AUD-M01 remains open** — the artifacts gate asks a different
question and still wants the digest.

---

## 9. Honest limits

- **This is static conformance.** It verifies configuration, contracts and the absence of
  forbidden constructs. It cannot verify that a running L0 system stays offline — that needs
  the sensory harness and the full voice loop at G6, which do not exist.
- **I3 has almost nothing to scan.** 7 config files, no Python. NT5 proves the check is
  live, but it will not be load-bearing until Phase 1 writes code.
- **The egress guard covers `socket`.** A subprocess making its own connections would not be
  caught. Adequate today — the gate spawns nothing — and worth revisiting when it does.
- **No runtime latency, memory or model behaviour is checked.** Those are G6 concerns.

The gate is honest about being a *static* L0 conformance gate. It is no longer honest-shaped
and empty.

---

*Re-ran the L0 gate only, as instructed. `bash ci/run_gates.sh l0-conformance` → **exit 1**,
6 violations across 44 checks.*
