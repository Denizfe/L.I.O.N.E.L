# ADR-0009: Extended BrainProvider contract

| | |
|---|---|
| Status | **Accepted** |
| Date | 2026-08-02 |
| Phase | 0 |
| Amends | [ADR-0001](ADR-0001-swappable-brain-provider.md) |
| Related | [ADR-0025](ADR-0025-cancellation-backpressure.md), [ADR-0021](ADR-0021-eval-harness-gates.md) |

## Context

[ADR-0001](ADR-0001-swappable-brain-provider.md) established the principle. A
`complete()` / `stream()` pair is too narrow to carry it: providers differ in tool-calling
format, structured-output support, context window, streaming chunk shape, and readiness
semantics. A narrow interface does not remove those differences — it pushes them into
callers as `if provider == "ollama"` branches, and provider independence becomes fictional.

## Decision

The `BrainProvider` interface carries nine capabilities.

| Capability | Purpose |
|---|---|
| `ProviderCapabilities` | Declares `native_tools`, `structured_output`, `streaming`, `vision`, `max_context`, `token_counting`. **Callers branch on capability, never on provider name** |
| `health()` | Liveness **and** readiness as distinct states. Ollama loading a 30 GB model is alive and not ready |
| Metrics emission | Latency, tokens, tool-call success rate, per provider — feeds [ADR-0019](ADR-0019-opentelemetry.md) |
| Structured outputs | Schema-constrained generation, with a documented prompt-based fallback where unsupported |
| Cancellation token | On **every** call. Non-optional. Prerequisite for [ADR-0025](ADR-0025-cancellation-backpressure.md) |
| Tool metadata normalization | See `ToolSpec` below |
| Streaming abstraction | A single `StreamEvent` union — `TextDelta`, `ToolCallDelta`, `Usage`, `Done`, `Error` — so callers never see provider-native chunks |
| **`ToolSpec` IR** | A provider-neutral tool schema, translated at the adapter edge into Anthropic tool blocks / OpenAI functions / Ollama format |
| **Cost & quota accounting** | Token and spend counters per provider with a configurable ceiling |

### Why the last two were added

Neither was in the original proposal, and both are load-bearing.

**`ToolSpec` IR.** Without it, every capability server must author its schema in some
provider's native dialect, and that dialect leaks through the entire system. Provider
independence would hold at the brain boundary and fail everywhere else. The IR is the thing
that makes ADR-0001 true beyond `brain/`.

**Cost accounting.** L3 uses a metered API. An agent loop with a tool-calling bug can burn
a lot of money quickly. A ceiling is not a nice-to-have on a system designed to run
autonomously.

## Consequences

### Positive
- Callers are genuinely provider-agnostic; a provider swap is config.
- Readiness distinct from liveness prevents routing turns to a model that is still loading.
- Cost has a hard stop.

### Negative / Costs
- A wide interface is more work per provider. Mitigated: providers declare capabilities
  they lack rather than faking them, and the contract test suite catches drift.
- The `ToolSpec` translation layer is real code with real edge cases per provider.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Keep the narrow interface, branch in callers | Provider independence in name only — the exact failure this ADR prevents |
| Adopt the OpenAI schema as the IR | Ties a neutral layer to one vendor's shape and inherits its quirks |
| Optional cancellation | Cancellation added later never reaches every call site. Barge-in needs 100% coverage |

## Verification

Gate **G3**. One `ToolSpec` produces a valid native schema for all three providers;
`health()` reports not-ready during model load; a cancellation token aborts a streaming
generation within 200 ms; the cost ceiling halts a runaway; a static check finds no
provider-name branches outside `brain/providers/`.
