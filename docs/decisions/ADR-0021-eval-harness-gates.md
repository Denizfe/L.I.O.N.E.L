# ADR-0021: Evaluation harness gates model and prompt changes

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 8 |
| Related | [ADR-0001](ADR-0001-swappable-brain-provider.md), [ADR-0013](ADR-0013-artifact-pinning.md), [ADR-0027](ADR-0027-testing-strategy.md) |

## Context

Model swaps, prompt edits, and provider changes alter behavior in ways ordinary tests do not
catch. A prompt tweak that improves one case can silently break tool selection in five
others, and nothing goes red.

[ADR-0001](ADR-0001-swappable-brain-provider.md) requires comparing local and API providers.
Done manually, that comparison happens once, gets written into an ADR, and is never repeated
— so it decays into folklore about a model version nobody is running anymore.

## Decision

An evaluation harness in `evals/`, wired as a **CI gate on every PR touching a model,
prompt, or provider.**

| Suite | Measures |
|---|---|
| **Golden set** | Utterance → expected tool-call set. Correct tool, correct arguments |
| **STT WER** | Word error rate on English **and** Turkish fixtures |
| **Wake FAR/FRR** | False accepts against a negative corpus; false rejects against positives |
| **TTS intelligibility** | Spot-check corpus, both languages |
| **Provider leaderboard** | provider × model × prompt-version, persisted over time |

### Operating rules

- **A regression blocks merge.** Not a warning.
- Thresholds are versioned alongside the suite; raising one is a reviewed change with a
  reason, not a quiet edit.
- The model registry keys to `artifacts.lock.toml`
  ([ADR-0013](ADR-0013-artifact-pinning.md)), so every eval result names the exact artifact
  that produced it.
- **Swapping the STT model becomes a lockfile change plus an eval run — not a code change.**

### What this converts

ADR-0001's Anthropic-vs-Ollama comparison stops being a one-time measurement and becomes a
**standing regression gate**. "Is the local model good enough yet?" becomes a query against
the leaderboard rather than an argument.

## Consequences

### Positive
- Behavioral regressions are caught before merge.
- The L0 capability ceiling is tracked continuously as local models improve.
- Model upgrades become routine and low-risk.

### Negative / Costs
- The golden set must be built and maintained; a stale eval set is worse than none because
  it grants false confidence.
- Eval runs cost time in CI and tokens against the API provider.
- Non-determinism requires tolerance bands rather than exact matching.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Manual spot-checking (v1.0) | Not reproducible, not comparable, silently skipped under time pressure |
| Unit tests over prompts | Prompts are not deterministic functions; assertions on exact strings are brittle |
| Public benchmarks | Measure general capability, not whether *our* tools get called correctly |
| Eval as advisory, not blocking | An advisory gate is ignored by the third sprint |

## Verification

Gate **G8**. The suite runs in CI on every relevant PR; **a deliberate prompt regression is
caught and blocks merge**; provider comparison reproducible from one command; WER and
FAR/FRR trend in Grafana.
