# L.I.O.N.E.L Contracts

**Phase 0 / M2.** Interfaces defined before the implementations they constrain.

This directory is the reason the v1.0 → v2.0 migration cost zero lines of code, and the
reason future migrations will be cheap. A schema written after the code is a description.
A schema written before it is a constraint.

## Layout

```
contracts/
├── MANIFEST.json          contract-set version, inventory, negotiation rules
├── Contract_Inventory.md  the full register: version, producer, consumer, owner
├── core/v1/               CROSS-CUTTING — Event envelope, HealthStatus, Metrics
├── mcp/v1/                CONTROL PLANE — MCP capability surface (ADR-0003, ADR-0006)
├── events/v1/             INTERNAL — IR and event shapes crossing module boundaries
├── media/v1/              DATA PLANE descriptors — AudioFrame, VisionFrame
└── grpc/v1/               DATA PLANE wire format — protobuf (ADR-0006, ADR-0028)
```

**Directory versioning, not file versioning.** `v2` appears as a sibling directory and both
are served simultaneously during a migration window. A consumer pins a major version by
importing from a path, which makes the dependency visible in a diff.

## Formats

| Plane | Format | Why |
|---|---|---|
| Control (`mcp/`) | **JSON Schema 2020-12** | MCP is JSON-RPC; schemas are the native validation mechanism |
| Internal (`events/`) | **JSON Schema 2020-12** | Same tooling; these shapes serialize for telemetry and audit |
| Data descriptors (`media/`) | **JSON Schema 2020-12** | Frame *metadata* and test fixtures. **Never carries live PCM** — see below |
| Data wire (`grpc/`) | **Protocol Buffers 3** | ADR-0028. Protobuf is an IDL, not implementation. Binary encoding avoids the ~33% base64 inflation that ADR-0006 exists to prevent |

### Why `media/` is a separate namespace

ADR-0006 forbids PCM on the control plane. AudioFrame and VisionFrame still need JSON
Schema definitions — for the ADR-0027 sensory harness, which describes WAV fixtures, and
so the protobuf messages have a validatable mirror.

Putting them in `events/` would have made the invariant check "no audio types in the
control plane" fail, and the tempting fix would have been to weaken the check. Instead they
live in `media/`, where the rule is stated explicitly: **a live frame's `payload` is
populated only on the data plane. On the control plane only the descriptor travels.** The
schemas enforce this structurally — see `x-lionel.payload_policy` on each.

## The `x-lionel` extension block

Every schema carries one. JSON Schema has no native slot for provenance, ownership, or
compatibility policy, so this is a reserved vocabulary — validators ignore unknown
keywords, so it is inert at validation time and load-bearing at review time.

```jsonc
"x-lionel": {
  "version": "1.0.0",                    // semver of THIS schema
  "adr": ["ADR-0009"],                   // the decisions that produced it
  "stability": "stable",                 // stable | provisional | deprecated
  "plane": "control",                    // control | data | internal
  "owner": "brain",                      // module accountable for changes
  "producer": ["brain_gateway"],         // components that EMIT this shape
  "consumers": ["turn_executor"],        // components that READ it
  "compatibility": {
    "since": "1.0.0",
    "breaking_changes": [],              // append on every major bump, never rewrite
    "notes": "..."                       // what a consumer must know to upgrade safely
  }
}
```

### Why producer and consumer are mandatory

A schema with no declared consumer is dead weight, and a schema with many consumers is
expensive to change. Recording both makes the blast radius of a proposed change visible
**before** the change, rather than discoverable by breaking something. When a schema lists
five consumers, "just add a required field" stops looking cheap.

`producer` is normally a single component. **If two components produce the same shape, that
is a design smell worth an ADR** — it usually means the shape is really two shapes wearing
one name.

### Ownership

`owner` names the module accountable for a contract, not a person. Ownership is about who
must be consulted, not who is to blame.

| Owner | Owns | Scope |
|---|---|---|
| `core-orchestration` | Turn lifecycle, tool routing, cancellation, trust | `src/lionel/core/` |
| `brain` | Provider abstraction, ToolSpec IR, streaming | `src/lionel/brain/` |
| `memory` | Memory Service, records, retrieval | `src/lionel/memory/` |
| `capabilities` | Capability servers, policy, audit | `src/lionel/capabilities/` |
| `sensory` | Audio, wake, VAD, STT, TTS, locale | `src/lionel/sensory/` |
| `platform` | Config, secrets, process supervision, transport | `src/lionel/platform/` |
| `observability` | Telemetry, metrics, health | `src/lionel/platform/telemetry/` |

**Escalation:** any change to a `stable` contract requires an ADR and Efe's approval,
regardless of owner. Ownership decides who drafts it, not who may skip it.

## Compatibility policy

### What is a MINOR change (backward compatible)

- Adding an **optional** property.
- Adding a value to an enum that appears **only in outputs** — consumers already must
  tolerate unknown output values.
- Relaxing a constraint (widening a range, loosening a pattern).
- Adding a new schema file.
- Adding an optional protobuf field with a **fresh** field number.

### What is a MAJOR change (breaking)

- Removing or renaming any property.
- Adding a **required** property.
- Narrowing a type or tightening a constraint.
- Adding a value to an enum that appears in **inputs** — an older producer cannot emit it,
  but worse, an older *consumer* will reject it.
- Changing the discriminator of a union.
- Reusing or renumbering a protobuf field number. **Removed field numbers are `reserved`,
  permanently.**

### The asymmetry that matters

> **Wire formats are permissive about unknown fields. Configuration files are strict.**

Consumers of `events/` and `mcp/` payloads **MUST ignore unknown properties** — this is
what allows a newer producer to talk to an older consumer during a rolling upgrade.

Configuration is the opposite: per **ADR-0015**, an unknown key in `lionel.toml` is an
**error**. A typo'd config key that is silently ignored produces a system running with a
default the operator believes they overrode, and it fails at the worst possible time.

Different failure economics, therefore deliberately different rules. Schemas that describe
config set `additionalProperties: false`; schemas that describe wire payloads do not.

### Version negotiation (M7)

An MCP server declares `contract_version` in its capability manifest. The host compares
majors:

| Case | Behavior |
|---|---|
| Server major **==** host major | Connect |
| Server major **<** host major | Connect if the host still serves that major; otherwise refuse with a clear message |
| Server major **>** host major | **Refuse at connect.** Do not fail at first call |

Refusing at connect rather than at first call is the whole point — an incompatibility
discovered mid-conversation is a bad user experience and a confusing bug report.

## Rules

1. **No implementation in this directory.** Schemas and IDL only.
2. **Every schema names its ADR.** A contract with no decision behind it is an accident.
3. **Every schema carries `examples`.** An example is the fastest correct answer to "what
   does this actually look like", and it is machine-checkable against its own schema — the
   CI contract job does exactly that.
4. **`breaking_changes` is append-only.** The history is the point.
5. **Changing a `stable` schema requires an ADR.** Provisional schemas may change freely
   until promoted.
