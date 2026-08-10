# ADR-0031: A licence that needs review must have somewhere to be reviewed

| | |
|---|---|
| Status | **Proposed** — awaiting Efe's approval (Architecture_Freeze.md §5 step 4) |
| Date | 2026-08-10 |
| Phase | 0 |
| Related | [ADR-0013](ADR-0013-artifact-pinning.md), [ADR-0017](ADR-0017-dual-tts.md), [ADR-0023](ADR-0023-turkish-locale-correctness.md) |

## Context

`ci/policy/policy.yaml` classifies licences three ways: `allow`, `review_required`, and an
`unresolved_registry` for licences genuinely unknown upstream. The `licenses` gate fails
`LIC-002` on anything in `review_required`, with this instruction:

> Confirm the intended use is permitted, or replace the artifact.

**There was no way to record having done the first thing.** Confirming the use is permitted
left the gate failing exactly as before. In practice that leaves three moves, and two of
them destroy information:

| Move | Effect |
|---|---|
| Move the licence to `allow` | Silences the gate for **every** artifact, forever. The constraint disappears |
| Delete the licence identifier from the lockfile | The gate goes quiet because the fact is gone. This is how `verify per MODEL_CARD` strings are born |
| Leave it red | CI is red permanently, and a permanently red build is a build nobody reads |

This stopped being hypothetical on 2026-08-10. `models.piper_tr_dfki` had carried
`license: "verify per MODEL_CARD before release"` since 2026-08-02. Reading the MODEL_CARD
gave **CC-BY-NC-SA-4.0** — the repository-level `rhasspy/piper-voices` licence is MIT, but
the per-voice card governs, and the DFKI-OT training data is NC-SA.

Recording that honestly turned the gate red, and none of the three moves above was
acceptable: `allow`ing NC-SA would have waved through every future NC artifact; deleting the
identifier would have restored exactly the fog that hid it for eight days; and it is the
only Turkish voice the project has, with ADR-0023 making Turkish first-class and G6c's DoD
requiring the Turkish loop to pass.

**The information is not "this licence is fine". It is "this licence permits this use, this
person decided so, and here is when that must be looked at again."** The policy file had no
shape for that, so the gate could ask a question it gave no way to answer — and a check with
no reachable green state teaches people to disable checks.

## Decision

**Add `licenses.review_accepted`: a register of `review_required` licences that have been
reviewed, recording the ruling rather than suppressing the question.**

Each entry declares:

| Field | Why it is mandatory |
|---|---|
| `artifact` | The ruling is per artifact. A licence is not approved; a **use of an artifact** is |
| `license` | Must match the lockfile. If the artifact's licence changes, the ruling no longer applies and the gate goes red again |
| `owner` | Who is answerable. Same contract as `todo.registry` and `unresolved_registry` |
| `scope` | **The operative field.** What the ruling permits — and by omission, what it does not |
| `revisit_at` | The gate at which the ruling must be re-made. A permission with no expiry is a licence change by another name |
| `why` | The reasoning, so the next reader does not have to reconstruct it |

Behaviour:

1. A `review_required` licence with a matching `review_accepted` entry produces a **note**,
   not a failure — and the note **restates the scope on every run**. A bounded permission
   that stops being visible is indistinguishable from no constraint at all.
2. Any mismatch — licence changed, artifact renamed, entry absent — falls back to
   `LIC-002`.
3. **`LIC-006`** polices the register itself: an entry missing any mandatory field fails,
   exactly as `LIC-005` polices `unresolved_registry`.

**This is a register of rulings, not an allowlist.** It cannot make a licence permissive; it
records that a specific use of a specific artifact was judged acceptable, by someone, until
a named gate.

### The first entry

```yaml
- artifact: models.piper_tr_dfki
  license: CC-BY-NC-SA-4.0
  owner: sensory
  scope: "personal use only — NOT distributable, NOT commercial"
  revisit_at: "G6c"
```

Recorded in `artifacts.lock.yaml` with the MODEL_CARD URL and retrieval date, and escalated
in `Architecture_Risk_Register.md` as **R-A15**, raised from Minor to Major. R-A15 had been
scored against `models.wake_bootstrap`, whose NC ambiguity is self-liquidating — ADR-0023
replaces that model at G6a. The Turkish voice has no replacement, no alternative, and a
share-alike obligation on top of the non-commercial one.

**Replacing the voice is a technology decision and is not in this ADR.** It needs its own,
amending ADR-0017.

## Consequences

### Positive

- `LIC-002` becomes answerable. A gate whose only reachable green states are "delete the
  evidence" or "widen the allowlist" trains people to do one of those.
- The constraint travels with the artifact instead of living in someone's memory. Every run
  prints *"personal use only — NOT distributable, NOT commercial"*.
- The ruling expires. `revisit_at: G6c` means the question returns at the gate where the
  Turkish voice is actually built, rather than never.
- The distinction between "we do not know this licence" (`unresolved_registry`) and "we know
  it and ruled on it" (`review_accepted`) is now recorded. It was previously collapsed, and
  the collapse is what let a resolved-but-restrictive licence look like an open question.

### Negative / Costs

- **This is a relaxation of a gate**, which is why it is an ADR at all (Architecture_Freeze
  §4). A register of exceptions can grow into an allowlist with extra steps. The mitigations
  are `LIC-006`, the mandatory `revisit_at`, and the scope line printed on every run — but
  none of them stops someone adding a fourth entry, and a fourth entry deserves a hard look.
- `scope` is prose. No gate can check that the project's actual use matches it; that is a
  human judgement made at `revisit_at`.
- Recording the ruling makes the restriction easier to live with, and easy-to-live-with
  restrictions get lived with. The Turkish voice still blocks distribution, and R-A15 exists
  so that fact has somewhere to be seen other than a YAML comment.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| **Move `CC-BY-NC-SA-4.0` to `allow`** | Approves NC-SA for every future artifact on the strength of one voice model. The next NC artifact would arrive silently |
| **Keep the `verify per MODEL_CARD` deferral** | The state that hid this for eight days. `LIC-003` was asking the right question; nobody was obliged to answer it |
| **Let `licenses` stay red** | The `artifacts` gate was red by design through Phase 0 for a bounded, documented reason with a known closing action. This has no closing action short of replacing the only Turkish voice — an indefinite red build, which is a build nobody reads |
| **Drop the artifact now** | Removes Turkish TTS, which ADR-0023 makes first-class and G6c's DoD requires. A licence mechanism should not force a product decision by default |
| **`license_risk` free text only** | Already present, already read by the gate as a note — and the gate still failed, correctly. Free text is not a ruling: no owner, no scope, no expiry |
| **Per-artifact `# noqa`-style pragma in the lockfile** | Puts the exemption where the artifact is and the accountability nowhere. The registry pattern used by `todo.registry` and `unresolved_registry` already works here |

## Verification

Gate **`licenses`**:

- **`LIC-006`** — every `review_accepted` entry declares `license`, `owner`, `scope` and
  `revisit_at`. Missing any one fails.
- **`LIC-002`** continues to fail for any `review_required` licence **without** a matching
  entry, and for an entry whose `license` no longer matches the lockfile.
- The gate emits the scope on every run for every accepted entry.

`ci/self_test.sh` plants a lockfile licence that is on no list and asserts `LIC-004`, which
exercises the same classification path.

**Standing criterion:** `review_accepted` holds two entries — the Turkish voice and its
config — both `revisit_at: G6c`. A third entry is a signal, not a routine event.

**This ADR is `Proposed`.** Per Architecture_Freeze.md §5 step 4 it is not in force until
Efe accepts it. The mechanism is implemented so the decision can be evaluated against
something real; if it is rejected, `review_accepted` is removed and `licenses` returns to
failing `LIC-002` on the Turkish voice, which is a true statement about an unresolved
question.
