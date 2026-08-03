# ADR-0023: Turkish locale correctness — the dotted/dotless `i`

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 6c |
| Related | [ADR-0017](ADR-0017-dual-tts.md), [ADR-0018](ADR-0018-multilingual-stt.md) |

## Context

Turkish has **four** `i` characters: `i` `I` `ı` `İ`. Case mapping is not what most code
assumes:

| | Invariant | Turkish |
|---|---|---|
| `I` lowercased | `i` | **`ı`** (dotless) |
| `i` uppercased | `I` | **`İ`** (dotted capital) |

Any code that case-folds for comparison — a wake word, a tool name, a config key, a language
code, a user utterance — will mismatch the moment the process locale is Turkish or the input
contains Turkish characters.

This is a well-known and genuinely nasty bug class. It is **invisible in English testing**
and **guaranteed in Turkish production**, and it fails silently: no exception, just a
comparison that returns false when it should return true. `"TITLE".lower() == "title"` is
`False` under a Turkish locale.

Since L.I.O.N.E.L will run bilingually on a machine that may well have a Turkish system
locale, this is not hypothetical.

## Decision

**Casing is always explicit about which behavior it wants. Never implicit.**

| Purpose | Rule |
|---|---|
| Internal identifiers — tool names, config keys, language codes, wake words, enum values | **Invariant casing, explicitly requested.** Never locale-dependent |
| User-facing display text | **Locale-aware casing**, deliberately chosen |

Supporting rules:

- Internal identifiers are **defined lowercase-invariant at the source**, so folding is
  rarely needed at all.
- A lint rule flags bare `.lower()` / `.upper()` on identifier-typed values.
- **Turkish text normalization is a distinct concern** and lives in `sensory/locale/`:
  number-to-words (structurally different from English), dates, abbreviations, currency —
  all required before TTS synthesis.
- A dedicated test suite exercises `i I ı İ` across every comparison path.
- CI runs at least one job under a Turkish locale so the failure mode is reachable in
  automation rather than only on Efe's machine.

## Consequences

### Positive
- A silent, hard-to-diagnose bug class is prevented rather than debugged.
- Text normalization has an explicit home instead of being scattered inline.
- Explicit casing is self-documenting at the call site.

### Negative / Costs
- Slightly more verbose than bare `.lower()`.
- One more CI job for the Turkish-locale run.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Ignore it; force an English process locale | Fragile — one library or subprocess sets it back. Also wrong for user-facing text |
| Normalize everything to ASCII | Destroys Turkish text. Wrong for a bilingual assistant |
| Handle it when it breaks | It breaks silently. There is no moment when it announces itself |
| Locale-aware casing everywhere | Correct for display, wrong for identifiers — the same bug from the other direction |

## Verification

Gate **G6c**. The `i I ı İ` test suite passes across all comparison paths; a CI job runs
under a Turkish locale; Turkish number and date normalization produce correct spoken forms,
confirmed by Efe.
