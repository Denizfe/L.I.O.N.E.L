# ADR-0001: Swappable BrainProvider

| | |
|---|---|
| Status | **Accepted** — carried forward from MASTER_PLAN v1.0 |
| Date | 2026-08-01, amended 2026-08-02 |
| Phase | 0 |
| Amended by | [ADR-0009](ADR-0009-extended-brain-provider-contract.md) |
| Related | [ADR-0007](ADR-0007-degradation-ladder.md), [ADR-0026](ADR-0026-side-effect-classification.md) |

## Context

L.I.O.N.E.L needs a reasoning engine. The obvious options pull in opposite directions:

- A hosted API (Claude) has the most reliable tool-calling and the fastest iteration loop,
  but requires network and is not "independent."
- A local model (Ollama, llama.cpp) delivers genuine offline autonomy, but tool-calling
  fidelity varies widely by model and quantization, and debugging a bad tool call is slow.

Choosing either one at the start is an irreversible bet made at the moment of least
information — before a single tool has been written and before we know how hard our
actual workload is.

## Decision

The reasoning engine sits behind a **`BrainProvider` abstraction**. Three implementations
ship: `anthropic`, `ollama`, `llamacpp`. Selection is a config value
(`[brain] provider` in `config/lionel.toml`), not a code change.

**`core/turn_executor` imports `BrainProvider` and nothing else.** No module outside
`brain/providers/` may import a concrete provider or branch on a provider name.

## Consequences

### Positive
- The local-vs-API gap becomes **measurable** rather than assumed. The same golden
  transcript replays against both, and the delta is data.
- No vendor lock-in. A fourth provider is an adapter, not a migration.
- Development speed is decoupled from offline capability — we can build against the API
  and still ship something that runs on a plane.

### Negative / Costs
- The abstraction must be wide enough to cover real differences (native tool blocks vs.
  JSON-schema prompting, streaming shapes, context limits). A too-narrow interface leaks
  provider details into callers. [ADR-0009](ADR-0009-extended-brain-provider-contract.md)
  addresses this.
- Three providers means three code paths to test. [ADR-0027](ADR-0027-testing-strategy.md)
  makes this a replay-test obligation, not a manual one.

### Neutral
- Providers may have genuinely different capabilities. Callers branch on
  *capability flags*, never on provider identity.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Hardcode Claude API | Fastest to build, but "fully local and autonomous" becomes false and untestable |
| Hardcode Ollama | Honest about autonomy, but tool-calling reliability is the project's largest unknown (v1.0 risk R2) and we would discover it late |
| LangChain / LiteLLM as the abstraction | A large dependency whose abstractions we would fight. Our surface is narrow enough to own |

## Verification

Gate **G3**. The same golden transcript produces equivalent tool calls under `anthropic`
and `ollama`; the comparison runs in CI as a regression gate. A static check asserts no
caller branches on provider name.
