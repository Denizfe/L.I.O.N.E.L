# Latency Budget

**ADR-0019.** In MASTER_PLAN v1.0 this budget was a table in a document and a stopwatch
reading pasted into a runbook, once. From Phase 5 onward **every stage below emits an
OpenTelemetry histogram and every target is a Prometheus alert.** A budget you cannot
measure is a wish.

## Targets — wake to first spoken word

| Stage | Target | Metric | Owner |
|---|---|---|---|
| Wake detection | < 100 ms | `lionel.wake.detect.duration` | `sensory/wake` |
| VAD endpointing | 400 ms trailing silence | `lionel.vad.endpoint.duration` | `sensory/vad` |
| STT (5 s utterance) | < 800 ms **— see note** | `lionel.stt.transcribe.duration` | `sensory/stt` |
| Memory recall | < 150 ms | `lionel.memory.recall.duration` | `memory/service` |
| Brain first token | < 1200 ms | `lionel.brain.first_token.duration` | `brain/` |
| TTS first audio | < 300 ms | `lionel.tts.first_audio.duration` | `sensory/tts` |
| **Wake → first spoken word** | **< 2500 ms** | `lionel.turn.wake_to_speech.duration` | end to end |
| Barge-in → playback stopped | < 300 ms | `lionel.interrupt.playback_stop.duration` | `core/interrupt_controller` |

## The STT note — read this before G6b

The 800 ms target was set in v1.0 against `ggml-base.en`. **ADR-0018 replaces that model
with multilingual `large-v3-turbo`, which is materially heavier.**

**This target must be re-measured at G6b, not assumed.** If CPU inference breaks it, that
measurement is the trigger to move STT into the Cluster Runtime for GPU inference — one of
the clearest practical justifications for the tiering in ADR-0007.

Discover this at G6b by measurement. Not at G6d by disappointment.

## Per-tier expectations

Budgets are **per tier**. Network hops at L2 are real and must be measured, not estimated.

| Tier | Wake→speech target | Note |
|---|---|---|
| L0 | < 2500 ms | Everything in-process. The reference measurement |
| L1 | < 2700 ms | Loopback IPC overhead |
| L2 | re-measure at G7 | Network + mTLS handshake; connection reuse is load-bearing |
| L3 | re-measure | API round-trip replaces local first-token |

## Alerting

Each stage alerts on **p95 over target across a 5-minute window**. Alerting on p50 hides
the tail the user actually notices; alerting on max fires on every cold start.

G5's exit criterion is that **a deliberate budget violation fires an alert** — that is the
moment the budget stops being aspirational.
