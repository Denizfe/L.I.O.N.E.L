# ADR-0017: Dual TTS — Kokoro for English, Piper for Turkish

| | |
|---|---|
| Status | **Accepted**, corrected 2026-08-02 — see Correction below |
| Date | 2026-08-02 |
| Phase | 6c |
| Related | [ADR-0018](ADR-0018-multilingual-stt.md), [ADR-0023](ADR-0023-turkish-locale-correctness.md) |

## Context

MASTER_PLAN v1.0 chose Kokoro-TTS: 82M parameters, ONNX, near-real-time on CPU, no GPU
required. Correct for English.

Turkish is now an explicit requirement, and **Kokoro has no Turkish voice.** It ships
American and British English natively, adds Japanese and Chinese via `misaki` extras, and
reaches Spanish, French, Hindi, Italian and Brazilian Portuguese through an espeak-ng
fallback. Turkish is explicitly unsupported.

Piper (`rhasspy/piper`) ships three Turkish voices — `tr_TR-fettah-medium`,
`tr_TR-dfki-medium`, `tr_TR-fahrettin-medium` — as ~15M-parameter VITS models in ONNX,
running on CPU with no cloud round-trip. Operationally identical profile to Kokoro.

## Decision

A **`TTSProvider` port** with two adapters, routed by language.

| Language | Engine | Model |
|---|---|---|
| English | **Kokoro** (v1.0 decision preserved) | `kokoro-v1.0.onnx` + `voices-v1.0.bin` |
| Turkish | **Piper** | `tr_TR-dfki-medium` — **the only option**, see Correction |

Same abstraction shape as [ADR-0001](ADR-0001-swappable-brain-provider.md): callers see one
interface, adding a third language is an adapter, and no caller branches on engine name.

Both are ONNX on CPU, so the operational and deployment profile is uniform — one runtime,
one packaging story, one latency class.

## Correction — 2026-08-02

This ADR originally named `tr_TR-fettah-medium` as the primary Turkish voice with
`tr_TR-dfki-medium` as an alternate, and deferred the choice to a G6c listening test.

**That was wrong.** Resolving the artifact checksums revealed that `rhasspy/piper-voices`
— the distributable voice repository — contains **only `tr/tr_TR/dfki`**. The `fettah` and
`fahrettin` voices exist in `rhasspy/piper-checkpoints`, which holds *training
checkpoints*, not packaged voices. The original claim came from search results that
conflated the two repositories.

**Consequences of the correction:**

- `tr_TR-dfki-medium` is the Turkish voice. Not the winner of a comparison — the only entry.
- **The G6c fettah-vs-dfki listening test is removed.** It compared one thing to nothing.
- G6c's Turkish criterion narrows to a straight quality judgement: *is dfki good enough for
  daily use?* Efe answers that. If the answer is no, the fallback is not another Piper voice
  — it is reopening ADR-0017 against XTTS-v2 or converting a checkpoint ourselves, both of
  which are larger decisions than a voice swap.
- This is exactly the kind of error that surfaces when a lockfile is populated from real
  upstream metadata instead of from recollection. Worth noting as an argument for doing
  artifact resolution early rather than at Phase 6.

## Amendment — 2026-08-02: Kokoro source moved to a Hugging Face mirror

The Kokoro model files are now fetched from **`huggingface.co/fastrtc/kokoro-onnx`**, not
from the `thewh1teagle/kokoro-onnx` GitHub release.

**Why.** GitHub release assets uploaded before the API gained a `digest` field return
`digest: null`, so the primary source is unpinnable — there is no upstream-published hash
to verify against. Per the ADR-0013 amendment, prefer sources that publish content digests.
The mirror publishes Git-LFS SHA-256s for both files.

**The identity check that made this safe:** the mirror's byte lengths match the GitHub
assets **exactly** — 325,532,387 for `kokoro-v1.0.onnx` and 28,214,398 for
`voices-v1.0.bin`. Size equality is necessary but not sufficient for byte identity, so the
mirror is pinned as the **source of record** rather than being used to vouch for the GitHub
asset. We fetch what we hashed.

**What was rejected:** `onnx-community/Kokoro-82M-v1.0-ONNX` publishes a clean SHA-256 and
is 155 bytes smaller. Different file. Its hash would have verified cleanly against a model
nobody runs.

**Consequence:** a third-party mirror is a weaker *trust* claim than the primary source even
though the *hash* claim is stronger. Recorded as verification tier B, and the residual risk
is in `Artifact_Verification_Report.md` §6 R4. The GitHub release remains valid as a
fallback whose identity must be confirmed by hash on first download.

## Consequences

### Positive
- v1.0's Kokoro decision is preserved rather than discarded.
- Turkish arrives without a heavyweight multilingual model, GPU requirement, or license
  question.
- Sentence-chunked streaming works identically for both engines.

### Negative / Costs
- Two engines, two model formats, two sets of voice assets in
  `artifacts.lock.toml` ([ADR-0013](ADR-0013-artifact-pinning.md)).
- Voice character differs between languages — L.I.O.N.E.L will not sound like the same
  "person" in English and Turkish. Accepted; matching voices across engines is not
  achievable without cloning.
- Language detection is now on the critical path and can be wrong.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| XTTS-v2 for both | One engine, native Turkish, voice cloning — but much heavier, GPU-preferred, slower first-token, and the Coqui license needs review. Loses the CPU-only property that makes L0 comfortable |
| Piper for both languages | Would work, but discards Kokoro's better English quality for uniformity alone |
| Kokoro + espeak-ng for Turkish | espeak-ng Turkish is intelligible and robotic. Below the bar for a daily assistant |
| Cloud TTS for Turkish | Breaks L0 ([ADR-0007](ADR-0007-degradation-ladder.md)). Non-starter |

## Verification

Gate **G6c**. Both engines synthesize through the port with no caller-visible difference;
language routing selects correctly from detected input language; **Turkish output is
intelligible to a native speaker (Efe)**; first audio within 300 ms for both.
