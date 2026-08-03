# Phase 0 Blockers — G0 Rejection

**Verdict: FAIL.** Three findings must clear before re-audit. Estimated total effort:
**one working session.**

| ID | Severity | Title | Effort |
|---|---|---|---|
| **AUD-C01** | Critical | Repository not under version control; CI has never executed | ~30 min + one CI run |
| **AUD-C02** | Critical | Secret scanning fully bypassed under `ci/` | ~20 min |
| **AUD-M01** | Major | Artifacts gate red — unresolved GHCR digest | ~5 min, **or** an ADR amendment |

Nothing below requires redesign. Every blocker is a gap between what the architecture
claims and what has been demonstrated.

---

## BLOCKER 1 — AUD-C01

### Repository is not under version control; CI has never executed

**Why this blocks.** MASTER_PLAN_v2 Phase 0 DoD requires *"CI skeleton with the L0 gate
wired (failing is fine; **present is mandatory**)"* and *"CI runs and reports"*. The
workflow file exists. The pipeline has never run.

**What is currently inert, not merely unproven:**

| Control | State |
|---|---|
| `.gitattributes` `*.sh text eol=lf` | Never applied — takes effect on first `git add`. Correct but unexercised; ADR-0014 names CRLF-in-`.sh` as the most likely Windows failure |
| `.gitignore` | Never exercised — will work on first `git add`, but the `models/` (~2 GB) and `__pycache__/` exclusions are unverified against a real staging operation |
| ADR-0016 immutability | Unenforceable without history |
| `secrets` job `fetch-depth: 0` | No history to scan |
| All 88 rules | Never executed by CI; evidence is local-only |

**Remediation**

```bash
cd /c/Users/deniz/Desktop/L.I.O.N.E.L
git init -b main
git config core.autocrlf false          # .gitattributes is authoritative
git add -A
git status --porcelain | head -40       # confirm .env absent, models/ absent
```

Then present the staged tree for approval and push, per the project's standing rule.

> **`git init` and `git add` are not commits.** The no-autonomous-commit rule governs
> `commit` and `push`. Initialising the repository and staging for review is the step that
> *enables* that review, and it has been skipped.

**Verification**

- [ ] `.git` exists; `git ls-files | wc -l` > 0
- [ ] `git ls-files --eol | grep -c 'w/crlf'` returns 0
- [ ] `.env`, `models/`, `data/`, `logs/` absent from `git ls-files`
- [ ] A GitHub Actions run exists showing 18 jobs
- [ ] 15 green · `artifacts` red · `gate-self-test` green
- [ ] Run URL attached to the re-audit request

---

## BLOCKER 2 — AUD-C02

### Secret scanning is fully bypassed under `ci/`

**Why this blocks.** Proven by probe on an isolated copy:

```
ci/policy/_probe.yaml   AWS key      → gate_secrets exit 0   BYPASS
ci/gates/_probe.py      AWS key      → gate_secrets exit 0   BYPASS
ci/_probe.txt           PEM key      → gate_secrets exit 0   BYPASS
config/_probe.yaml      AWS key      → gate_secrets exit 1   caught (control)
```

`ci/gates/gate_secrets.py:22-24` excludes the entire `ci/` tree.

**The reasoning was right; the scope was wrong.** *"Gates and their self-test necessarily
contain the strings they hunt"* holds for token-pattern gates — `no-latest` must contain
the literal `latest`. It does **not** hold for secret scanning: a gate needs the *regex*
`AKIA[0-9A-Z]{16}`, never a *matching literal*. One exclusion was generalised across
categorically different gates.

Severity is Critical because ADR-0015's whole posture — `secret://` URIs, `SecretStr`
redaction — is defence-in-depth *behind* the assumption that a literal in the tree is
caught. `ci/` is an ordinary place for helper scripts and nobody would think of it as
exempt.

**Remediation** — pick one:

| Option | Approach | Recommended |
|---|---|---|
| **A** | Drop the `ci/` exclusion from `gate_secrets.py`. Move self-test fixtures out of the scanned tree — generate them into `$TMPDIR` at runtime | **Yes** — removes the hole and the reason for it |
| B | Per-line exemption: skip only lines carrying `# ci-policy: test-fixture` | Acceptable; narrower blast radius than a directory |
| C | Keep the exclusion, add a second scanner over `ci/` | Rejected — two scanners drift |

Keep the `ci/` exclusion for `no-latest`, `no-pending`, `no-todo`, where it is justified.

**Verification**

- [ ] Probe 3 repeated: all four planted credentials caught
- [ ] `config/` control still caught
- [ ] `bash ci/self_test.sh` still 8/8
- [ ] `bash ci/run_gates.sh secrets` exits 0 on the clean tree
- [ ] Rationale in `Policy_Gates.md` §Scope exclusions updated to distinguish the two gate categories

---

## BLOCKER 3 — AUD-M01

### Artifacts gate red — unresolved GHCR digest

**Why this blocks.** On technical merit this is **Major but deferrable**: the artifact is
`requires_network: true` and already excluded at L0, the blocker is correctly classified
TEMPORARY with four reproducible alternatives, and nothing in Phase 0 consumes it.

It blocks anyway **because the project declared that it does**:

> ADR-0013 Verification — *"fails closed … on any `UNRESOLVED` entry"*
> `artifacts.lock.yaml` — *"G0 cannot be signed off until this file contains zero of them."*

Waiving a self-declared hard criterion because the finding looks small teaches the project
that its criteria are negotiable — the same erosion ADR-0007 exists to prevent, applied to
a different rule.

**Remediation** — pick one. Both are legitimate.

### Option 1 — Resolve it *(≈5 minutes)*

```bash
docker buildx imagetools inspect ghcr.io/github/github-mcp-server:<version-tag>
```

Then in `artifacts.lock.yaml`:
- `status: RESOLVED` · `digest: sha256:…` · `verification.tier: A` ·
  `provenance: registry-manifest` · `retrieved:` today
- `meta.resolved: 13` · `meta.unresolved: 0`

Update `config/capabilities.registry.json` with the real digest, which also clears
**AUD-M03**.

> Pick an explicit version tag. `:latest` is mutable and pinning it defeats the purpose.

### Option 2 — Amend ADR-0013 *(≈20 minutes, arguably better design)*

Narrow the G0 criterion to distinguish **G0-blocking** artifacts (on the L0 critical path)
from **G1-blocking** ones. The current rule treats an artifact explicitly excluded at L0 as
equally G0-blocking, which is stricter than the architecture requires.

Requires: a superseding amendment to ADR-0013, `gate_artifacts.py` implementing the
narrowed rule, and an `l0_critical: true|false` flag per artifact in the lockfile.

**Not acceptable:** signing off against the current criterion while it is unmet.

**Verification**

- [ ] `python3 ci/gates/gate_artifacts.py` exits 0, **or** ADR-0013 carries an approved amendment and the gate implements it
- [ ] If resolved: digest matches `^sha256:[0-9a-f]{64}$` and `meta` counts agree
- [ ] `config/capabilities.registry.json` contains no invalid image reference

---

## Not blockers — but fix before Phase 1 ends

These do not gate G0. Listed so they are not lost.

| ID | Title | Why it matters at Phase 1 |
|---|---|---|
| AUD-M02 | Check counters are violation counts, not coverage | Silent coverage loss; `CI_Architecture.md` §4 asserts a safety net that does not exist |
| AUD-M04 | Architecture checks are syntactic; two proven bypasses | Becomes serious the moment Phase 1 writes Python |
| AUD-M05 | No Windows or Turkish-locale CI job | ADR-0014 and ADR-0023 are unverifiable; both are Windows-first hazards |
| AUD-M06 | Self-test covers 8 of 16 gates | `artifacts` and `contracts` have never been shown to reject anything |
| AUD-M07 | Artifact blockers need no owner or deadline | Weaker standard than a TODO comment |

---

## Re-audit

Submit when all three blockers verify. Required with the request:

1. GitHub Actions run URL showing 18 jobs
2. `bash ci/run_gates.sh` output — expect **16/16 green** once AUD-M01 clears
3. `bash ci/self_test.sh` output
4. Diff of remediation changes

Re-audit will re-run all 19 probes plus the three verification sets above.

**Architecture remains unfrozen.** No design change is required by this rejection.
