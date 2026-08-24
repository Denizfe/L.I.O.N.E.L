"""The capability registry.  ADR-0003, ADR-0007, ADR-0012, ADR-0015.

WHAT THIS REPLACES
    v1.0's `mcp.servers.json`. Three things were wrong with it and all three are fixed in
    the frozen `config/capabilities.registry.json` rather than here:

      * `${GITHUB_PAT}` interpolation, which nothing expanded — JSON does not expand
        variables and no component was ever named as the expander. Now a `secret://` URI
        (ADR-0015), dereferenced by `lionel.secrets.SecretResolver` at point of use.
      * Container images by tag. Now pinned by digest (ADR-0013).
      * A `shell` capability. ADR-0011 abolished it, and `ARCH-001` fails the build if the
        directory ever reappears. Its absence is a decision, not an omission.

WHAT THE REGISTRY IS FOR HERE
    The Policy Engine's default-deny needs something to be default-denied *against*. This
    is that something: the set of capabilities anyone has declared, with the governance
    fields ADR-0007 and ADR-0012 require — `requires_network`, `offline_allowed`, `owner`,
    `phase`, `trust_level`, `side_effect_default`, `trust_required`.

TOOL NAMES VERSUS CAPABILITY NAMES
    A ToolCall names `capability.tool` (the pattern is in tool-call.schema.json). The
    registry declares *capabilities*; the individual tools inside one are enumerated by the
    MCP server at connect time, which does not happen until a server is running.

    So at G1 `knows()` answers the question it can actually answer — is this call addressed
    to a declared capability? — and says so plainly rather than implying a completeness it
    does not have. A capability MAY declare a `tools` list, and when it does, the check
    tightens to that list. G4 wires the live enumeration; the interface does not change
    when it does.

TIER FILTERING
    ADR-0007's L0 guarantee is a machine-readable fact, not prose: every capability
    declares `requires_network` and `offline_allowed`, and `available_at("l0")` returns
    only the ones that hold offline. `L0-NETDEP-004` in the gates enforces that the
    declarations exist; this is what consumes them.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

__all__ = ["Capability", "CapabilityRegistry", "RegistryError"]

TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")

_REQUIRED_GOVERNANCE = ("requires_network", "offline_allowed", "owner", "phase",
                        "trust_level")


class RegistryError(Exception):
    """The registry file is missing, malformed, or fails its governance requirements."""


@dataclass(frozen=True)
class Capability:
    name: str
    transport: str
    side_effect_default: str
    trust_required: str
    requires_network: bool
    offline_allowed: bool
    owner: str
    phase: str
    trust_level: str
    supervised: bool = False
    tools: tuple[str, ...] = ()
    secrets: Mapping[str, str] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict)

    def available_at(self, tier: str) -> bool:
        """ADR-0007: at L0 a capability that needs the network is not degraded, it is absent."""
        return self.offline_allowed if tier.lower() == "l0" else True


class CapabilityRegistry:
    """Loads and answers questions about `config/capabilities.registry.json`."""

    def __init__(self, capabilities: Mapping[str, Capability]) -> None:
        self._caps = dict(capabilities)

    # -- construction ------------------------------------------------------------
    @classmethod
    def from_json(cls, path: str | Path) -> "CapabilityRegistry":
        p = Path(path)
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise RegistryError(
                f"no capability registry at {p}. The engine does not synthesise one: with "
                f"no registry every tool is unregistered, and a system that denies "
                f"everything looks identical to one that is misconfigured."
            ) from None
        except json.JSONDecodeError as e:
            raise RegistryError(f"{p} is not valid JSON: {e}") from None

        entries = doc.get("capabilities")
        if not isinstance(entries, dict) or not entries:
            raise RegistryError(f"{p} declares no `capabilities` object")

        caps: dict[str, Capability] = {}
        for name, spec in entries.items():
            missing = [k for k in _REQUIRED_GOVERNANCE if k not in spec]
            if missing:
                raise RegistryError(
                    f"capability `{name}` is missing {', '.join(missing)}. "
                    f"capabilities-registry.schema.json v1.1.0 requires these, and "
                    f"L0-NETDEP-004 enforces them: ADR-0007's L0 exclusion used to be "
                    f"expressed only in prose, and prose does not filter a tier.")
            caps[name] = Capability(
                name=name,
                transport=spec.get("transport", "stdio"),
                side_effect_default=spec.get("side_effect_default", "read"),
                trust_required=spec.get("trust_required", "any"),
                requires_network=bool(spec["requires_network"]),
                offline_allowed=bool(spec["offline_allowed"]),
                owner=spec["owner"],
                phase=spec["phase"],
                trust_level=spec["trust_level"],
                supervised=bool(spec.get("supervised", False)),
                tools=tuple(spec.get("tools", ())),
                secrets=dict(spec.get("secrets", {})),
                raw=spec,
            )
        return cls(caps)

    # -- queries -----------------------------------------------------------------
    def __len__(self) -> int:
        return len(self._caps)

    def __contains__(self, capability: object) -> bool:
        return capability in self._caps

    def __iter__(self):
        return iter(self._caps.values())

    def get(self, capability: str) -> Capability | None:
        return self._caps.get(capability)

    def knows(self, tool_name: str) -> bool:
        """Is this call addressed to a declared capability?

        A malformed name is not known. `tool-call.schema.json` pins the shape to
        `capability.tool`, and accepting something else here would mean the policy engine
        and the router disagree about what a tool name is — which is the kind of
        disagreement that only surfaces once something has already been dispatched.
        """
        if not isinstance(tool_name, str) or not TOOL_NAME.match(tool_name):
            return False
        capability, tool = tool_name.split(".", 1)
        cap = self._caps.get(capability)
        if cap is None:
            return False
        # An empty `tools` tuple means "not yet enumerated", not "no tools". Treating it as
        # the latter would deny every call to every capability at G1 and make the
        # default-deny proof vacuous — the engine would pass its test by refusing
        # everything, including the things it is supposed to allow.
        return not cap.tools or tool in cap.tools

    def side_effect_of(self, tool_name: str) -> str | None:
        if not self.knows(tool_name):
            return None
        return self._caps[tool_name.split(".", 1)[0]].side_effect_default

    def available_at(self, tier: str) -> list[Capability]:
        return [c for c in self._caps.values() if c.available_at(tier)]

    def secret_uris(self) -> dict[str, str]:
        """Every `secret://` URI the registry references, keyed `capability.ENV_NAME`.

        Returned as URIs, never resolved. Resolution is `SecretResolver`'s job and happens
        at point of use — a registry that eagerly resolved its secrets would hold every
        credential in memory from startup, for capabilities that may never be invoked.
        """
        out: dict[str, str] = {}
        for cap in self._caps.values():
            for env_name, uri in cap.secrets.items():
                out[f"{cap.name}.{env_name}"] = uri
        return out
