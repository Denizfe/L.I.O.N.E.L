# ADR-0018: Multilingual STT mandatory; `.en` models rejected

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 6b |
| Supersedes | MASTER_PLAN v1.0's `ggml-base.en.bin` selection |
| Related | [ADR-0017](ADR-0017-dual-tts.md), [ADR-0007](ADR-0007-degradation-ladder.md) |

## Context

MASTER_PLAN v1.0 selected `ggml-base.en.bin` — fast, ~140 MB, adequate for English commands
— and advised measuring before upgrading. Sound reasoning for an English-only assistant.

With Turkish now required, this is not a tuning choice. **Whisper's `.en` models are
English-only by construction**, not merely English-optimized. They cannot transcribe
Turkish at any quality. A larger `.en` model does not help.

This is the quieter half of the Turkish requirement. The TTS gap is obvious — no Turkish
voice exists. The STT gap looks like a model-size question and is actually a hard
incompatibility that would surface at the final gate, after the entire pipeline had been
built around the wrong model class.

## Decision

**Multilingual Whisper models only. `.en` variants are rejected project-wide.**

Primary: **`ggml-large-v3-turbo`** — multilingual, substantially faster than `large-v3` at
comparable accuracy. Fallback if latency proves unacceptable on CPU: `ggml-medium`
(multilingual), accepting lower Turkish accuracy.

Language handling: auto-detect per utterance, with a configurable hint. The detected
language routes TTS engine selection in
[ADR-0017](ADR-0017-dual-tts.md) and locale normalization in
[ADR-0023](ADR-0023-turkish-locale-correctness.md).

### The latency consequence, made explicit

`large-v3-turbo` is materially heavier than `base.en`. **v1.0's 800 ms STT budget must be
re-measured at G6b, not assumed.** If CPU inference breaks the budget, that is the trigger
to move STT inference into the Cluster Runtime where it can use a GPU — one of the clearest
practical justifications for the tiering in
[ADR-0007](ADR-0007-degradation-ladder.md).

**This must be discovered at G6b, by measurement, not at G6d by disappointment.**

## Consequences

### Positive
- Turkish works at all — a correctness fix, not an optimization.
- One model serves both languages; no dual-STT complexity.
- Language detection comes free and feeds TTS routing.

### Negative / Costs
- Larger download (~1.5 GB vs ~140 MB), pinned in `artifacts.lock.toml`.
- Higher CPU cost and latency; may force GPU or cluster inference.
- L0 on a modest machine becomes materially heavier. This is the real cost of bilingual
  offline operation.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| `base.en` (v1.0) | Structurally incapable of Turkish |
| Two models, switched by language | Requires knowing the language before transcribing — a chicken-and-egg problem, plus double memory |
| `large-v3` (non-turbo) | Slower for accuracy gains that do not justify the latency at conversational length |
| Cloud STT for Turkish | Breaks L0. Non-starter |

## Verification

Gate **G6b**. WER measured on **both** an English and a Turkish fixture set; streaming
partials emitted; **STT latency re-measured and recorded against the budget**, with the
cluster-inference decision triggered here if it fails.
