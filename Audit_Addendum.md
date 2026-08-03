# Phase 0 Audit — Addendum 1

**Scoped re-verification.** This is **not** a re-audit.

| | |
|---|---|
| Parent | `Phase0_Audit_Report.md` (2026-08-02, verdict **FAIL**) |
| Scope | Only findings touched by three changes: the AUD-C02 remediation, `ADR0013_Review.md`, and `Turkish_TTS_Decision.md` |
| Explicitly **not** re-checked | AUD-M02 · M03 · M04 · M05 · M06 · M07 · N01–N06 · I01–I06 · all 19 original probes |
| Method | Targeted probe replay + structural inspection. No repository file modified |
| Date | 2026-08-02 |
| **Verdict** | **FAIL — unchanged.** 1 Critical and 1 Major blocker remain open |

---

## 1. Status board

| ID | Severity | Previous | **Now** | Blocks G0 |
|---|---|---|---|---|
| **AUD-C02** | Critical | OPEN | ✅ **RESOLVED** | no |
| **AUD-C01** | Critical | OPEN | **OPEN** *(untouched)* | **yes** |
| **AUD-M01** | Major | OPEN | **OPEN** — reviewed, not remediated | **yes** |
| **R-A12** | Major | OPEN | ⬇ **DOWNGRADED to Minor** | no |
| **AUD-M08** | Major | — | 🆕 **NEW** — coupled to AUD-M01 | via M01 |
| **AUD-N07** | Minor | — | 🆕 NEW | no |
| **AUD-N08** | Minor | — | 🆕 NEW | no |
| **AUD-I07** | Informational | — | 🆕 NEW | no |

**Net: one Critical closed. One Major downgraded. Four new findings, none of them blocking
on its own.**

---

## 2. AUD-C02 — Secret scanning bypass · **RESOLVED**

### Verification performed

Replayed the original probes with the payload **generated from `sample_parts`** rather than
stored, so the test itself introduces no literal:

| Probe | Original result | **Now** |
|---|---|---|
| 3a — AWS key in `ci/policy/` | BYPASS | **CAUGHT** |
| 3b — AWS key in `ci/gates/` | BYPASS | **CAUGHT** |
| 3c — PEM private key in `ci/` | BYPASS | **CAUGHT** |
| 3d — AWS key in `config/` (control) | caught | **CAUGHT** |

### Structural confirmation

| Check | Result |
|---|---|
| Path exclusion in gate code | **none** |
| Exclusion key in `secrets:` policy | **none** — and `SEC-EXCLUDE` now fails the build if one reappears |
| Residual credential-shaped literals in the whole repo | **0** |
| Files scanned | **114** (previously the gate reported 7 checks) |
| `gate_secrets.py` exit | **0** |
| `--verify-patterns-only` | **PASS**, 32 checks — regexes are exercised, not merely present |
| Self-test | **9/9** planted violations caught (was 8/8) |

### Collateral

Seven other gates re-run: `shell`, `markdown`, `structure`, `no-latest`, `no-pending`,
`licenses`, `architecture` — **all exit 0.** The fix disturbed nothing.

### Auditor assessment

**Accepted.** The remediation is stronger than the finding required, and the reasoning is
the part that convinces me: rather than narrowing the exclusion, the author **measured
whether it was needed at all** and found that none of the six regexes matches its own
source text. `ci/policy/policy.yaml` never required exclusion; the entire directory was
exempted to hide one literal in one file.

Three design elements make recurrence unlikely rather than merely unlikely-for-now:

- **SEC-SELF-REGEX** makes the enabling property machine-checked. A future self-matching
  pattern fails the gate instead of creating pressure for a new exclusion.
- **SEC-EXCLUDE** makes reintroduction-by-config a build failure.
- **Fixtures are generated and planted outside the repository**, removing the motive.

The remediation also partially addresses **AUD-M02** — `gate_secrets` now counts *files
examined* (114) rather than violations found, and carries a 50-file coverage floor. **The
other five gates with that defect are unchanged**; AUD-M02 remains open and was not
re-checked here.

---

## 3. AUD-M01 — Unresolved GHCR digest · **OPEN, unchanged**

### Verification performed

| Check | Result |
|---|---|
| ADR count | **28** — no ADR-0029 adopted |
| `ADR-0013` file modified since audit | **no** (timestamp unchanged) |
| `images.github_mcp` status | **UNRESOLVED** |
| `required_by` / `l0_critical` / `owner` / `resolve_by` present | **NONE** |
| `meta.gate` in lockfile | still *"G0 blocks while unresolved > 0"* |
| `gate_artifacts.py` exit | **1** |

### Auditor assessment

**`ADR0013_Review.md` is a proposal, and a proposal does not resolve a finding.** The
review carries three explicit "requires approval" markers, ADR-0013 is byte-unchanged, and
the gate still fails on the criterion as written.

I record two things about the review itself, as an auditor rather than a participant:

**The reasoning is sound and I concur with the recommendation.** I raised AUD-M01 noting
that the artifact is deferrable on technical merit and blocks only because the project said
so. The review independently reached the same place by a stronger route — it found that
ADR-0013's own Decision says *"verified before use"* and its own Verification assigns the
digest to G1. That is a better argument than the one in my report.

**But the review also surfaced a new finding, recorded below as AUD-M08.** The
contradiction it identified exists *regardless* of which resolution is chosen, and it means
the criterion AUD-M01 cites is itself unsound. That changes the character of AUD-M01 from
"blocked by a clear rule" to "blocked by a rule that cannot be complied with as written."

**AUD-M01 remains a G0 blocker.** Either remediation path in `Phase0_Blockers.md` Blocker 3
still applies — resolve the digest, or adopt an approved amendment. Neither has happened.

---

## 4. AUD-M08 🆕 — ADR-0013 is internally contradictory · **Major**

**Evidence** — all three clauses confirmed present in `docs/decisions/ADR-0013-artifact-pinning.md`:

| Clause | Location | Assigns to |
|---|---|---|
| *"Everything external is pinned, checksummed, and verified **before use**"* | Decision | use-time |
| *"Gate **G1**: the pinned GitHub MCP image digest is verified at pull"* | Verification, line 2 | **G1** |
| *"fails closed … on any `UNRESOLVED` entry"* at Gate **G0** | Verification, line 1 | **G0** |

**Affected** `docs/decisions/ADR-0013-artifact-pinning.md` · `artifacts.lock.yaml` (`meta.gate`) · `ci/gates/gate_artifacts.py` (ART-000)

**Impact** The ADR assigns an artifact to G1 by name and blocks G0 on it in the adjacent
sentence. **It cannot be complied with as written.** An unenforceable rule is worse than
either a strict or a permissive one, because it trains readers to skip the parts that do
not make sense — and this ADR governs the project's supply chain.

Severity **Major** rather than Minor: ADR-0016 makes ADRs the durable source of authority,
and an authority that contradicts itself undermines the mechanism generally, not just this
artifact.

**Blocks G0** — not independently. It is **coupled to AUD-M01**: both remediation paths in
`ADR0013_Review.md` §6 and §10 resolve it as a side effect. It cannot be closed *without*
closing AUD-M01, and vice versa.

**Required remediation** Either adopt ADR-0029 (Decision and mechanism both become
"before use"), **or** keep the strict rule and delete the G1 sentence while amending the
Decision to say "resolved before G0". **Leaving both clauses is not an option.**

**Verification** `grep` confirms exactly one of the two conflicting assignments remains.

---

## 5. R-A12 — Turkish TTS single candidate · **DOWNGRADED to Minor**

### Verification performed

| Check | Result |
|---|---|
| ADR-0017 modified | **no** |
| ADR-0023 modified | **no** |
| `evals/` corpus files | **0** |
| `piper_tr_dfki` lockfile entry | unchanged; licence still *"verify per MODEL_CARD"* |
| Stage 0 listening test | **not run** |

### Auditor assessment

**Downgraded Major → Minor. Not closed.**

The original risk was *"one candidate and no fallback."* `Turkish_TTS_Decision.md`
demonstrates that the second half was wrong, and the finding is worth stating precisely:

> A **custom fine-tuned Piper voice** shares the entire runtime with `tr_TR-dfki-medium` —
> same ONNX, same inference, same container, same latency profile. Switching is a lockfile
> change and an eval run. **Architectural cost: zero.**

A risk with a zero-cost mitigation already designed into the architecture is not Major. The
`TTSProvider` port from ADR-0017 is what makes the fallback free, which is the abstraction
paying for itself before any code exists.

**Why it is not closed:**

1. **Nothing has been verified by listening.** dfki's quality remains unknown to every
   party, including the author, who says so explicitly.
2. **No ADR was amended.** The recommendation to promote the custom voice from polish to
   risk-control is a proposal.
3. **No corpus exists.** `evals/` is empty.
4. **The dfki voice licence is still unresolved** — registered to `sensory` for G6c, so
   correctly tracked, but open.

**The scheduling recommendation is sound and I endorse it.** Stage 0 — listening to the
published dfki samples — requires no implementation and would convert the largest
unmitigated sensory unknown into a known quantity. Deferring it to G6c means a negative
answer arrives after the pipeline is built around it.

---

## 6. AUD-I07 🆕 — XTTS-v2 is permanently unavailable · **Informational**

**Evidence** XTTS-v2 weights ship under the Coqui Public Model License — **non-commercial**
(the `coqui-ai/TTS` code is MPL-2.0; the weights are not). **Coqui Inc. dissolved in January
2024**, so no entity survives to sell a commercial licence. Independently, its CPU
real-time factor is **1.41** — slower than real time, failing the L0 CPU constraint before
licensing is even considered.

**Impact** This is worth recording as an audit finding because it is a **permanently closed
door**, and it is categorically different from the openWakeWord non-commercial ambiguity
(`Artifact_Verification_Report.md` §4), which is at least *resolvable* by asking someone. A
licence with no surviving licensor cannot be negotiated, clarified, or purchased — ever.

**Net effect on risk: mildly positive.** XTTS-v2 is the option a reasonable engineer would
propose whenever Turkish TTS comes up. Documenting its rejection prevents the analysis being
re-litigated, and removes a path that would have silently foreclosed distribution.

**Blocks G0** — no. Recommend carrying it into `Architecture_Risk_Register.md` as a closed
option rather than an open one.

---

## 7. New findings introduced by the AUD-C02 fix

Both Minor. Recorded because a remediation that introduces regressions unnoticed is how
fixes accumulate debt.

### AUD-N07 — Duplicate file-walker · Minor

`gate_secrets.py` defines its own `SKIP_DIRS` and `walk()` rather than using
`_lib.repo_files()`.

| Walker | Skip dirs | Divergence today |
|---|---|---|
| `_lib.repo_files()` | 13 | — |
| `gate_secrets.walk()` | 13 | **none** |

Identical **today**. Two independent implementations of the same policy will drift: adding
a skip directory to `_lib` will not reach the secrets gate, and the divergence will be
silent in both directions.

Mildly ironic in context — the same remediation round collapsed
`scripts/verify_artifacts.sh` into `gate_artifacts.py` for precisely this reason
(*"duplicated policy across two files is how the two quietly disagree"*).

**Remediation** Extend `_lib.repo_files()` to accept a `root` argument and have
`gate_secrets` use it. **Verification** One walker in the codebase.

### AUD-N08 — `--root` disables the coverage floor · Minor

`SEC-COVERAGE` is guarded by `root == ROOT` (line 238). A `--root` invocation on a
one-file tree reports **`PASS 33 checks`** with no coverage complaint.

Not exploitable through the committed workflow, which invokes the gate with no arguments.
But `--root` is the path the **self-test** uses, so the defence against silent coverage
loss is absent on the only path routinely exercised with a small tree.

**Remediation** Apply a proportional floor on `--root` runs, or have the self-test assert
an expected scanned-file count. **Verification** A `--root` run on a near-empty tree fails
or warns.

### Not a regression: URI check scope

A malformed `secret://bogus/thing` in a `.sh` or `.py` is unflagged, because URI
well-formedness is scoped to config file types. **The previous gate behaved identically** —
its URI loop also iterated only `.json/.toml/.yaml/.yml`. This is a pre-existing gap now
made explicit and justified rather than accidental. **No finding.**

---

## 8. Verdict

### **FAIL — unchanged**

| Blocker | Status |
|---|---|
| **AUD-C01** — repository not under version control; CI has never executed | **OPEN** — untouched by this round |
| **AUD-M01** — unresolved GHCR digest | **OPEN** — reviewed, not remediated |
| **AUD-M08** — ADR-0013 contradicts itself | **OPEN** — coupled to M01; resolves with it |
| ~~AUD-C02~~ — secret scanning bypass | ✅ **RESOLVED** |

**One of the three original blockers is closed.** AUD-C01 remains the decisive one: it is a
hard G0 Definition-of-Done requirement (*"CI runs and reports"*), and every claim in this
addendum — including my own verification of the AUD-C02 fix — rests on scripts executed
locally rather than on a pipeline anyone can observe.

That constraint applies to me as much as to the author. I re-ran the probes and they
passed. I cannot show you a CI run that did.

### Path to re-audit

Unchanged from `Phase0_Blockers.md`, minus Blocker 2:

1. **AUD-C01** — `git init`, stage, present for approval, push, attach the run URL.
2. **AUD-M01 + AUD-M08 together** — resolve the digest, **or** adopt an approved amendment
   that removes the contradiction. Either path closes both.

Estimated remaining effort: **well under one session.**

---

## 9. Scope statement

This addendum re-verified **only** the findings affected by the three named changes. The
following were **not** re-checked and retain their status from the parent report:

`AUD-M02` (check counters — *partially* addressed in `gate_secrets` only) · `AUD-M03`
(invalid image ref in the capability registry) · `AUD-M04` (syntactic architecture checks;
two proven bypasses) · `AUD-M05` (no Windows or Turkish-locale CI job) · `AUD-M06`
(self-test covers 9 of 16 gates — up from 8, still not full coverage) · `AUD-M07` (artifact
blockers need no owner or deadline) · `AUD-N01`–`AUD-N06` · `AUD-I01`–`AUD-I06`.

No repository file was modified during this addendum. Probe payloads were generated at
runtime and planted only in temporary directories; residue verified zero.

**Architecture remains unfrozen.**
