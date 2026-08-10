# Architecture Risk Register

**Independent G0 audit · 2026-08-02.** Risks to L.I.O.N.E.L's architecture, ranked by
expected cost of leaving them unaddressed. Complements the project's own register in
`MASTER_PLAN_v2.md` §6 — this one is written by someone who did not choose the design.

**Scoring:** Likelihood × Impact, each Low/Med/High. Severity is the auditor's judgement,
not the product.

---

## 1. Register

| ID | Risk | L | I | Severity | Gate | Owner | Status |
|---|---|---|---|---|---|---|---|
| **R-A01** | CI never executes; controls stay inert | **High** | **High** | **Critical** | G0 | platform | **OPEN — blocks G0** |
| **R-A02** | Secret reaches the tree via `ci/` | Med | **High** | **Critical** | G0 | platform | **OPEN — blocks G0** |
| **R-A03** | Self-declared gate criteria treated as negotiable | Med | **High** | **Major** | G0 | architecture | **OPEN — blocks G0** |
| **R-A04** | Architecture gates pass syntactically while semantics drift | **High** | **High** | **Major** | G1 | core-orchestration | OPEN |
| **R-A05** | Silent CI coverage loss (counter ≠ coverage) | Med | **High** | **Major** | G1 | platform | OPEN |
| **R-A06** | Windows/Git Bash failure discovered late | **High** | Med | **Major** | G1 | platform | OPEN |
| **R-A07** | L0 erodes despite ADR-0007 | Med | **High** | **Major** | every | architecture | MITIGATED, unverified |
| **R-A08** | Untested gates fail silently when they matter | Med | Med | **Major** | G1 | platform | OPEN |
| **R-A09** | Deferrals lack dates; "later" never arrives | **High** | Med | **Major** | G1 | architecture | OPEN |
| **R-A10** | STT latency breaks the budget; tiering forced late | **High** | Med | **Major** | G6b | sensory | ACCEPTED, monitored |
| **R-A11** | Local model tool-calling too weak for L0 | **High** | **High** | **Major** | G3 | brain | ACCEPTED, measured |
| **R-A12** | Turkish TTS quality unacceptable, no fallback | Med | **High** | **Major** | G6c | sensory | OPEN — **and now licence-blocked, see R-A15** |
| **R-A13** | Provisional contracts become permanent | Med | Med | Minor | G2 | architecture | OPEN |
| **R-A14** | Tier-D artifact outlives its replacement plan | Low | Med | Minor | G6a | sensory | REGISTERED |
| **R-A15** | NC licence blocks distribution | **High** | **High** | **Major** | G6a · **G6c** | sensory | **ESCALATED 2026-08-10** |
| **R-A16** | Fabricated hash undetected until Phase 6 | Low | **High** | Minor | G6 | platform | ACCEPTED |
| **R-A17** | Embedding model changed; vectors silently invalid | Low | **High** | Minor | G2 | memory | MITIGATED |
| **R-A18** | Cancellation incomplete at L2; orphaned cluster work | Med | Med | Minor | G7 | core-orchestration | DESIGNED |
| **R-A19** | Eleven-phase plan outlasts motivation | Med | Med | **Informational** | — | Efe | **NEWLY RAISED** |

\* ~~Likelihood Low **only while use stays personal**~~ — superseded 2026-08-10. The condition was not the artifact anyone was watching. See R-A15.

---

## 2. Risks that block G0

### R-A01 — CI never executes; controls remain inert · **Critical**

The pipeline is well built and has never run. `.gitattributes` has never normalised a line
ending; `.gitignore` has never excluded anything; no GitHub Actions run exists.

The compounding factor: **every claim about the pipeline is unverifiable by a third
party.** `CI_Inventory.md` reports 15/16 green and 8/8 planted violations caught. I
reproduced both locally — but "the author ran it and it worked" is not a control, it is an
anecdote. Controls that have never fired in their target environment have an unknown
failure rate.

*Mitigation:* `Phase0_Blockers.md` Blocker 1. *Verification:* an Actions run URL.

### R-A02 — Secret reaches the tree via `ci/` · **Critical**

Proven bypass. AWS keys, GitHub tokens and PEM private keys under `ci/` are not scanned.
`ci/` is a normal home for helper scripts.

The deeper risk is **generalising a narrow exemption across categorically different
gates**. The `ci/` exclusion is correct for token-pattern gates and wrong for secret
scanning, and the difference was not noticed because both were "gates that contain the
strings they hunt". Expect this class of error to recur; the systemic fix is to require an
exemption to name the *category* it applies to, not just the path.

*Mitigation:* Blocker 2.

### R-A03 — Self-declared gate criteria treated as negotiable · **Major**

ADR-0013 says G0 blocks while any artifact is unresolved. One is. The temptation is to
observe that it is excluded at L0 and wave it through.

That reasoning is correct on the merits and corrosive as a precedent. A project whose
declared criteria bend when the finding looks small has criteria that describe intentions
rather than constraints — which is precisely the failure ADR-0007 exists to prevent, in a
different register.

The clean resolutions are: resolve the artifact, or **amend ADR-0013** so the rule matches
what the architecture actually requires. Both are honest. Waiving is not.

*Mitigation:* Blocker 3.

---

## 3. Risks materialising at Phase 1

### R-A04 — Syntactic conformance, semantic drift · **Major**

Two proven bypasses (unlisted media key name; dict-lookup provider branch). More
importantly, **most architecture checks are vacuous today**: ARCH-002 scans `.py` files and
there are none; ARCH-001 and ARCH-015 assert directories are absent. Of 19 reported checks
roughly 8 examine real content.

`19 checks PASS` reads as much stronger coverage than exists. The moment Phase 1 writes
Python, the gap between reported and actual coverage becomes the gap between believed and
actual conformance.

*Mitigation:* invert ARCH-003 to flag base64/bytes-typed properties rather than a name
list; add AST-based provider-branch detection at Phase 1; report vacuous checks distinctly.

### R-A05 — Silent coverage loss · **Major**

`checks_run` counts violations, not files examined. Four gates report `PASS 1 checks`
against an empty tree. `CI_Architecture.md` §4 claims this is impossible.

A documented safety net that does not exist is worse than no claim, because reviewers stop
looking for the failure it purports to catch.

*Mitigation:* count per item examined; add minimum-coverage floors.

### R-A06 — Windows/Git Bash failure found late · **Major**

The host runtime is Windows + Git Bash. CI runs on Ubuntu only. The project has correctly
catalogued the Windows hazards — Job Objects, CRLF, `MSYS_NO_PATHCONV`, `ProactorEventLoop`,
`MAX_PATH` — and exercises **none** of them.

Likelihood is High because these bugs are the default outcome of writing POSIX-shaped code
on a POSIX CI runner and deploying to Windows. ADR-0023's `İ/ı` bug is described by the
project itself as "invisible in English testing and guaranteed in Turkish production", and
the CI job that would make it visible does not exist.

*Mitigation:* add `windows-latest` and `tr_TR.UTF-8` jobs at G1. Both are configuration,
not application code, and can precede the code they protect.

### R-A09 — Deferrals without dates · **Major**

Every registry — TODO, licence, provisional contracts — names a *gate* (`G6`, `G6c`) and
never a *date*. Gate-relative deferral is elegant while gates arrive on schedule and
becomes unbounded when one slips. Nothing signals that "unblocked_by: G6" has been pending
for a year.

Artifact blockers are worse: they require neither owner nor deadline, a weaker standard
than the project applies to a TODO comment.

*Mitigation:* add an ISO review date alongside every gate reference; require `owner` and
`resolve_by` on artifact blockers.

---

## 4. Newly raised by this audit

### R-A12 — Turkish TTS has one candidate and no fallback · **Major**

ADR-0017 was corrected when `rhasspy/piper-voices` turned out to ship only `tr/tr_TR/dfki`.
The correction is honest and the G6c listening test was rightly removed as meaningless.

But the consequence deserves to be a tracked risk rather than a footnote: **Turkish TTS now
has exactly one candidate and no fallback.** If `dfki` is not good enough for daily use —
a judgement only Efe can make, at G6c, after the pipeline is built — the options are
reopening ADR-0017 against XTTS-v2 (heavier, GPU-preferred, licence review needed) or
converting a Piper checkpoint. Both are materially larger than a voice swap, and both
surface at the last sensory gate.

Turkish is not a nice-to-have here; it is half the product.

*Mitigation:* pull the quality judgement forward. A five-minute listening test on
`tr_TR-dfki-medium` samples, done **now**, converts a G6c surprise into a Phase 0 decision.
The samples are published in the same HF repo already pinned.

### R-A15 — NC licence blocks distribution · **Major** *(escalated 2026-08-10)*

**Raised Minor on the wrong artifact.** The register scored this against
`models.wake_bootstrap`, whose openWakeWord licence is ambiguous (NC vs Apache) and which
ADR-0023 **replaces at G6a** — self-liquidating, hence Minor, hence Low likelihood "only
while use stays personal".

Reading the MODEL_CARD that `artifacts.lock.yaml` had been deferring since 2026-08-02 shows
the same licence on a completely different artifact, with none of the properties that made
it Minor:

```
models.piper_tr_dfki   tr_TR-dfki-medium
  repo licence          MIT          (rhasspy/piper-voices)
  MODEL_CARD licence    CC-BY-NC-SA-4.0   ← governs; DFKI-OT training data
```

| | `wake_bootstrap` | `piper_tr_dfki` |
|---|---|---|
| Replaced by a named ADR | ✅ ADR-0023, at G6a | ❌ nothing planned |
| Alternatives exist | ✅ several | ❌ **it is the only Turkish voice** (R-A12) |
| Self-liquidating | ✅ | ❌ **permanent until someone decides otherwise** |
| Share-alike obligation | — | ✅ **also SA**, not merely NC |

**Impact.** Personal use — the entire scope of L.I.O.N.E.L today — is unaffected. But ADR-0023
makes Turkish first-class and MASTER_PLAN_v2 G6c's DoD requires the Turkish voice loop to
pass, so the product cannot be distributed without either dropping half its language surface
or replacing the voice. **The blocker is not at G6c. It is at whatever gate first considers
distribution**, and no such gate exists.

*Status:* recorded as an SPDX identifier in `artifacts.lock.yaml`, reviewed and accepted for
personal use in `ci/policy/policy.yaml` → `licenses.review_accepted` (owner `sensory`,
revisit at G6c, ADR-0031). The `licenses` gate now restates the scope on every run rather
than asking the same unanswered question.

*Mitigation, unchanged from R-A12 and now more urgent:* the replacement search and the
quality judgement are the same piece of work. Doing it at G6c means discovering at the last
sensory gate that both the quality **and** the licence force a rebuild. Doing it now costs
an afternoon. Either way it needs an ADR amending ADR-0017 — a technology decision, Efe's
call.

*How it was missed for eight days:* the lockfile said *"verify per MODEL_CARD before
release"* and the gate accepted that as a registered deferral. The deferral was honest and
correctly owned. It was simply never executed, because nothing forced it to be — the same
root cause behind every other finding of 2026-08-10. **A deferral with an owner and a date
is still a deferral; only reading the MODEL_CARD reads the MODEL_CARD.**

### R-A19 — Plan length versus sustained motivation · **Informational**

Eleven phases with hard gates, for a project with one developer. The discipline is
excellent and is itself a risk: G0 has produced 28 ADRs, 30 contracts, 16 gates and roughly
15,000 words of specification, and **zero lines of the agent**.

This is defensible — the review that turned v1.0 into v2.0 cost zero rework precisely
because nothing was built — but the ratio cannot persist. The plan's own value depends on
Phase 1 arriving while the reasoning behind Phase 0 is still fresh.

*Not an architectural defect.* Recorded because a gatekeeper who only counts technical
risks misses the one that actually kills projects.

*Mitigation:* consider timeboxing G1 and resisting further Phase 0 elaboration. The
foundations are sufficient; more of them is now a cost.

---

## 5. Risks the project already handles well

Recorded so remediation does not disturb them.

| ID | Risk | Why the mitigation is sound |
|---|---|---|
| R-A07 | L0 erodes | ADR-0007 makes it a permanent blocking gate rather than a principle. The correct mechanism — pending only the CI run that proves it (R-A01) |
| R-A11 | Local tool-calling too weak | ADR-0001's swappable provider defers an irreversible bet and makes the gap measurable at G3 rather than assumed |
| R-A14 | Tier-D artifact | Self-liquidating by design; `max_tier_d: 1` stops it becoming a pattern |
| ~~R-A15~~ | ~~NC licence~~ | **Withdrawn 2026-08-10.** The mitigation was sound for the artifact it was assessed against (`wake_bootstrap`, replaced at G6a). It does not extend to `piper_tr_dfki`, which has no replacement and no alternative. Moved to §2-adjacent as an escalated Major — see R-A15 |
| R-A16 | Fabricated hash | Explicitly acknowledged as discipline-enforced rather than machine-enforced. Honest labelling beats false assurance |
| R-A17 | Embedding model as hidden schema | Named as a hidden schema, pinned, with a documented re-index path. Most projects discover this in production |
| R-A18 | Cancellation at L2 | ADR-0025 specifies fan-out order and cross-boundary propagation before any code exists — unusually foresighted |

---

## 6. Systemic observations

Three patterns worth naming, because individual fixes will not address them.

**6.1 — Documentation outruns implementation.** Two claims were checked and found false:
`CI_Architecture.md` §4 on check counters, and the implied `tr_TR` CI job. Both were
written as descriptions of intent and read as descriptions of fact. The docs are otherwise
excellent, which makes the drift *more* dangerous — a reviewer who finds ninety-five
accurate claims stops verifying the ninety-sixth.

*Suggestion:* generated docs should assert only what a gate proves, and hand-written claims
about CI behaviour should cite the rule id that enforces them.

**6.2 — A good exemption pattern applied one gate too far.** The `ci/` exclusion is
correct for token-pattern gates and wrong for secret scanning. The reasoning did not
distinguish the categories, so a sound principle produced a hole.

*Suggestion:* require an exemption to declare the *category* of gate it applies to.

**6.3 — Gate-relative deferral without dates.** Elegant while gates arrive; unbounded when
one slips. Every registry inherits this.

*Suggestion:* an ISO date beside every gate reference, reviewed at each gate.

---

## 7. Summary

| Severity | Count | Blocking G0 |
|---|---|---|
| Critical | 2 | 2 |
| Major | 9 | 1 |
| Minor | 7 | 0 |
| Informational | 1 | 0 |

**Three risks block G0**, all remediable in roughly one session. None requires a design
change.

The architecture is sound and, in several places — verification tiers, trust monotonicity,
the degradation ladder, abolishing shell execution — better than what I typically see at
this gate. **What has not been demonstrated is that the machinery runs.**

*Architecture is not frozen. Re-audit after remediation.*
