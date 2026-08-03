# Turkish TTS — Evaluation Plan and Decision

| | |
|---|---|
| Purpose | Choose the Turkish voice for L.I.O.N.E.L; define how to prove the choice |
| Raised by | `Architecture_Risk_Register.md` **R-A12** — "one candidate and no fallback" |
| Governs | ADR-0017 (dual TTS), ADR-0023 (Turkish locale) |
| Constraints | ADR-0007 (L0 offline), `docs/LATENCY_BUDGET.md`, ADR-0002 (Windows host) |
| Status | **Plan. No implementation.** |
| Recommended gate | **Pull the listening test forward to now — do not wait for G6c** |

---

## 1. Summary

**Three of the four candidates are eliminated by hard constraints before quality is ever
measured.** That is the finding, and it changes the shape of the decision.

| Candidate | Outcome | Eliminated by |
|---|---|---|
| **Kokoro** | **Not applicable** | No Turkish voice exists. Not a quality judgement — a capability gap |
| **XTTS-v2** | **Rejected** | CPU real-time factor **1.41** (slower than real time) **and** a non-commercial licence whose licensor no longer exists |
| **Piper `tr_TR-dfki-medium`** | **Provisionally selected** | Only candidate satisfying every hard constraint |
| **Custom Piper voice** | **The real fallback** | Requires training. Not available today; **available before it is needed** |

So the evaluation reduces to one binary question that only Efe can answer:

> **Is `tr_TR-dfki-medium` good enough to talk to every day?**

Section 6 is the plan for answering it. Section 7 is what happens if the answer is no.

**The most useful correction to R-A12:** the register recorded "one candidate and no
fallback." That was half right. XTTS-v2 is *not* a viable fallback — it fails on latency
and licensing independently. But a **custom Piper voice is**, and it is better than XTTS-v2
on seven of eight criteria. ADR-0023's custom model was filed as polish. **It is actually
the risk mitigation.**

---

## 2. Hard constraints

A candidate failing any of these is out regardless of how it sounds.

| # | Constraint | Source | Threshold |
|---|---|---|---|
| **H1** | Runs fully offline | ADR-0007 (L0 is the autonomy guarantee) | No network, ever |
| **H2** | Runs on CPU at real time | ADR-0007 — L0 has no GPU guarantee | **RTF < 1.0**, ideally < 0.5 |
| **H3** | First audio ≤ 300 ms | `LATENCY_BUDGET.md` | p95 over a 5-minute window |
| **H4** | Licence permits the intended use | ADR-0013 | Personal now; **must not foreclose distribution** |
| **H5** | Runs on Windows + Git Bash | ADR-0002, ADR-0014 | Native, no WSL requirement |
| **H6** | Deployable in a container | ADR-0020 | Linux amd64 **and** arm64 |
| **H7** | Streams sentence-chunked | ADR-0017 | Required for the 300 ms budget |

**H2 and H4 do the eliminating.** Everything else is satisfiable by all candidates.

---

## 3. Candidate assessment

### 3.1 Kokoro — not applicable

| Criterion | Assessment |
|---|---|
| Turkish support | **None.** en-us, en-gb natively; ja/zh via `misaki` extras; es/fr/hi/it/pt-br via espeak-ng fallback. Turkish explicitly unsupported |
| Everything else | Excellent — 82M params, ONNX, CPU real-time, Apache-2.0 |

Kokoro remains the **English** engine under ADR-0017 and is not a Turkish candidate. Listed
here only because the question was asked; there is nothing to evaluate.

> A note worth recording: Turkish could in principle be reached through Kokoro's espeak-ng
> fallback path, as Spanish and Italian are. Nobody has trained those voices, and
> espeak-ng Turkish alone is intelligible and robotic — below the bar for a daily
> assistant. Not a path.

### 3.2 XTTS-v2 — rejected on two independent grounds

Either would be sufficient to reject it. Both apply.

**Ground 1 — it cannot run at real time on CPU.**

| Measure | Value | Against H2/H3 |
|---|---|---|
| **CPU real-time factor** | **1.41** | **FAIL** — a 5 s utterance takes ~7 s to synthesise |
| GPU RTF (deepspeed) | ~0.25 | Passes, but requires a GPU |
| GPU first chunk | 212–320 ms | Marginal against the 300 ms budget |
| VRAM | **4–6 GB** | Competes with the local LLM for the same GPU at L0 |

RTF > 1.0 means the model is a batch tool, not a streaming one. At L0 — the tier that
carries the project's autonomy guarantee and assumes no GPU — XTTS-v2 does not merely miss
the latency budget, it cannot produce audio as fast as the audio plays.

Even at L1+/GPU it would compete for VRAM with the Ollama model that ADR-0001 puts on the
same machine. Two 4–6 GB residents on one consumer GPU is a resource conflict, not a
deployment.

**Ground 2 — the licence is a permanent dead end.**

- XTTS-v2 weights ship under the **Coqui Public Model License (CPML) — non-commercial.**
  The `coqui-ai/TTS` *code* is MPL-2.0; the *weights* are not.
- **Coqui Inc. shut down in January 2024.** There is no entity left to sell a commercial
  licence.

That second point is what makes this different from every other licensing question in this
project. The openWakeWord non-commercial ambiguity (`Artifact_Verification_Report.md` §4)
is *resolvable* — someone could be asked, or the artifact replaced. **This one is not.** The
counterparty does not exist. A licence with no licensor cannot be negotiated, clarified, or
purchased, ever.

Adopting XTTS-v2 would mean permanently foreclosing distribution of L.I.O.N.E.L in exchange
for a voice that cannot meet the latency budget on the target hardware.

**Verdict: rejected.** Not "heavy" — structurally unsuitable and permanently
licence-blocked.

### 3.3 Piper `tr_TR-dfki-medium` — provisionally selected

| Criterion | Assessment | H |
|---|---|---|
| **Offline** | Fully. ONNX + espeak-ng phonemiser, no network | ✅ H1 |
| **CPU / latency** | VITS ~15M params. Designed for CPU-only and edge hardware — runs on a Raspberry Pi 4 without modification. RTF comfortably < 1.0 on any modern x86 | ✅ H2 |
| **First audio** | Sentence-chunked streaming; small model, fast first chunk | ⚠️ H3 — *must be measured*, not assumed |
| **Licence** | **MIT** (Piper). Voice licence per `MODEL_CARD` — **still unresolved**, registered to `sensory` for G6c | ⚠️ H4 |
| **Windows** | ONNX Runtime native; no WSL requirement | ✅ H5 |
| **Docker** | Small image; multi-arch straightforward | ✅ H6 |
| **Streaming** | Supported | ✅ H7 |
| **Cloning** | **None.** Fixed voice | — |
| **Quality** | **Unknown. This is the open question** | ? |

Two caveats recorded honestly:

1. **It is the only Turkish voice in `rhasspy/piper-voices`.** `fettah` and `fahrettin`
   exist only in `rhasspy/piper-checkpoints` — training checkpoints, not distributable
   voices (ADR-0017 correction, 2026-08-02).
2. **The voice licence is genuinely unresolved.** `artifacts.lock.yaml` records
   *"verify per MODEL_CARD before release"*. That must close before distribution, and it
   is registered with an owner and a gate.

### 3.4 Custom Piper voice — the real fallback

Filed under ADR-0023 as the "Hey Lionel" wake-word companion. On examination it is the
**strongest long-term option** and the correct answer if dfki disappoints.

| Criterion | Assessment |
|---|---|
| **Runtime** | **Identical to dfki.** Same ONNX, same Piper inference, same container, same latency profile. **Zero architectural change** |
| **Licence** | **Project-owned.** Removes the last third-party licence risk from the sensory layer |
| **Quality ceiling** | Bounded by dataset quality, not by an upstream decision |
| **Cloning** | Effectively yes — a voice trained on a chosen speaker |
| **Cost** | Fine-tune from an existing checkpoint (`lessac medium` is the common base). ~1 hour of recordings is workable for fine-tuning; more is better. Dataset must be **22,050 Hz mono** |
| **Effort** | Fine-tuning is hours-to-days on a consumer GPU. Training from scratch is ~10 days on a 3090 and unnecessary |
| **Risk** | Requires a Turkish dataset and a GPU. Neither is on the critical path today |

**Why this reframes R-A12:** the register said there was no fallback. There is one, it
shares the entire runtime with the current choice, and it is *better licensed* than
anything third-party. It simply has to be built.

---

## 4. Comparison matrix

Scored against the constraints, not in the abstract. **✅ pass · ⚠️ unproven · ❌ fail**

| Criterion | Kokoro | XTTS-v2 | **Piper dfki** | Custom Piper |
|---|---|---|---|---|
| **Turkish capability** | ❌ none | ✅ native | ✅ | ✅ |
| **Latency — first audio** | n/a | ❌ CPU / ⚠️ GPU 212–320 ms | ⚠️ measure | ⚠️ = dfki |
| **CPU usage / RTF** | n/a | ❌ **1.41** | ✅ « 1.0 | ✅ « 1.0 |
| **Offline (L0)** | n/a | ⚠️ needs GPU | ✅ | ✅ |
| **Licensing** | ✅ Apache-2.0 | ❌ **CPML, no licensor** | ⚠️ MIT + voice TBC | ✅ **project-owned** |
| **Windows deployment** | ✅ | ⚠️ torch + CUDA | ✅ ONNX native | ✅ |
| **Docker deployment** | ✅ | ⚠️ large, GPU runtime | ✅ small, multi-arch | ✅ |
| **Voice cloning** | ❌ | ✅ **best in class** | ❌ | ✅ effectively |
| **Quality (Turkish)** | n/a | likely highest | **unknown** | dataset-bounded |

**XTTS-v2 wins exactly one row** — cloning — and fails two hard constraints to get it.

---

## 5. Turkish-specific test corpus

Generic TTS benchmarks do not exercise what breaks in Turkish. The corpus below targets
the failure modes that matter, and doubles as the ADR-0023 locale-correctness fixture set.

### 5.1 Categories

| # | Category | Why it breaks | Examples |
|---|---|---|---|
| **T1** | **Dotted/dotless i** | ADR-0023's core hazard. Four glyphs: `i I ı İ` | `İstanbul`, `ılık`, `IŞIK açık`, `iyi misin` |
| **T2** | **Circumflex vowels** | Changes meaning and length | `kâğıt`, `hâlâ`, `âlem` vs `alem` |
| **T3** | **Numbers** | Turkish uses **comma** as decimal separator, **period** as thousands | `1.234,56 TL`, `%15`, `3'üncü`, `2/3` |
| **T4** | **Dates & times** | Ordinal and case suffixes attach to digits | `2 Ağustos 2026`, `saat 14:30`, `1990'da` |
| **T5** | **Vowel harmony in suffixes** | Suffix vowel depends on the stem | `evde` / `okulda` / `gözde` / `yurtta` |
| **T6** | **Question particle `mI`** | Separate word, but carries the intonation contour | `geliyor mu?` `gördün mü?` `iyi misin?` |
| **T7** | **Agglutination** | Very long single words; prosody must not collapse | `çekoslovakyalılaştıramadıklarımızdanmışsınızcasına` |
| **T8** | **Abbreviations** | Expanded or spelled out | `TBMM`, `vb.`, `Dr.`, `TL`, `km/sa` |
| **T9** | **Loanwords / code-switching** | Efe will mix English technical terms | `commit yaptım`, `Docker container`, `pull request` |
| **T10** | **Assistant register** | The actual workload | `C sürücünde 187 GB boş yer var.` |

### 5.2 Composition

- **60 utterances.** 5 per category T1–T9, 15 for T10 (the real workload dominates).
- Length distribution: 20 short (< 5 words), 25 medium (5–15), 15 long (> 15).
- Stored as `evals/tts/tr/corpus.yaml` — text plus expected normalisation.
- **T9 code-switching is the one most likely to be skipped and most likely to matter.**
  Efe will say `commit` and `container` inside Turkish sentences constantly.

---

## 6. Evaluation plan

### 6.1 What is measured, and by whom

| Dimension | Method | Judge | Threshold |
|---|---|---|---|
| **First-audio latency** | p95 over 60 utterances, cold and warm | machine | **≤ 300 ms** |
| **RTF** | synthesis time ÷ audio duration | machine | **< 0.5** |
| **CPU usage** | peak and mean core-seconds per utterance | machine | ≤ 1 core sustained |
| **Memory** | RSS during synthesis | machine | ≤ 500 MB |
| **Intelligibility** | STT round-trip: synthesise → `large-v3-turbo` → WER vs source | machine | **WER ≤ 10%** |
| **Naturalness** | blind 1–5 MOS on 20 sampled utterances | **Efe** | **mean ≥ 3.5** |
| **Correctness** | per-category pass/fail on T1–T9 | **Efe** | **T1 and T3 must be 100%** |
| **Daily-use verdict** | "would I talk to this every day?" | **Efe** | **binary** |

**The machine measurements are necessary and not sufficient.** A voice can hit every
latency target, score WER 4%, and still be unpleasant enough that you stop using the
assistant. That is why the last row exists and why it is binary.

### 6.2 Why T1 and T3 are must-pass

They are **correctness**, not taste. If `İstanbul` is read with a dotless ı, or `1.234,56`
is read as one thousand two hundred point thirty-four, the assistant is *wrong*, not merely
inelegant. Everything else can be traded against convenience; these cannot.

### 6.3 Protocol

1. **Blind.** Efe scores audio files without knowing engine or voice. Trivial now with one
   candidate; essential later when comparing dfki against a custom voice.
2. **On the target machine.** The Windows host, not a container, not a cloud runner.
   ADR-0002 makes the Windows box the deployment target.
3. **Both a cold and a warm run.** Model-load time is a real first-turn cost.
4. **Record raw audio.** Store under `evals/tts/tr/samples/` so a future candidate is
   compared against the same corpus rather than a memory of it.
5. **Efe scores in one sitting.** Naturalness judgements drift across sessions.

### 6.4 Timing — bring it forward

**Recommendation: run the Stage 0 subset now, not at G6c.**

R-A12 identified the problem: at G6c the pipeline is already built around the chosen
engine. A "no" answer there is expensive. A "no" answer now is a Phase 0 decision costing
nothing.

| Stage | When | Scope | Cost | Decides |
|---|---|---|---|---|
| **Stage 0 — smoke** | **Now** | Published `tr_TR-dfki-medium` samples from Hugging Face; 5 min of listening | ~10 min | Is dfki *plausibly* good enough? |
| **Stage 1 — corpus** | G6c | Full 60-utterance corpus, all metrics | ~2 h | Is dfki *actually* good enough? |
| **Stage 2 — comparative** | Only if Stage 1 fails, or when a custom voice exists | dfki vs custom, blind A/B | ~3 h | Which voice ships? |

**Stage 0 requires no implementation.** The `rhasspy/piper-voices` repository publishes
sample audio for `tr/tr_TR/dfki/medium` alongside the model already pinned in
`artifacts.lock.yaml`. Listening to those samples is a browser tab and ten minutes, and it
converts the project's largest unmitigated sensory risk into a known quantity.

---

## 7. Decision and fallback ladder

### 7.1 Decision

**Provisionally select Piper `tr_TR-dfki-medium`**, confirming ADR-0017 as amended.
Provisional until Stage 1 passes at G6c.

**Formally reject XTTS-v2** on CPU real-time factor and on a non-commercial licence with no
surviving licensor. Recording the rejection matters: XTTS-v2 is the obvious suggestion
whenever Turkish TTS comes up, and without a written rejection this analysis gets
re-litigated every few months.

### 7.2 Fallback ladder

Ordered by cost. Each rung is a complete answer, not a stopgap.

| Rung | Option | Trigger | Architectural cost |
|---|---|---|---|
| **1** | `tr_TR-dfki-medium` | Default | none — already pinned |
| **2** | **Fine-tuned Piper voice** | Stage 1 fails, or quality merely tolerable | **Zero.** Same ONNX, same runtime, same container, same latency. Only the model file changes |
| **3** | Piper trained from a Turkish corpus | Fine-tune insufficient | Low. Same runtime; needs a dataset and GPU time |
| **4** | Re-open ADR-0017 for a new engine | All Piper paths fail | High. New runtime, new licence review, new deployment |
| ~~5~~ | ~~XTTS-v2~~ | — | **Rejected.** Fails H2 and H4 |
| ~~6~~ | ~~Cloud TTS~~ | — | **Breaks L0.** Non-starter under ADR-0007 |

**Rung 2 is the important one.** It shares the entire runtime with rung 1, so switching is a
lockfile change and an eval run — the same property ADR-0021 gives model swaps generally.
The fallback is cheap *because* the ADR-0017 `TTSProvider` port already exists.

### 7.3 What this changes about ADR-0023

ADR-0023's custom model is currently framed as wake-word work with a licence benefit. This
analysis promotes it:

> **The custom Piper voice is the primary mitigation for R-A12**, not a later refinement.
> It is the only rung on the ladder that is both fully licensed to the project and
> architecturally free.

Recommend amending ADR-0023 to record that its scope covers **both** the wake word and the
Turkish voice, and that the Turkish voice is a *risk control*, not polish.

---

## 8. Open items

| # | Item | Owner | By |
|---|---|---|---|
| 1 | **Stage 0 listening test** on published dfki samples | Efe | **now** |
| 2 | Resolve the dfki voice licence from `MODEL_CARD` | sensory | G6c *(already registered)* |
| 3 | Build `evals/tts/tr/corpus.yaml` — 60 utterances, T1–T10 | sensory | G6c |
| 4 | Decide the custom-voice dataset source: Efe's own recordings vs a public Turkish corpus | Efe | G6a |
| 5 | Amend ADR-0017 to record the XTTS-v2 rejection and this ladder | architecture | with this doc |
| 6 | Amend ADR-0023 to cover the Turkish voice as risk mitigation | architecture | with this doc |

Items 5 and 6 are **proposals requiring approval**. No ADR was modified by this document.

---

## 9. What this document does not settle

- **No Turkish MOS comparison exists** in published benchmarks for these engines. Every
  quality number here would be borrowed from English evaluations and would not transfer.
  That absence is precisely why §6 puts a human in the loop rather than citing a score.
- **dfki's actual quality is unknown to me.** I have not heard it. The plan is built so
  that its quality is *measured* rather than assumed in either direction.
- **Fine-tuning effort is estimated from general Piper guidance**, not from a Turkish
  fine-tune. Treat the numbers as an order of magnitude.

---

*No implementation. No ADR modified. Sources: Piper voice inventory and licence; XTTS-v2
CPML status and post-shutdown licensing; XTTS-v2 CPU RTF benchmarks; Kokoro language
support; Piper fine-tuning guidance.*
