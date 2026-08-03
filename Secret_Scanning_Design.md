# Secret Scanning Design

**Remediation of AUD-C02.** Why the secrets gate no longer excludes `ci/`, and why the new
design cannot be bypassed by putting a credential there.

| | |
|---|---|
| Finding | AUD-C02 (Critical) — secret scanning fully bypassed under `ci/` |
| Status | **RESOLVED** |
| Gate | `ci/gates/gate_secrets.py` |
| Policy | `ci/policy/policy.yaml` → `secrets:` |
| Path exclusions | **None. Zero. Every file is scanned.** |

---

## 1. What was wrong

The old gate opened with:

```python
if r.startswith("ci/"):
    continue
```

An audit proved the consequence:

| Planted | Location | Old result |
|---|---|---|
| AWS access key | `ci/policy/` | **undetected** |
| AWS access key | `ci/gates/` | **undetected** |
| PEM private key | `ci/` | **undetected** |
| AWS access key | `config/` (control) | caught |

The stated rationale was *"gates and their self-test necessarily contain the strings they
hunt."* That is true for token-pattern gates — `no-latest` must contain the literal
`latest` — and it was **generalised across categorically different gates.**

The distinction that was missed:

> A secret-scanning gate needs the **pattern** `AKIA[0-9A-Z]{16}`.
> It never needs a **string that matches it**.

One exclusion was applied to hide one fixture. An entire directory went unscanned, in a
place nobody would think of as exempt, while ADR-0015's whole posture — `secret://` URIs,
`SecretStr` redaction — sits *behind* the assumption that a literal in the tree is caught.

---

## 2. Why the exclusion turned out to be unnecessary

The remediation began with a measurement rather than a redesign. Two questions:

**Q1 — Do the regexes match their own source text?**

```
SEC-AWS        AKIA[0-9A-Z]{16}                    self-match: no
SEC-GH         gh[pousr]_[A-Za-z0-9]{36,}          self-match: no
SEC-ANTHROPIC  sk-ant-[A-Za-z0-9_\-]{20,}          self-match: no
SEC-OPENAI     sk-[A-Za-z0-9]{32,}                 self-match: no
SEC-PEM        -----BEGIN [A-Z ]*PRIVATE KEY-----  self-match: no
SEC-SLACK      xox[baprs]-[A-Za-z0-9-]{10,}        self-match: no
```

**None of them.** The reason is structural: in `AKIA[0-9A-Z]{16}` the character after
`AKIA` is `[`, which is not in `[0-9A-Z]`. A character class never matches its own bracket
notation. So `ci/policy/policy.yaml` — the file holding all six patterns — never needed
excluding at all.

**Q2 — What, with no exclusions anywhere, would actually trip?**

Two files. `ci/self_test.sh`, holding one literal AWS key as a fixture. And
`Phase0_Audit_Report.md`, quoting that same literal three times in evidence.

**The `ci/` exclusion — an entire directory of security tooling left unscanned — existed
to hide a single string.**

---

## 3. The new design

### 3.1 No path exclusions

`gate_secrets.py` walks the whole tree. The only skips are non-source directories shared
with every other gate (`.git`, `models/`, `data/`, `logs/`, `vendor/`, `__pycache__`), and
`ci` is deliberately absent from that set with a comment saying so.

The gate scans **itself**, and it scans the policy file that configures it.

### 3.2 Fixtures are generated, never stored

Patterns declare fragments instead of literals:

```yaml
- id: SEC-AWS
  regex: "AKIA[0-9A-Z]{16}"
  sample_parts: ["AKIA", "IOSFODNN7EXAMPLE"]
  negative_sample: "AKIA-not-a-key"
```

The **join** matches. The **source line does not**, because the `", "` between the parts
breaks the pattern — after `AKIA` comes `"`, which is not in `[0-9A-Z]`.

No matching literal exists anywhere in the repository. Verified: a scan for all six
patterns across every file returns **0 hits**.

### 3.3 Two structural invariants, proven on every run

These are what make exclusions unnecessary, and they are *checked*, not assumed:

| Rule | Asserts | Why it matters |
|---|---|---|
| **SEC-SELF-REGEX** | No pattern matches its own regex source | If someone adds a self-matching pattern, the gate fails and forces a redesign — instead of creating exactly the pressure that produced AUD-C02 |
| **SEC-SELF-SPEC** | No individual `sample_parts` fragment matches on its own | A fragment that matches alone *is* a credential-shaped literal in the repo, which is the thing `sample_parts` exists to prevent |

### 3.4 The regexes are themselves tested

| Rule | Asserts | Catches |
|---|---|---|
| **SEC-REGEX-POS** | Each pattern matches its generated sample | A detector broken by a typo. **This is the most dangerous failure this gate can have** — a regex that matches nothing reports a clean repository forever, indistinguishable from success |
| **SEC-REGEX-NEG** | Each pattern rejects its near-miss | An over-broad pattern. False positives are how a security gate gets disabled by the third person who hits one |
| **SEC-REGEX-BAD** | Every pattern compiles | An uncompilable regex silently detects nothing |

Runnable alone: `python3 ci/gates/gate_secrets.py --verify-patterns-only` → 32 checks.

### 3.5 The self-test plants outside the repository

`gate_secrets.py` accepts `--root DIR`. `ci/self_test.sh` now:

1. Reads `sample_parts` from policy and **joins them at runtime**
2. Writes the credential into `$(mktemp -d)` — outside the repository entirely
3. Runs `gate_secrets.py --root $TMP`
4. Asserts exit 1 and `SEC-AWS` in the output
5. Deletes the temp tree

**Nothing is ever written into the repository to test it.** The old design had to plant
inside `config/`, which is why the fixture literal existed in the first place.

### 3.6 A policy exclusion is itself a violation

**SEC-EXCLUDE** fails the gate if `ci/policy/policy.yaml` ever grows an `exclude`,
`exclude_paths` or `skip_paths` key under `secrets:`. Reintroducing AUD-C02 through
configuration now breaks the build.

### 3.7 A coverage floor

**SEC-COVERAGE** fails if fewer than 50 files are scanned. A collapse in coverage — a
directory rename, a widened skip — previously looked identical to a clean repository.
`checks_run` now counts **files examined** (149 checks over 111 files) rather than
violations found.

---

## 4. Why this cannot be bypassed via `ci/`

Four independent reasons, in descending order of strength:

**1. There is no code path that skips `ci/`.** The old `if r.startswith("ci/"): continue`
is gone. Scanning is unconditional; a bypass would require editing the gate, which is
itself a reviewed change.

**2. Reintroducing it via config fails the build.** SEC-EXCLUDE rejects any path-exclusion
key in the secrets policy.

**3. The reason anyone wanted the exclusion no longer exists.** SEC-SELF-REGEX and
SEC-SELF-SPEC guarantee no file in the tree — including the policy and the gate itself —
contains a matching literal. There is no legitimate motive to exclude `ci/`, so the
argument for it cannot be made in good faith again.

**4. The self-test proves it rather than asserting it.** `ci/self_test.sh` plants a
generated credential and asserts detection on every run.

### Re-test of the audit's own probes

| Probe | Before | After |
|---|---|---|
| 3a — AWS key in `ci/policy/` | BYPASS | **CAUGHT** |
| 3b — AWS key in `ci/gates/` | BYPASS | **CAUGHT** |
| 3c — PEM private key in `ci/` | BYPASS | **CAUGHT** |
| *new* — GitHub token in `ci/self_test.sh` | — | **CAUGHT** |
| *new* — AWS key in `ci/policy/policy.yaml` itself | — | **CAUGHT** |
| 3d — AWS key in `config/` (control) | caught | **CAUGHT** |
| negative control — clean tree | — | **PASS**, no false positives |

The fourth and fifth rows are the ones that matter: the gate detects a credential planted
in **its own test harness** and in **its own configuration file**.

---

## 5. One narrowing that is *not* a path exclusion

The `secret://` URI **well-formedness** check applies only to `.json`, `.toml`, `.yaml`,
`.yml`.

This is a **config-correctness** check, not a security check. Prose legitimately
illustrates URI shapes — ``secret://env/NAME`` appears throughout the ADRs — and a
malformed URI in a sentence does nothing at runtime. Removing the scope produced 21 false
positives, all of them valid URIs in markdown inline code where the trailing backtick was
captured and broke the anchor.

The distinction, stated plainly because it is exactly the reasoning that failed last time:

> **Narrowing which *check* applies to a file type** is different from
> **excluding a *file* from scanning.**
> AUD-C02 was the latter. This is the former.

The secret-literal scan — the security-relevant one — runs on every file with no exemption
of any kind.

A related syntactic rule replaces what used to be a path-based skip: a `secret://`
occurrence containing regex metacharacters (`(`, `|`, `[`, `\`) is a *pattern definition*,
not a *usage*. That is a property of the string itself, not of the file it lives in, so no
location-based exception is needed to tell them apart.

---

## 6. Verification

```bash
python3 ci/gates/gate_secrets.py                    # PASS · 149 checks · 111 files
python3 ci/gates/gate_secrets.py --verify-patterns-only   # PASS · 32 checks
bash ci/self_test.sh                                # 9/9 planted violations caught
```

**Residual literals in the repository: 0** — verified by scanning every file with all six
patterns.

---

## 7. Files changed

| File | Change |
|---|---|
| `ci/gates/gate_secrets.py` | Rewritten. No path exclusions; `--root`; `--verify-patterns-only`; SEC-SELF-REGEX, SEC-SELF-SPEC, SEC-REGEX-POS/NEG/BAD, SEC-EXCLUDE, SEC-COVERAGE |
| `ci/policy/policy.yaml` | `secrets:` section only — `sample_parts` and `negative_sample` per pattern; no exclusion keys |
| `ci/self_test.sh` | Secret fixture generated at runtime into a temp tree outside the repo; added a regex self-test case (8 → 9) |
| `Phase0_Audit_Report.md` | Redacted 3 key-shaped literals to `AKIA<16-char-example>`. Required for the gate to pass, and correct hygiene — security documentation should not carry full credential-shaped strings |
| `Policy_Gates.md` | Scope-exclusions table corrected; it documented the now-removed exclusion |
| `Secret_Scanning_Design.md` | This document |

No other file was modified.

---

## 8. What this does not fix

Stated so the remediation is not mistaken for more than it is.

- **Pattern-based detection only.** Six known formats. A novel token shape, or a
  high-entropy string not matching a known pattern, is not detected. This is not a
  substitute for a dedicated secret-scanning service.
- **No history scan.** A credential committed and later removed remains in git history.
  The workflow sets `fetch-depth: 0` so a history scan can be added without another
  workflow change, but none exists yet.
- **AUD-M02 is only partly addressed.** `gate_secrets` now counts files examined and has a
  coverage floor. The other five gates with the same defect still count violations rather
  than coverage.
