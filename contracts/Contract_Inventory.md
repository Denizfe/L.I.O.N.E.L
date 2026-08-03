# Contract Inventory

**L.I.O.N.E.L contract set v1.1.0** — Phase 0 / M2. Generated 2026-08-02.

The register of every contract: version, producer, consumer, owner, stability. Authoritative definitions live in the schema files; this is the index for finding them and for judging the blast radius of a proposed change.

> **No implementation exists.** Contracts are defined before the code they constrain. That ordering is what made the v1.0 → v2.0 migration cost zero lines of code, and it is what will make the next one cheap.

## At a glance

- **27 JSON Schemas** + **3 protobuf files** across 5 planes
- **Planes:** control 10 · data 2 · internal 15
- **Owners:** brain 5 · capabilities 4 · core-orchestration 6 · memory 3 · observability 5 · platform 2 · sensory 2
- **Stability:** provisional 2 · stable 25
- **45 examples**, every one validated against its own schema in CI

## Register

### Plane: `internal`

| Contract | v | Owner | Producer | Consumers | Stability | ADR |
|---|---|---|---|---|---|---|
| [Event](core/v1/event.schema.json) | 1.0.0 | `observability` | `any component` | `otel_collector`, `audit_log`, `session_coordinator` +1 | stable | ADR-0019, ADR-0006 |
| [MetricRecord](core/v1/metrics.schema.json) | 1.0.0 | `observability` | `all components via platform/telemetry` | `otel_collector`, `prometheus`, `grafana` +1 | stable | ADR-0019, ADR-0007 |
| [AgentDecision](events/v1/agent-decision.schema.json) | 1.0.0 | `core-orchestration` | `turn_executor`, `tool_router` +2 | `audit_log`, `otel_collector`, `eval_harness` | stable | ADR-0008, ADR-0012 |
| [AuditRecord](events/v1/audit-record.schema.json) | 1.0.0 | `capabilities` | `policy_engine` | `audit_log`, `security_review`, `otel_collector` | stable | ADR-0012, ADR-0026 |
| [CancellationToken and CancellationEvent](events/v1/cancellation.schema.json) | 1.0.0 | `core-orchestration` | `interrupt_controller` | `turn_executor`, `brain_gateway`, `tts_service` +2 | stable | ADR-0025, ADR-0008 |
| [MemoryRecord](events/v1/memory-record.schema.json) | 1.0.0 | `memory` | `memory_service` | `context_assembler`, `turn_executor`, `memory_service` | stable | ADR-0010, ADR-0012 |
| [ProviderCapabilities and HealthStatus](events/v1/provider-capabilities.schema.json) | 1.0.0 | `brain` | `anthropic_provider`, `ollama_provider` +1 | `brain_gateway`, `turn_executor`, `provider_router` +1 | stable | ADR-0009, ADR-0001 |
| [ProviderRequest](events/v1/provider-request.schema.json) | 1.0.0 | `brain` | `turn_executor`, `context_assembler` | `brain_gateway`, `anthropic_provider`, `ollama_provider` +1 | stable | ADR-0001, ADR-0009 |
| [ProviderResponse](events/v1/provider-response.schema.json) | 1.0.0 | `brain` | `brain_gateway` | `turn_executor`, `session_coordinator`, `eval_harness` +2 | stable | ADR-0009, ADR-0001 |
| [StreamEvent](events/v1/stream-event.schema.json) | 1.0.0 | `brain` | `anthropic_provider`, `ollama_provider` +1 | `turn_executor`, `tts_service`, `otel_collector` | stable | ADR-0009, ADR-0001 |
| [Telemetry semantic conventions](events/v1/telemetry-attributes.schema.json) | 1.0.0 | `observability` | `all components via platform/telemetry` | `otel_collector`, `prometheus`, `grafana` | stable | ADR-0019, ADR-0007 |
| [ToolSpec](events/v1/tool-spec.schema.json) | 1.0.0 | `brain` | `capability servers` | `brain_gateway`, `tool_router`, `anthropic_provider` +2 | stable | ADR-0009, ADR-0026 |
| [TrustContext](events/v1/trust-context.schema.json) | 1.0.0 | `core-orchestration` | `context_assembler`, `session_coordinator` | `policy_engine`, `tool_router`, `turn_executor` +1 | stable | ADR-0012, ADR-0011 |
| [TurnEvent](events/v1/turn-event.schema.json) | 1.0.0 | `observability` | `session_coordinator`, `turn_executor` +5 | `otel_collector`, `grafana`, `audit_log` | stable | ADR-0006, ADR-0008 |
| [WorkflowEvent](events/v1/workflow-event.schema.json) | 1.0.0 | `core-orchestration` | `session_coordinator`, `memory_service` | `audit_log`, `otel_collector`, `session_coordinator` | provisional | ADR-0008, ADR-0010 |

### Plane: `control`

| Contract | v | Owner | Producer | Consumers | Stability | ADR |
|---|---|---|---|---|---|---|
| [HealthStatus](core/v1/health-status.schema.json) | 1.0.0 | `observability` | `memory_service`, `brain_gateway` +3 | `session_coordinator`, `tool_router`, `kubernetes_probes` +1 | stable | ADR-0009, ADR-0005 |
| [MemoryQuery and MemoryQueryResult](events/v1/memory-query.schema.json) | 1.0.0 | `memory` | `context_assembler`, `tool_router` | `memory_service` | stable | ADR-0010, ADR-0012 |
| [CapabilitiesRegistry](mcp/v1/capabilities-registry.schema.json) | 1.0.0 | `platform` | `operator (config file)` | `tool_router`, `process_supervisor`, `config loader` | stable | ADR-0003, ADR-0015 |
| [CapabilityManifest](mcp/v1/capability-manifest.schema.json) | 1.0.0 | `capabilities` | `capability servers` | `tool_router`, `capabilities registry loader` | stable | ADR-0003, ADR-0011 |
| [ErrorEnvelope](mcp/v1/error-envelope.schema.json) | 1.0.0 | `platform` | `all components` | `turn_executor`, `tool_router`, `session_coordinator` +1 | stable | ADR-0003, ADR-0025 |
| [MCPTool](mcp/v1/mcp-tool.schema.json) | 1.0.0 | `capabilities` | `capability servers` | `tool_router`, `brain_gateway (via ToolSpec translation)` | stable | ADR-0003, ADR-0009 |
| [Memory Service MCP surface](mcp/v1/memory-service.schema.json) | 1.0.0 | `memory` | `memory_service` | `tool_router`, `context_assembler` | stable | ADR-0010, ADR-0012 |
| [PolicyRuleset](mcp/v1/policy-ruleset.schema.json) | 1.0.0 | `capabilities` | `operator (config file)` | `policy_engine` | stable | ADR-0012, ADR-0026 |
| [ToolCall](mcp/v1/tool-call.schema.json) | 1.0.0 | `core-orchestration` | `turn_executor` | `tool_router`, `policy_engine`, `capability servers` +1 | stable | ADR-0012, ADR-0026 |
| [ToolResult](mcp/v1/tool-result.schema.json) | 1.0.0 | `core-orchestration` | `tool_router` | `turn_executor`, `context_assembler`, `audit_log` +1 | stable | ADR-0003, ADR-0012 |

### Plane: `data`

| Contract | v | Owner | Producer | Consumers | Stability | ADR |
|---|---|---|---|---|---|---|
| [AudioFrame](media/v1/audio-frame.schema.json) | 1.0.0 | `sensory` | `audio_io`, `tts_service` | `wake`, `vad`, `stt_service` +2 | stable | ADR-0006, ADR-0028 |
| [VisionFrame](media/v1/vision-frame.schema.json) | 1.0.0 | `sensory` | `(none yet — camera_io at Phase 10)` | `(none yet — vision_service, brain_gateway when vision capability is enabled)` | provisional | ADR-0006, ADR-0028 |

### Plane: `data` — wire format

| File | Version | Owner | Contents |
|---|---|---|---|
| [common.proto](grpc/v1/common.proto) | 1.0.0 | `sensory` | TurnContext, AudioFormat, AudioFrame, CancelRequest, StreamError, HealthCore |
| [stt.proto](grpc/v1/stt.proto) | 1.0.0 | `sensory` | SpeechToText — bidi streaming, multilingual enforced (ADR-0018) |
| [tts.proto](grpc/v1/tts.proto) | 1.0.0 | `sensory` | TextToSpeech — server streaming, Kokoro EN + Piper TR (ADR-0017) |

> Dependency graph is a tree: `stt` and `tts` both import `common` and never each other. A TTS service must not depend on an STT service.

## Change cost — fan-out

Consumer count is the honest proxy for what a change costs. A contract with five consumers is not one edit, it is five coordinated ones.

| Contract | Consumers | Reading |
|---|---|---|
| `CancellationToken and CancellationEvent` | **5** | adding a required field breaks every producer at once |
| `ProviderResponse` | **5** | adding a required field breaks every producer at once |
| `ToolSpec` | **5** | adding a required field breaks every producer at once |
| `AudioFrame` | **5** | adding a required field breaks every producer at once |
| `Event` | **4** | changes need coordinated updates across consumers |
| `HealthStatus` | **4** | changes need coordinated updates across consumers |

## Ownership

Module-level, not personal. Ownership decides who drafts a change, not who may skip review.

| Owner | Contracts | Module |
|---|---|---|
| `core-orchestration` | 6 | `src/lionel/core/` |
| `observability` | 5 | `src/lionel/platform/telemetry/` |
| `brain` | 5 | `src/lionel/brain/` |
| `capabilities` | 4 | `src/lionel/capabilities/` |
| `memory` | 3 | `src/lionel/memory/` |
| `platform` | 2 | `src/lionel/platform/` |
| `sensory` | 2 | `src/lionel/sensory/` |

**Escalation:** any change to a `stable` contract requires an ADR and Efe's approval, regardless of owner.

## Compatibility policy

Full rules in [README.md](README.md#compatibility-policy). The short version:

| | MINOR (compatible) | MAJOR (breaking) |
|---|---|---|
| Properties | add optional | remove, rename, or add required |
| Enums | add value in **outputs** | add value in **inputs**; change a discriminator |
| Constraints | relax | tighten |
| Protobuf | add optional field, fresh number | reuse or renumber a field |

**The asymmetry that matters:** wire payloads are permissive about unknown fields so a newer producer can talk to an older consumer during a rolling upgrade. **Config files are strict** — per ADR-0015 an unknown key is an error, because a silently-ignored typo leaves the operator running on a default they believe they overrode.

## Invariants enforced in CI

- No audio or image PAYLOAD appears in any control-plane schema. Descriptors live in media/, payload_b64 is fixtures-only. ADR-0006.
- No schema permits free text destined for a shell interpreter. ADR-0011.
- Every ToolSpec declares side_effect and trust_required; the registry rejects tools that do not. ADR-0026, ADR-0012.
- MCPTool never carries side_effect, trust_required, rate limits or audit flags. Authorization metadata does not leave the system.
- Trust is monotonically non-increasing within a turn. ToolResult.trust_of_output and MemoryQueryResult.trust_floor are both required so no path can restore it. ADR-0012.
- turn_id is present on every event and doubles as the OpenTelemetry trace id. ADR-0019.
- policy defaults.decision is pinned to deny by const. ADR-0012.
- memory.forget is a required tool, never optional. ADR-0010.
- Every schema declares version, plane, owner, producer, consumers and compatibility notes.

## Provisional contracts

| Contract | Why provisional | Promotion gate |
|---|---|---|
| `WorkflowEvent` | Nothing produces workflows until memory consolidation lands. Defined now so the Event envelope has a second specialization — a base class with one subclass is just a base class with extra steps. | **G2** |
| `VisionFrame` | No producer, and no protobuf mirror: writing wire format for a subsystem with no producer is speculative. Defined so the data plane is not accidentally designed around audio alone. | **G10**, not committed |

## Validation

`.github/workflows/ci.yml` → `contracts` job:

1. Meta-validate every schema against JSON Schema 2020-12
2. Every example validates against its own schema
3. Cross-file `$ref` resolution
4. `protoc` compile + field-number hygiene (no duplicates, every enum reserves 0)
5. Contract invariants above
6. Every schema declares version, plane, owner, producer, consumers, compatibility

---

*Generated from the `x-lionel` blocks. Regenerate rather than hand-edit — a stale inventory is worse than none, because it is trusted.*
