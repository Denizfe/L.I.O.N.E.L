# ADR-0027: Five-layer testing strategy

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 |
| Related | [ADR-0007](ADR-0007-degradation-ladder.md), [ADR-0021](ADR-0021-eval-harness-gates.md) |

## Context

MASTER_PLAN v1.0 specified four files: `test_phase1_env.py` through `test_phase4_sensory.py`.
Unit tests only. Three gaps, in increasing severity:

1. **No contract tests.** Nothing verifies an MCP server matches its declared schema, or a
   provider matches the ABC. Drift is found at integration time.
2. **No chaos tests.** Nothing verifies behavior when Qdrant dies mid-turn or the brain
   times out.
3. **No hardware-free sensory testing.** Every sensory test needs a live microphone, which
   means **Phase 6 — the riskiest phase — has zero CI coverage.**

The third also makes the L0 gate in [ADR-0007](ADR-0007-degradation-ladder.md) impossible
to automate, and a gate that cannot run in CI is not a gate.

## Decision

Five layers, each with a distinct job.

| Layer | Scope | Runs |
|---|---|---|
| **Unit** | Pure logic, no I/O | Every commit |
| **Contract** | Every MCP server against its declared schema; every `BrainProvider` against the ABC; every tool against its metadata requirements | Every commit |
| **Replay** | Golden transcripts replayed across providers | Every PR touching brain/prompts |
| **Chaos** | Kill Qdrant mid-turn, time out the brain, remove the audio device, saturate the data plane | Nightly + pre-gate |
| **Sensory harness** | Pre-recorded WAV fixtures injected at the audio-buffer boundary | Every commit |

### The sensory harness is the important one

Fixtures are injected at the ring-buffer boundary, **below** wake detection. Everything
above — wake word, VAD, STT, the full pipeline, barge-in — becomes testable with no
microphone, no speaker, and no human.

This is what makes the L0 conformance gate automatable, and therefore what makes
[ADR-0007](ADR-0007-degradation-ladder.md)'s invariant real rather than aspirational.

### Chaos assertions are about degradation, not survival

Each chaos test asserts the system **degrades as declared** — memory down means proceed
without recall and say so; brain down means fall back to the next provider; TTS down means
surface text. **The system must always produce a response**, even if that response is an
honest statement that a subsystem is unavailable.

## Consequences

### Positive
- Phase 6 gains CI coverage, closing the largest hole in v1.0.
- Contract tests catch interface drift at the boundary rather than at integration.
- Declared degradation behavior is verified rather than documented and hoped for.

### Negative / Costs
- Five suites to build and maintain; fixture audio must be recorded and version-controlled
  (binary, but small).
- Chaos tests are slower and somewhat flaky by nature — hence nightly rather than per-commit.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Unit tests only (v1.0) | Leaves the riskiest subsystem untested and the L0 gate un-automatable |
| Manual sensory testing | Not repeatable, not in CI, and skipped under time pressure |
| Integration tests only | Slow, and failures do not localize |
| Mock the audio device driver | More brittle than fixture injection and tests the mock, not the pipeline |

## Verification

Gate **G0**: CI runs and reports all five layers, even where suites are empty.
Gate **G6a**: the sensory harness exercises the full pipeline with **no microphone attached**.
