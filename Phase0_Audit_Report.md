# Phase 0 Gate G0 — Independent Audit Report

| | |
|---|---|
| Auditor role | External Principal AI Architect · Security Reviewer · Release Gatekeeper |
| Independence | Assumed no authorship of any file under audit |
| Date | 2026-08-02 |
| Scope | MASTER_PLAN v1/v2 · 28 ADRs · 30 contracts · artifact lockfile · 16 CI gates · policy registries · repository structure |
| Method | Read-only inspection + independent gate execution + adversarial probing on an isolated copy (`/tmp/audit/repo`). **No repository file was modified.** |
| Gates executed | **16 / 16** independently |
| Adversarial probes | **19** |

## VERDICT: **FAIL**

Two **Critical** findings break hard G0 requirements. Neither is a matter of taste or
polish; both mean that claims central to this gate have not been demonstrated in the
environment where they must hold.

This is a rejection of the *gate*, not of the work. The architecture underneath is
unusually strong and most of it is ready. Section 8 explains why FAIL is nonetheless the
correct call, and `Phase0_Blockers.md` gives the bounded path to re-audit.

---

## 1. Executive summary

### What is genuinely good

This repository is above the standard I normally encounter at an equivalent gate. Twelve
observations, stated so they are not lost in what follows:

1. **The Degradation Ladder (ADR-0007) is a first-class idea**, and treating L0 offline
   conformance as a permanent blocking gate is the correct mechanism for a stated goal
   that would otherwise erode silently.
2. **Verification tiers A–E in the artifact lockfile** are the best supply-chain framing
   I have reviewed on a project this size. "A hash is not a hash" is exactly right, and
   almost nobody does it.
3. **The rejected-substitute record** for Kokoro — noting a mirror 155 bytes smaller and
   refusing to use its digest — is evidence of real discipline. That trade is normally
   made silently and never discovered.
4. **Abolishing shell execution outright** (ADR-0011) rather than allowlisting it is the
   correct security call and is rarely made.
5. **Trust propagation is monotonic and structurally enforced** in the contracts —
   `ToolResult.trust_of_output` and `MemoryQueryResult.trust_floor` are both required, so
   there is no path that launders untrusted content upward.
6. **Control/data plane separation** (ADR-0006) is correctly reasoned and the `media/`
   namespace exists specifically so the invariant stays checkable rather than being
   weakened when it became inconvenient.
7. **ADR-0004 retained with its rationale** instead of deleted demonstrates the ADR
   discipline actually working.
8. **Contract consumer counts** make change cost visible before a change, which is the
   single most useful thing a contract register can do.
9. **The gate self-test** (`ci/self_test.sh`) is a genuine attempt to prove the pipeline
   bites, and it found real bugs during authoring.
10. **Three exit codes** (pass / violation / gate-broken) is correct and uncommon.
11. **Exemption registries requiring an owner and a removal gate**, with rules TODO-002
    and LIC-005 policing the escape hatches themselves, is sound governance design.
12. **Zero runtime code under `src/lionel/`**, machine-enforced. Phase 0 discipline held.

### Why it still fails

| Finding | Why it is fatal to *this gate* |
|---|---|
| **AUD-C01** — repository is not under version control | `.git` does not exist. **CI has never executed.** G0's DoD requires "CI skeleton wired… CI runs and reports". `.gitattributes` and `.gitignore` are inert files with no effect. Every claim of gate correctness rests on local runs by the author, unreproducible by a third party. |
| **AUD-C02** — `ci/` is wholly excluded from secret scanning | Proven by probe: AWS keys, GitHub tokens and PEM private keys placed anywhere under `ci/` are not detected. `ci/` is a normal home for helper scripts and a natural place to stash a token. |

Plus **7 Major** findings, one of which (AUD-M01) is the project's own declared G0
criterion being unmet.

### Finding counts

| Severity | Count | Blocks G0 |
|---|---|---|
| **Critical** | 2 | Yes |
| **Major** | 7 | 1 does (AUD-M01) |
| **Minor** | 6 | No |
| **Informational** | 6 | No |
| **Total** | **21** | |

---

## 2. Independent gate execution

All 16 gates executed from a clean copy. Results reproduced exactly as documented — the
project's own reporting is accurate.

| Gate | Exit | Checks | Verdict on the gate itself |
|---|---|---|---|
| `structure` | 0 | 24 | Sound |
| `adr` | 0 | 195 | Sound, thorough |
| `contracts` | 0 | 34 | Sound, one gap (AUD-N03) |
| `jsonschema` | 0 | 155 | Sound |
| `protobuf` | 0 | 25 | Sound |
| `artifacts` | **1** | 1 | Correct — red by design (AUD-M01) |
| `docker-digests` | 0 | 11 | **Gap** — skips `UNRESOLVED` refs (AUD-M03) |
| `no-latest` | 0 | 1 | **Counter is not coverage** (AUD-M02) |
| `no-pending` | 0 | 1 | Same |
| `no-todo` | 0 | 1 | Same |
| `secrets` | 0 | 7 | **Bypassable** (AUD-C02) |
| `licenses` | 0 | 13 | Sound |
| `markdown` | 0 | 40 | Sound |
| `dependencies` | 0 | 1 | Inert until Phase 1 — correctly declared |
| `shell` | 0 | 4 | Sound |
| `architecture` | 0 | 19 | **Syntactic only** (AUD-M04) |

**I did not accept any gate merely because it exists.** Section 3 records what happened
when each was attacked.

---

## 3. Adversarial probe results

19 probes on an isolated copy. Zero residue; the repository was never touched.

| # | Probe | Result |
|---|---|---|
| 1 | Gates run against a tree containing only themselves | **All report `PASS 1 checks`** → counter is not coverage |
| 3a | AWS key in `ci/policy/` | **BYPASS** |
| 3b | AWS key in `ci/gates/` | **BYPASS** |
| 3c | PEM private key in `ci/` | **BYPASS** |
| 3d | AWS key in `config/` (control) | Caught |
| 4a | `:latest` in `deploy/README.md` | **BYPASS** |
| 4b | `:latest` in `deploy/…/overlay.yaml` (control) | Caught |
| 4c | `sha256: PENDING` in a `.md` runbook | **BYPASS** |
| 5a | Media payload under an unlisted key (`raw_audio_bytes`) in a control-plane schema | **BYPASS** |
| 5b | Provider branch via dict lookup instead of `==` | **BYPASS** |
| 5c | Provider branch via `==` (control) | Caught |
| 11 | Fabricated but well-formed 64-hex hash | **Undetectable** until first download (Phase 6) |
| 15 | Version-control state | **No `.git` directory** |

---

## 4. Findings

### CRITICAL

---

#### AUD-C01 — Repository is not under version control; CI has never executed

**Evidence**
```
$ ls -a /…/L.I.O.N.E.L/.git
  (does not exist)
```
`git rev-list --count HEAD` → not a repository.

**Affected** `.git` (absent) · `.gitattributes` · `.gitignore` · `.github/workflows/ci.yml` · all 16 gates · `CI_Inventory.md` · `CI_Architecture.md`

**Impact**

- **G0's Definition of Done is explicitly unmet.** MASTER_PLAN_v2 Phase 0 DoD: *"CI
  skeleton with the L0 gate wired (failing is fine; **present is mandatory**)"* and *"CI
  runs and reports"*. The workflow file exists; the pipeline has never run.
- **`.gitattributes` has never been applied.** `*.sh text eol=lf` normalisation takes effect
  on first `git add`, so the file is correct but unexercised. ADR-0014 and the Git Bash
  hazard table identify CRLF-in-`.sh` as the project's most likely Windows failure. The
  current tree is clean — I verified 0 CRLF files — but that is the author's editor
  behaving, not the control working. **Precision matters here: the control is untested,
  not defective.**
- **`.gitignore` has never been exercised.** It will function correctly on first `git add`;
  it has simply never run. The residual risk is that `models/`, `data/`, `logs/` and
  `__pycache__/` exclusions are unverified against a real staging operation — and
  `models/` will eventually hold ~2 GB of weights.
- **ADR-0016 immutability is unenforceable.** "ADRs are immutable once Accepted" has no
  mechanism without history.
- **The `secrets` job sets `fetch-depth: 0`** to scan history. There is no history.
- **Third-party reproducibility is zero.** Every claim — "15/16 gates pass", "8/8 planted
  violations caught" — rests on the author executing scripts locally. A gatekeeper cannot
  independently confirm the pipeline works in the environment where it must work.

**Blocks G0** — **Yes.** Directly and explicitly.

**Remediation** `git init -b main`; verify LF normalisation applied; stage and present the
tree for approval per the project's commit rule; push and let the workflow execute; attach
the run URL. **`git init` is not a commit** and does not conflict with the no-autonomous-commit
rule.

**Verification** `.git` exists · `git ls-files | wc -l` > 0 · a GitHub Actions run exists
showing 18 jobs with 15 green, `artifacts` red, `gate-self-test` green.

---

#### AUD-C02 — Secret scanning is fully bypassed under `ci/`

**Evidence** (probe 3, on the isolated copy)
```
ci/policy/_probe.yaml   aws: "AKIA<16-char-example>"   → gate_secrets exit 0   BYPASS
ci/gates/_probe.py      K="AKIA<16-char-example>"      → gate_secrets exit 0   BYPASS
ci/_probe.txt           -----BEGIN RSA PRIVATE KEY--- → gate_secrets exit 0   BYPASS
config/_probe.yaml      aws: "AKIA<16-char-example>"   → gate_secrets exit 1   caught
```

**Affected** `ci/gates/gate_secrets.py:22-24` · `Policy_Gates.md` (§Scope exclusions) · `CI_Architecture.md` §3

**Impact**

The stated rationale — *"gates and their self-test necessarily contain the strings they
hunt"* — is legitimate **for pattern-token gates** (`no-latest`, `no-pending`, `no-todo`).
It is **not** legitimate for secret scanning, and the two were generalised together.

A gate's source needs to contain the *regex* `AKIA[0-9A-Z]{16}`. It never needs to contain
a *matching literal*. Excluding the whole directory to avoid a self-match is a
disproportionate remedy that opens a real hole: `ci/` is an ordinary place for helper
scripts, and a token pasted into a CI helper is a common real-world incident.

Severity is raised to Critical because ADR-0015's entire secret posture — `secret://` URIs,
`SecretStr` redaction — is defence-in-depth *behind* the assumption that a literal in the
tree is caught. Here it is not, in a directory nobody would think of as exempt.

**Blocks G0** — **Yes.** A security control with a proven bypass in a normal code location
is not a control.

**Remediation** Remove the blanket `ci/` exclusion from `gate_secrets.py`. Replace with a
narrow, per-line mechanism: exclude only lines carrying an explicit
`# ci-policy: test-fixture` marker, or move planted fixtures out of the scanned tree
entirely (e.g. generate them into `$TMPDIR` at self-test runtime). Keep the `ci/` exclusion
for the token-pattern gates, where the rationale does hold.

**Verification** Re-run probe 3: all four cases caught, `config/` control still caught, and
`bash ci/self_test.sh` still 8/8.

---

### MAJOR

---

#### AUD-M01 — Artifacts gate red; unresolved GHCR digest

*(Directly answers audit question 1.)*

**Evidence** `gate_artifacts.py` exits 1 · `ART-000` · `artifacts.lock.yaml` `meta.unresolved: 1` ·
`images.github_mcp.status: UNRESOLVED`, tier E.

**Classification on technical merit: MAJOR BUT DEFERRABLE.**

Reasoning:

- The artifact is `requires_network: true`, so ADR-0007 **already excludes it at tier L0**.
  It is not on the offline critical path, and L0 conformance does not depend on it.
- The blocker is correctly classified **TEMPORARY** with an accurate technical explanation
  (GHCR requires an `Authorization: Bearer` header).
- **Four alternatives, all marked reproducible**, including an exact command.
- No Phase 0 deliverable consumes it. It is first needed at **G1**.
- Nothing about the artifact or the registry is defective; the constraint was the tooling
  in the authoring environment.

**However — it blocks G0 anyway, because the project said so.** ADR-0013 Verification:
*"fails closed … on any `UNRESOLVED` entry"*, and `artifacts.lock.yaml` header: *"G0 cannot
be signed off until this file contains zero of them."*

A gatekeeper who waives a project's own self-declared hard criterion because the finding
looks small teaches the project that its criteria are negotiable. That is precisely the
erosion ADR-0007 exists to prevent, applied to a different rule.

**Two legitimate exits, and only two:**

1. Resolve it — one command, per `Artifact_Verification_Report.md` §5 alternative 1.
2. **Amend ADR-0013** to distinguish *G0-blocking* artifacts (on the L0 path) from
   *G1-blocking* ones, and re-audit against the amended criterion.

Option 2 is intellectually defensible and arguably better design. What is not acceptable is
signing off against the current criterion while it is unmet.

**Blocks G0** — **Yes**, as currently written.

**Verification** `gate_artifacts.py` exits 0, or ADR-0013 carries an approved amendment and
the gate implements the narrowed rule.

---

#### AUD-M02 — Check counters are violation counts, not coverage; a documented safety claim is false

**Evidence** Probe 1 — `no-latest`, `no-pending`, `no-todo`, `secrets` each report
`PASS 1 checks` against a tree containing nothing but the gates themselves.
`gate_no_latest.py:25` calls `g.check()` only inside the violation branch; line 33 adds an
unconditional `g.check(1)`.

`CI_Architecture.md` §4 states:
> "`checks_run` is reported alongside violations, so a gate that silently examined nothing
> is visible. `PASS 0 checks` is a bug, not a success"

**This is false as implemented.** The trailing `g.check(1)` guarantees a floor of 1, and
the counter never reflects scan breadth.

**Affected** `ci/gates/_lib.py` · `gate_no_latest.py` · `gate_no_pending.py` ·
`gate_no_todo.py` · `gate_secrets.py` · `gate_dependencies.py` · `CI_Architecture.md` §4

**Impact** Silent coverage loss. If a glob stops matching — a directory rename, an
`include=` suffix filter that drops a new file type, an exclusion widened during a hurried
fix — the gate goes green forever and nothing indicates it stopped looking. The
documentation asserts a safety net that does not exist, which is worse than not claiming
one, because reviewers will rely on it.

**Blocks G0** — No. But it undermines confidence in every green result.

**Remediation** Increment `checks_run` per **file or item examined**, not per violation.
Optionally add a policy floor (e.g. `secrets` must scan ≥ 50 files) so a collapse in
coverage fails rather than passes. Correct the claim in `CI_Architecture.md` §4.

**Verification** Probe 1 repeated: gates against an empty tree report `PASS 0 checks`, or
fail a declared minimum-coverage floor.

---

#### AUD-M03 — Runnable config contains a syntactically invalid image reference, and the gate deliberately skips it

**Evidence** `config/capabilities.registry.json:23`
```
"ghcr.io/github/github-mcp-server@sha256:UNRESOLVED-see-artifacts.lock.yaml"
```
`gate_docker_digests.py` skips any line containing `UNRESOLVED`.

**Affected** `config/capabilities.registry.json` · `ci/gates/gate_docker_digests.py` · `contracts/mcp/v1/capabilities-registry.schema.json`

**Impact** The registry is the file the host reads to spawn capabilities. This entry is not
a valid OCI reference and `docker run` would reject it. The intent — an honest marker
rather than a fabricated digest — is right, and the alternative (a fake digest) would be
worse. But the *result* is a config file that cannot be loaded, and the gate has been
taught to look away from exactly the field it exists to police.

The registry schema (`capabilities-registry.schema.json`) does not constrain the `args`
array, so schema validation does not catch it either. Two independent controls both miss it.

**Blocks G0** — No, because nothing executes in Phase 0. It **will** block G1.

**Remediation** Prefer `"enabled": false` on the capability with the digest field absent,
so the config remains loadable and the capability is explicitly off. Then remove the
`UNRESOLVED` skip from the docker gate.

**Verification** `config/capabilities.registry.json` parses and every image reference either
matches `^sha256:[0-9a-f]{64}$` or belongs to a capability marked `enabled: false`.

---

#### AUD-M04 — Architecture conformance is syntactic; two proven semantic bypasses

*(Directly answers audit question 5.)*

**Evidence** Probe 5.

| Bypass | Rule evaded | Mechanism |
|---|---|---|
| `raw_audio_bytes` (base64) in a control-plane schema | ARCH-003 | Rule matches a **fixed key list**: `payload_b64`, `payload`, `pcm`, `audio_bytes` |
| `H = {"anthropic": …}[cfg.provider]` | ARCH-002 | Rule matches only `==`, `!=`, `is` comparisons |

**Affected** `ci/gates/gate_architecture.py` · `ci/policy/policy.yaml` (`architecture.media_payload_keys`, `provider_branch_allowed_dirs`)

**Impact** ARCH-003 and ARCH-002 defend two of the most important invariants in the system
— no media on the control plane (ADR-0006), no provider-identity branching (ADR-0009) — and
both are evaded by ordinary alternative spellings, not by cleverness.

A second, larger point: **most architecture checks are currently vacuous.** ARCH-002 scans
`.py` files and there are none; ARCH-001 and ARCH-015 assert directories are absent. Of 19
reported checks, roughly 8 examine real content today. `19 checks PASS` reads as far
stronger coverage than exists.

**Blocks G0** — No. This is honest for Phase 0, where the code these rules govern does not
exist. It becomes serious the moment Phase 1 writes Python.

**Remediation** For ARCH-003, invert the rule: flag any property with
`contentEncoding: base64` or a `bytes`-like type in a control-plane schema, rather than
matching a name list. For ARCH-002, add AST-based detection at Phase 1 (provider names
appearing as dict keys, string constants, or `getattr` targets outside the allowed dirs).
Report vacuous checks distinctly from substantive ones.

**Verification** Probe 5a and 5b both caught.

---

#### AUD-M05 — No Windows CI coverage on a Windows-first project

**Evidence** `.github/workflows/ci.yml` — all 18 jobs `runs-on: ubuntu-latest`. No Windows
runner. No `tr_TR.UTF-8` locale job, despite ADR-0023 requiring one and `CI_Architecture.md`
§6 implying it is "already specified".

**Affected** `.github/workflows/ci.yml` · ADR-0014 · ADR-0023 · `CI_Architecture.md` §6

**Impact** The host runtime is Windows + Git Bash (ADR-0002, ADR-0014). The project has
correctly identified Windows-specific hazards — Job Objects for kill-tree, CRLF in `.sh`,
`MSYS_NO_PATHCONV`, `ProactorEventLoop`, `MAX_PATH` — and **none of them is exercised by
CI**. ADR-0023's dotted/dotless `İ/ı` bug is explicitly described as "invisible in English
testing and guaranteed in Turkish production", and the job that would make it visible does
not exist.

**Blocks G0** — No. There is no code to test yet. It must not survive G1.

**Remediation** Add a `windows-latest` job (initially: LF verification, path-length,
policy gates under Git Bash) and a `tr_TR.UTF-8` locale job. Correct the claim in
`CI_Architecture.md` §6.

**Verification** CI shows a passing Windows job and a passing Turkish-locale job.

---

#### AUD-M06 — Self-test covers 8 of 16 gates

**Evidence** `ci/self_test.sh` — `expect_violation` for: `secrets`, `no-latest`,
`no-pending`, `architecture`, `structure`, `no-todo`, `shell`, `markdown`.
**Untested:** `adr`, `contracts`, `jsonschema`, `protobuf`, `artifacts`, `docker-digests`,
`licenses`, `dependencies`.

**Impact** `CI_Architecture.md` §7 states the principle correctly — *"a gate that has never
rejected anything is unproven"* — and then leaves half the gates unproven. `artifacts` and
`contracts` are among the highest-value gates and neither has ever been shown to reject
anything. Probe 5 found two real bypasses in `architecture`, which *is* self-tested; the
untested half has had no equivalent scrutiny.

**Blocks G0** — No.

**Remediation** Extend `self_test.sh` to all 16. Adopt the project's own rule from
`CI_Architecture.md` §7 step 6 as mandatory.

**Verification** `bash ci/self_test.sh` reports 16/16.

---

#### AUD-M07 — Blocker records are not required to carry an owner or a deadline

*(Directly answers audit question 10.)*

**Evidence** `ci/policy/policy.yaml` `artifacts:` requires only
`require_blocker_classification` and `require_reproducible_alternative`.
`gate_artifacts.py` checks `what`, `classification`, and alternatives. Neither requires
`owner` or a date. `images.github_mcp` has **no owner field and no deadline**.

**Impact** The audit criterion for reproducibility is that every artifact is *either*
immutably pinned *or* "explicitly blocked with an **owner**, resolution command,
**deadline**, and gate". The lockfile satisfies command and gate; it does not satisfy owner
or deadline, and the gate does not require them.

This is inconsistent with the project's own standard elsewhere: `todo.registry` and
`licenses.unresolved_registry` both mandate an owner and a removal gate. The artifact
blocker — the most consequential deferral in the repository — is held to a weaker standard
than a TODO comment.

**Blocks G0** — No, but it is the difference between a deferral and a drift.

**Remediation** Add `owner` and `resolve_by` (a gate) as required fields on any UNRESOLVED
artifact; enforce in `gate_artifacts.py` alongside ART-009/010/011.

**Verification** A blocker lacking `owner` or `resolve_by` fails the gate.

---

### MINOR

| ID | Title | Evidence | Impact | Remediation |
|---|---|---|---|---|
| **AUD-N01** | TODO registry entry is over-broad | `policy.yaml` `todo.registry[1]`: pattern `TODO`, glob `.github/workflows/ci.yml` | Permits *any* TODO anywhere in the workflow. `unblocked_by` names a gate but there is no date, so "G6" could be a year away with nothing signalling drift | Narrow the pattern; add an ISO date alongside the gate |
| **AUD-N02** | Provisional contracts have no enforced promotion | `WorkflowEvent` (G2), `VisionFrame` (G10) declare promotion gates in prose only; no gate reads them | A provisional contract can quietly become permanent — the exact failure the exemption registries were designed to prevent, applied to contracts | Add `promote_at` to `x-lionel`; gate fails if the named gate has passed and stability is still `provisional` |
| **AUD-N03** | CONTRACT-007 satisfied by a placeholder | `vision-frame.schema.json` consumers = `["(none yet — vision_service, …)"]` — a non-empty list of one placeholder string | Syntactic conformance passes where the semantic intent (a real consumer exists) fails | Reject consumer entries matching `^\(none` |
| **AUD-N04** | `.md` exclusion permits `:latest` and `PENDING` in docs | Probes 4a, 4c | Low. Docs are copy-paste sources for runbooks; a `:latest` in a deploy README propagates | Scope the exclusion to prose blocks, or exempt only files under `docs/` and the two plan files |
| **AUD-N05** | Fabricated well-formed hash is undetectable | Probe 11 — gates validate format only; nothing re-derives from upstream | The "never invent a hash" rule is enforced by discipline, not machinery. Detection deferred to first download in Phase 6 | Optional: an online CI job re-deriving tier-A hashes from published APIs |
| **AUD-N06** | Rule-count drift | `Policy_Gates.md` header says 88; 89 extractable from gates; table has 90 rows | Cosmetic; a generated doc has drifted from its source | Regenerate |

---

### INFORMATIONAL — direct answers to the audit questions

#### AUD-I01 — Tier D `hey_jarvis` is **ACCEPTABLE for Phase 0** *(question 2)*

Single uncorroborated mirror (`harvestsu/openwakeword-onnx`), no upstream size to check,
no second source. Genuinely the weakest pin in the lockfile — and correctly labelled as
such rather than dressed up.

Acceptable because: the mirror is pinned as the source of record, so the build **is**
reproducible; the blocker is upstream's (openWakeWord v0.6.0 deleted its release assets, so
no digest exists to find); and it is **self-liquidating** — ADR-0023 replaces it with a
project-trained model at Phase 6a, taking both the tier-D weakness and the licence
ambiguity with it. `max_tier_d: 1` in policy prevents this becoming a pattern.

**Condition:** if it survives past G6a, it must be re-audited. Recommend adding it to a
registry with `resolve_by: G6a` per AUD-M07.

#### AUD-I02 — Non-commercial licence risk is **ACCEPTABLE for personal development; BLOCKING for distribution** *(question 3)*

The openWakeWord library is Apache-2.0; the author's own model repo
(`huggingface.co/davidscripka/openwakeword`) is tagged **cc-by-nc-sa-4.0**, and mirrors
disagree (`littlebearlabs` Apache-2.0, `harvestsu` none).

| Use | Verdict |
|---|---|
| Personal development on Efe's machine | **Acceptable.** NC permits personal, non-commercial use |
| Internal use at an organisation | **Requires review** — "non-commercial" is narrower than "not sold" |
| Distribution / open-sourcing / commercial | **Blocking** — must be resolved or the artifact replaced |

Mitigation already designed in: ADR-0023's custom model removes the dependency at Phase 6a.
The preprocessors (Apache-2.0, tier C) remain and are fine.

**Not a G0 blocker.** Correctly identified, registered, and owned by the project itself.

#### AUD-I03 — Nine deferred ADRs are **ACCEPTABLE before Phase 1** *(question 7)*

ADR-0001, 0005, 0017, 0019, 0021, 0023, 0024 and the rest await running code, deployable
services, or an audio pipeline. Each names the gate that will cover it
(`CI_Inventory.md` §2). 19 of 28 enforced at a phase with zero implementation is strong.

Two carry a caveat: **ADR-0023** (Turkish locale) needs its CI job at G1, not G6c — the
job is locale configuration, not application code, and can exist before the code it
protects (see AUD-M05). **ADR-0019** (observability) is enforceable earlier than G5 for
metric-name conformance against `metrics.schema.json`.

#### AUD-I04 — Contract design is **SOUND** *(question 8)*

Reviewed all 30 contracts. Versioning (directory-based, so a major pin shows in a diff),
compatibility declarations (`since`/`breaking_changes`/`notes`, append-only), producers and
consumers (present on all 27 schemas), trust fields (required in all three places that
matter), and plane separation (verified — no media payload in any control-plane schema)
are all correct.

Two observations, neither blocking: the wire-permissive / config-strict asymmetry is
correct and well argued; `MCPTool` as a projection withholding authorization metadata is a
genuinely good security decision that most projects get wrong.

Gaps are AUD-N02 and AUD-N03.

#### AUD-I05 — Validation code outside `src/lionel/` does **NOT** violate the no-runtime rule *(question 6)*

18 Python files under `ci/` and `tests/`; **0** under `src/lionel/`, machine-enforced by
STRUCT-004.

The rule is scoped by glob to `src/lionel/**/*.py` and the distinction is principled: CI
gates validate the repository, are never imported by the agent, depend only on
`pyyaml`/`jsonschema`/`grpcio-tools`, and are not shipped. Phase 0 intent is intact.

I checked the obvious loophole — whether any gate imports project code or could be
repurposed as runtime scaffolding. It does not, and `_lib.py` states the boundary
explicitly.

#### AUD-I06 — Deployment, MLOps and cloud portability readiness

`deploy/` and `evals/` contain **0 files** (directories only). Correct for Phase 0 —
Phases 7 and 8. No premature commitment; ADR-0020's overlay-only portability test is well
specified. Qdrant is digest-pinned with per-arch digests recorded, which is the right
groundwork for multi-arch. **No finding.**

---

## 5. Escape-hatch governance *(question 9)*

Genuinely well designed, with one asymmetry.

| Registry | Requires owner | Requires removal gate | Policed by |
|---|---|---|---|
| `todo.registry` | Yes | Yes (`unblocked_by`) | TODO-002 |
| `licenses.unresolved_registry` | Yes | Yes (`resolve_by`) | LIC-005 |
| Shell pragma | Reason mandatory | No | `gate_shell` |
| **Artifact blockers** | **No** | **No** | — (AUD-M07) |

TODO-002 and LIC-005 policing the registries themselves is the correct pattern — the
escape hatch cannot become the loophole. **Two gaps:** artifact blockers are held to a
weaker standard than TODO comments (AUD-M07), and **no registry carries a date** — only a
gate name. If G6 slips a year, nothing signals it. Recommend an ISO date alongside every
gate reference.

---

## 6. CI exclusions *(question 4)*

| Exclusion | Applied to | Realistic bypass? | Verdict |
|---|---|---|---|
| `ci/` | `no-latest`, `no-pending`, `no-todo` | No — these hunt tokens the gates must contain | **Justified** |
| `ci/` | **`secrets`** | **Yes — proven** | **NOT justified** → AUD-C02 |
| `ci/` | `shell` (self_test only) | No — narrowly scoped to one file | Justified |
| `*.md` | `no-latest`, `no-pending`, `docker-digests` | Low but real — docs are copy-paste sources | Acceptable → AUD-N04 |

The reasoning that produced the `ci/` exclusion is sound; it was applied one gate too far.
Secret scanning is categorically different from token-pattern scanning: a gate needs the
*regex*, never a *matching literal*.

---

## 7. Reproducibility assessment *(question 10)*

| Artifact | Pinned | Tier | Owner | Deadline | Command | Gate |
|---|---|---|---|---|---|---|
| 12 resolved | Yes | A×7 B×2 C×2 D×1 | n/a | n/a | `confirm_locally` on each | — |
| `images.github_mcp` | **No** | E | **Absent** | **Absent** | Present | Prose only |

**12 of 13 fully satisfy the criterion. One satisfies command-and-gate but lacks owner and
deadline** (AUD-M07). Provenance methodology is excellent; the governance wrapper around
the single exception is weaker than the project's own standard elsewhere.

---

## 8. Why FAIL rather than CONDITIONAL PASS

CONDITIONAL PASS requires *"no implementation-safety blocker, but explicitly bounded
pre-Phase-1 actions remain."* Two findings fail that test:

**AUD-C01** is not a bounded pre-Phase-1 action — it means **G0's Definition of Done has
not been met**. "CI runs and reports" is a stated exit criterion and CI has never run. This
is not paperwork: the pipeline has never executed on the platform it targets, `.gitattributes`
has never normalised a line ending, and no third party can reproduce any claim in
`CI_Inventory.md`. Signing off would certify results I cannot verify and the author has not
demonstrated in the required environment.

**AUD-C02** is a security control with a proven bypass in an ordinary code location. It is
fixable in minutes, which makes it bounded — but it is a *safety* defect, not a scheduling
one, and CONDITIONAL PASS is explicitly reserved for the absence of safety blockers.

**AUD-M01** independently breaks a hard, self-declared G0 requirement.

Three routes to a green re-audit, any of which is quick. See `Phase0_Blockers.md`.

**This verdict should not be read as a judgement on the architecture.** The design work is
strong — stronger than most repositories that pass this gate. What has not been
demonstrated is that the machinery *runs*. That is a small distance and an important one:
a pipeline nobody has watched execute is a hypothesis.

---

## 9. Statement of independence

- No repository file was created, modified, or deleted during this audit.
- All adversarial probing was performed on an isolated copy at `/tmp/audit/repo`; probe
  residue verified zero.
- All 16 gates were executed from that copy, not from the author's reported results.
- Documentation claims were checked against implementation rather than accepted; two were
  found false (AUD-M02, AUD-M05).
- The three audit outputs are new files and modify nothing.

**Architecture is NOT frozen.** Re-audit required after blocker remediation.
