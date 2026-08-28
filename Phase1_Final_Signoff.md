# Phase 1 — Final Sign-off

| | |
|---|---|
| Gate | **G1 — Host Runtime Skeleton & Control Plane** |
| Date | Prepared 2026-08-25 · **signed 2026-08-28** |
| Architecture | **1.12.0** · `sha256:2901336ab884ae5d61143a72139822c05f55bb9ba55bf563031a4596cb22b141` |
| Scope | Every DoD clause of MASTER_PLAN_v2 §10 Phase 1, which is v1.0's Phase 1 DoD **in full** plus five |
| Method | Each clause traced to an artefact — a named test, a gate rule, or a recorded run. Not to a sentence |
| **VERDICT** | **PASS — signed by Efe, 2026-08-28. G1 closed; G2 may begin** |

---

## 1. Executive summary

**Twelve DoD clauses. Twelve have an artefact.** Eleven are checked by something that runs
without a human; one (`get_me`) can only ever be checked on the host, by hand, because it
needs a credential that must not exist in this repository.

The interesting result is not the twelve. It is that **the sign-off audit kept finding the
same defect shape** — *something that could not do its job while appearing to* — and kept
finding it in things that had been read, reviewed and shipped:

| | What it claimed | What it did |
|---|---|---|
| 1.7.0 | five hazard rows "recorded in `check_env.sh`" | nothing was there |
| 1.8.0 | `get_me` verifies the login | the pipeline closed stdin before the server could answer; **`no login` for every input** |
| audit | "401, 403 and silence are three different reports" | `set -e` killed the script on any non-zero exit; **only `pass` was reachable** |
| 1.9.0 | a `max_calls_per_turn = 40` bound in `default.toml` | last rule, no `decision`; under the contract as written, unreachable — **a bound that bounds nothing** |
| 1.9.1 | ADR-0034 and §9.14 quoting that rule | both omitted its `match.any = true` line and argued from the absent `match` — **wrong premise, right conclusion**, in the ADR written about the entry above |

**Not one of the five was caught by a gate.** All five were caught by reading a claim and
then opening the file. That is the residual gap ADR-0033's Costs section names, and it is
the one thing this sign-off asks Efe to accept knowingly rather than silently.

**Two of the five are now closed by machine, after this document was prepared.** ADR-0034
(architecture 1.10.0) makes the constraint pass part of the contract and turns a rule that
neither decides nor constrains into a load error. ADR-0035 (architecture 1.12.0) adds a
23rd gate that checks every config-language fenced block in the ADRs and
`Architecture_Freeze.md` against the file it quotes.

**Three are not, and the honest statement of what remains is prose.** The first row above is
a sentence, not a fenced block; `doc-quotes` walks past it, and so would any successor that
respects the reproducibility a gate needs. What Efe is signing includes that: **claims this
repository makes about itself in prose are still checked by a human reading carefully, and
this document is evidence about how reliable that is.**

---

## 2. v1.0's Phase 1 DoD — MASTER_PLAN_v1 §1.5

Carried forward verbatim by MASTER_PLAN_v2:639, *"v1.0's Phase 1 DoD in full, plus …"*.

| # | Clause | State | Artefact |
|---|---|---|---|
| 1 | `check_env.sh` exits `0`, green row for all six tools | **Met** | `bash scripts/check_env.sh` → `git · python3 · node · uv · docker` ok, `cl` deferred to G6 and reported non-blocking. Table in `ci/policy/policy.yaml` → `preflight`, shape checked by `tests/unit/test_preflight.py` |
| 2 | `git log` shows exactly one commit, `[LIONEL-CORE] Phase 1: project scaffold` | **Superseded** | v1.0 modelled Phase 1 as one session. v2.0 §10 does not, and G1 spans many commits. The plan changed this, not the work |
| 3 | `git status --porcelain` clean; `.env` absent | **Met** | Clean at sign-off. `.gitignore` excludes `.env` and `.env.*`; `git ls-files` matches neither. `gate_secrets` scans with zero path exclusions |
| 4 | Filesystem MCP server starts, lists the root, refuses `C:/Windows/System32/drivers/etc/hosts` | **Met** | `check_env.sh --live`, host, 2026-08-25. **Both halves**: `.python-version` inside the root reads `3.11`; the outside path returns `isError` with *"path outside allowed directories"*. Either half alone proves nothing |
| 5 | GitHub MCP container starts; `get_me` returns Efe's login | **Met — by hand, and only by hand** | `check_env.sh --live`, host, 2026-08-25, **re-run after the reporting fix** → `ok github verified — get_me returned login denizefekaracakaya`, from the digest-pinned image, credential resolved through `secret://env/GITHUB_PAT`. The verdict carried no *"live check(s) did NOT run"* note. See §4 for why that sentence is the load-bearing one |
| 6 | `docs/decisions/ADR-0001-brain-adapter.md` exists and is committed | **Met, under a different name** | The file is `ADR-0001-swappable-brain-provider.md`. Same ADR number, same decision; the slug in v1.0's DoD was never the delivered filename. `MASTER_PLAN_v1.md` is a frozen historical record (`markdown.exempt_reasons`) and is **not** corrected — recording the mismatch here is the correction |
| 7 | Every `.sh` in `scripts/` has LF endings | **Met, and enforced** | `file scripts/*.sh \| grep -c CRLF` → `0`. No longer a manual check: `SH-CRLF` fails any `.sh` with CRLF, `CHECKSUM-004` fails any checksum-set file, and `ci/self_test.sh` plants both |

---

## 3. What G1 adds — MASTER_PLAN_v2 §10

| # | Clause | State | Artefact |
|---|---|---|---|
| 8 | Coordinators satisfy contract tests with stub implementations | **Met** | `tests/contract/test_coordinators.py`, 15 tests. ADR-0008's state-ownership rule is enforced by the language, not by review: the four stateless coordinators are frozen dataclasses, so caching on `self` raises. `test_dispatch_offers_no_way_to_skip_the_check` reads `ToolRouter.dispatch`'s signature and fails on `force`, `skip_policy`, `unchecked`, `bypass`, `trusted` |
| 9 | Job Object kill-tree — terminating a parent leaves **zero orphaned children** | **Met** | `tests/unit/test_process_supervisor.py`. Falsified before it was trusted: a naive `terminate()` leaves a grandchild alive and the detector reports it |
| 10 | A `secret://` URI resolves and its value redacts in log output | **Met** | `tests/unit/test_secrets.py`. `SecretStr` redacts in `__str__`, `__repr__` and `__format__`, and `__eq__` against a plain `str` raises rather than comparing |
| 11 | Policy Engine denies an unregistered tool by default | **Met** | `tests/unit/test_policy_engine.py`. `_validate()` refuses a ruleset whose `defaults.decision` is not `deny`; an unregistered tool is denied before any rule is consulted |
| 12 | The pinned GitHub MCP image digest is verified | **Met** | `tests/contract/test_pinned_artifacts.py`. Falsified: a zeroed-but-well-formed digest planted in the registry leaves `docker-digests`, `artifacts`, `no-pending` and `l0-conformance` **all passing** — each reads one file, and the failure is disagreement *between* two |

---

## 4. The one clause with no automated artefact

Clause 5 needs a live GitHub credential. It cannot be a test, and it must not be: a
credential in this repository is the failure `gate_secrets` exists to prevent, and a check
that reached the network by default would be the first thing to break ADR-0007's guarantee
that the ordinary path works with the cable pulled.

So it is `--live`, opt-in, announced before it runs. Which makes **the reliability of the
reporting the whole safeguard** — and the reporting was broken twice:

- The handshake was `printf … | docker run -i`. The pipe closes when `printf` finishes; the
  server reads EOF as a hangup and tears the session down before writing a byte. It
  reported *"container started but get_me returned no login"* for every input, a valid
  credential included.
- The driver captured the result with `out="$(…)"` under `set -e`, which aborts the script
  on a non-zero exit before `$?` can be read. `skip`, `fail` and `broken` were all
  unreachable; only `pass` could ever print.

Both are fixed, and both fixes are held by tests that need no network — a fake server
reproduces exiting-on-EOF and interleaving noise with responses. The verdict line now counts
un-run live checks, so `PASS` cannot be read as *"these clauses were verified"*.

### The run that counts

Clause 5 has now passed twice, and only the second one is evidence.

The first pass, on 2026-08-25, went through a driver in which `pass` was the sole reachable
outcome. It was a green light from a traffic light with one bulb. It happened to be telling
the truth — but a signal that cannot show red carries no information when it shows green,
and signing on the strength of it would have been signing on the strength of nothing.

The second run, after both defects were fixed, went through a driver that had been
*observed failing*: forcing an unresolvable `GITHUB_PAT` produced `skip github not run —
secret://env/GITHUB_PAT does not resolve`, and the verdict said so. Only then does

```
ok    github    verified    get_me returned login denizefekaracakaya
```

mean the container authenticated, rather than meaning the check ran at all.

**What Efe is asked to accept:** clause 5's evidence is a run, witnessed once, on one
machine, through a path proven capable of reporting its own failure. It is re-runnable in
one command. It is not, and cannot be, continuously verified.

---

## 5. State at sign-off

```
gates              23/23 · 0 violations · 0 broken
rules             149
workflow jobs      27 defined · 28 on GitHub
self-test          30/30 planted violations caught
tests             118 · 1 skipped (a POSIX-only kill-tree case)
ADRs               35 · 0 pending
contracts          27 JSON Schemas + 3 protobuf · 5 planes
checksum           sha256:2901336ab88… · 76 files · verified from a clean clone
CRLF               0 files
preflight          6 tools · 4 packages · 7 hazard rows · 2 live checks
```

**This block was 1.8.0's when the document was prepared on 2026-08-25, and it went stale
across four versions while the document sat unsigned.** Refreshed 2026-08-28, immediately
before signing. Nothing in §2 or §3 moved — every clause was met at 1.8.0 and is met now —
but a sign-off whose own state block is false would have been signed rather than caught,
which is a small instance of exactly what §1 is about.

**These numbers are now frozen.** §7 carries a signature, so this is a dated record and the
block stops tracking the present. Refreshing it again would be editing the archive.

Four of the seven Git Bash hazard rows are gate rules (`SH-MSYS-DOCKER`, `SH-BARE-PYTHON`,
`SH-CRLF`, `ARCH-017`), one is executed by the preflight (`HAZ-DOCKER-BACKEND`), and two are
`operator` — capped at two by a test, because `operator` is the one label in this repository
carrying neither an owner nor a route to removal.

---

## 6. Open items that do not block G1

| | Severity | Owner |
|---|---|---|
| **Turkish TTS is personal-use only.** `tr_TR-dfki-medium` is CC-BY-NC-SA-4.0 and is the only Turkish voice. Blocks distribution, not Phase 1. Replacing it needs an ADR amending ADR-0017 — **Efe's call**, R-A15 | Major | sensory · G6c |
| **A host fact cannot be checked from CI.** Mitigated by `check_env.sh`; the residual risk is that nothing forces it to run, and nothing can. Route to closure is a checklist step at each gate, R-A20 | Moderate | platform · G2 |
| ~~**Constraint-only policy rules contradict the contract.**~~ **Closed 2026-08-27.** ADR-0034 accepted; `policy-ruleset.schema.json` is 1.1.0 and states both passes, and a rule that neither decides nor constrains is now a load error. Architecture 1.10.0, §9.16 | — | closed |
| **ADR-0029 rule 1 has no gate.** Append-only is enforced by a `PreToolUse` hook that sees `Edit`/`Write` but not `sed` through `Bash`. A guardrail, not a proof | Minor | architecture |
| **Claims about what a file contains are HALF checked.** `doc-quotes` (ADR-0035, closed 2026-08-28) checks every config-language fenced block in the ADRs and `Architecture_Freeze.md` against the file it quotes — `QUOTE-001`–`QUOTE-003`, architecture 1.12.0, §9.18. **Prose claims stay unchecked**, and a fourth instance of this shape was found on 2026-08-27, inside the ADR written about the third | Minor | architecture |

---

## 6b. The live checks, witnessed

Clauses 1, 4 and 5 are the ones no machine re-checks on its own. One command exercises all
three:

```bash
bash scripts/check_env.sh --live
```

The bar is `ok filesystem verified`, `ok github verified — get_me returned login …`, and a
verdict carrying **no** "live check(s) did NOT run" note. A `skip` there is not a pass, and
the preflight says so in as many words.

**Run on the host 2026-08-25, immediately before this document was prepared:**

```
ok    filesystem  verified   reads inside the root, refuses outside it —
                             Access denied - path outside allowed directories
ok    github      verified   get_me returned login denizefekaracakaya

PASS  everything required now is present.
note  1 item(s) are needed at a later gate, not yet.
```

**Re-run on the host 2026-08-28, immediately before signing:**

```
ok    HAZ-DOCKER-BACKEND wsl2       6.18.33.2-microsoft-standard-WSL2

ok    filesystem  verified   reads inside the root, refuses outside it —
                             Access denied - path outside allowed directories
ok    github      verified   get_me returned login denizefekaracakaya

PASS  everything required now is present.
note  1 item(s) are needed at a later gate, not yet.
```

Both live checks verified, from the digest-pinned container, with the credential resolved
through `secret://env/GITHUB_PAT` and passed into the child process environment and nowhere
else. The single `note` is `cl` — VS Build Tools, needed at G6 and correctly non-blocking
here. No live check was skipped.

**It took three attempts on 2026-08-28, and the two that failed are the more interesting
evidence.** The first reported `skip github — no Docker daemon`. The second, with Docker
started, reported `skip github — secret://env/GITHUB_PAT does not resolve (SecretNotFound)`.
Two different causes, each named exactly, each refusing to read as a pass: `PASS everything
required now is present`, and immediately beneath it, *"PASS above means the environment is
ready, not that those clauses were verified."*

That is the whole of §4's argument, demonstrated rather than asserted. A signal that cannot
show red carries no information when it shows green — and this one was watched showing red
twice, for two distinct reasons, within the hour before it showed green. **Clause 5's
evidence is a run through a driver observed failing on the same day it passed**, which is
the strongest form this clause can take on one machine.

What remains true, and is not fixed by any of this: it is a run, on one host, at one moment.
It is re-runnable in one command and it is not continuously verified. That is R-A20, and
§6 carries it.

---

## 7. Sign-off

| | |
|---|---|
| Signed | **Efe · 2026-08-28** |
| Verdict | **PASS — G1 closed, Phase 2 (Memory Service, G2) may begin** |
| Architecture at signing | 1.12.1 · `sha256:029c9ee946a4b0cce6937939212b1a600735f56180843d49fa75fa867ba9c54e` |
| Live checks | both verified on the host 2026-08-28, §6b |

**This document is now a dated record.** Its numbers describe what was true at signing and
must not be refreshed again — §5's state block stops tracking the present here.
`doc_claims.out_of_scope` names the signature as this document's route out of the registry,
and this is that day: the entry's reason becomes `Phase0_Final_Signoff.md`'s.

`STRUCT-004` stays dormant, `repository.runtime_code_forbidden_until` stays `null`, and
Phase 2's first commit is now in scope. **G2's gate is the Memory Service, and its DoD is
MASTER_PLAN_v2 §10 Phase 2** — including the two v1.0 criteria carried forward verbatim, the
persistence proof across `compose down && up` and the semantic-recall test that keyword
matching must fail.
