"""The Policy Engine, in default-deny.  ADR-0012, ADR-0011, ADR-0026.

WHAT THIS REPLACES
    v1.0 allowlisted shell commands. W2 of MASTER_PLAN_v2 says why that was not a security
    boundary: an allowlist over a shell is a list of things that can each spawn anything
    else. ADR-0011 abolished shell execution entirely, and ADR-0012 put a declarative
    policy where the allowlist used to be.

THE TWO PROPERTIES THAT MATTER

    1. **Default is deny, and the schema pins it.** `contracts/mcp/v1/policy-ruleset.schema.json`
       declares `defaults.decision` as `const: "deny"` — not a default that config can
       override. The reasoning is in the schema itself: *allow-by-default means a forgotten
       tool registration becomes an open door.* Changing it needs a superseding ADR, and
       the schema change makes that visible in review.

       This engine goes further in one respect: an **unregistered tool never reaches the
       rules at all.** Rules describe what registered capabilities may do; a tool nobody
       declared has no side-effect class and no owner, so there is nothing to evaluate and
       no rule that could accidentally match it.

    2. **Trust is structural, not a filter.** ADR-0012: content read from a file or a web
       page is `external_content`, and it *stays* that way for the whole turn. A tool
       requiring `user_originated` cannot be invoked on a turn whose content has been
       degraded — not because a classifier judged the text safe, but because the effective
       trust of the turn is the MINIMUM across every source that entered it, and that
       minimum only ever goes down.

       This is what makes G4's DoD testable: *"a simulated prompt-injection payload
       embedded in a file read fails to reach any write tool."* No prompt engineering is
       involved. The write rule requires `user_originated`; reading the file degraded the
       turn to `external_content`; the rule cannot match.

FIRST MATCH WINS
    Rules are evaluated top to bottom and the first match decides, falling through to
    `defaults.decision`. That is the schema's stated semantics, and it means rule ORDER is
    part of the policy — a containment rule at the top would silently shadow everything
    below it.
"""
from __future__ import annotations

import fnmatch
import time
import tomllib
from collections import deque
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Deque, Iterable, Mapping

__all__ = [
    "TrustLevel", "TrustSource", "TrustContext",
    "Decision", "PolicyDecision", "AuditRecord",
    "PolicyEngine", "PolicyError", "MalformedRuleset",
]


class PolicyError(Exception):
    """Base for policy configuration failures."""


class MalformedRuleset(PolicyError):
    """The ruleset does not satisfy the frozen contract."""


class TrustLevel(IntEnum):
    """ADR-0012's four levels, ordered so that `min()` is the whole propagation rule.

    `untrusted` is an alias for `external_content` — the contract keeps both names because
    "untrusted" reads more clearly in a deny rule, and a vocabulary that reads badly in the
    rule it governs is a vocabulary people get wrong.
    """
    EXTERNAL_CONTENT = 0
    TOOL_RESULT = 1
    USER_ORIGINATED = 2
    OPERATOR = 3

    @classmethod
    def parse(cls, name: str) -> "TrustLevel":
        key = (name or "").strip().lower()
        if key == "untrusted":
            key = "external_content"
        try:
            return cls[key.upper()]
        except KeyError:
            raise MalformedRuleset(
                f"unknown trust level {name!r}. The contract "
                f"(contracts/events/v1/trust-context.schema.json) defines operator, "
                f"user_originated, tool_result, external_content, and untrusted as an "
                f"alias for the last."
            ) from None

    @property
    def wire_name(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class TrustSource:
    """One origin of content that has entered a turn. Append-only within the turn."""
    source_id: str
    level: TrustLevel
    description: str = ""


@dataclass
class TrustContext:
    """The effective trust of a turn.

    `level` is the MINIMUM across `sources`, and is never computed any other way — the
    contract says so in those words. Recomputing it from the sources on every read, rather
    than caching it, means there is no code path that can forget to update it.
    """
    turn_id: str
    sources: list[TrustSource] = field(default_factory=list)
    degraded_at: float | None = None
    degraded_by: str | None = None

    @classmethod
    def for_turn(cls, turn_id: str, initial: TrustLevel = TrustLevel.USER_ORIGINATED,
                 source_id: str = "utterance") -> "TrustContext":
        return cls(turn_id=turn_id,
                   sources=[TrustSource(source_id, initial, "the turn's triggering input")])

    @property
    def level(self) -> TrustLevel:
        if not self.sources:
            # A turn with no recorded source has no basis for trust. Returning the floor is
            # the only safe answer; returning a default would invent provenance.
            return TrustLevel.EXTERNAL_CONTENT
        return min(s.level for s in self.sources)

    def add_source(self, source: TrustSource) -> "TrustContext":
        """Record a new origin. The effective level can only fall."""
        before = self.level
        self.sources.append(source)
        after = self.level
        if after < before:
            self.degraded_at = time.time()
            self.degraded_by = source.source_id
        return self


class Decision(str):
    """`allow` / `deny` / `confirm`, as the contract spells them."""
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"


@dataclass(frozen=True)
class PolicyDecision:
    decision: str
    rule_name: str
    reason: str = ""
    confirmation_scope: str | None = None

    @property
    def allowed(self) -> bool:
        return self.decision == Decision.ALLOW


@dataclass(frozen=True)
class AuditRecord:
    """Every allow AND every deny.

    `config/policy/default.toml` says why in one line: *a log of refusals alone cannot
    answer "what did it actually do last Tuesday".*
    """
    turn_id: str
    call_id: str
    tool_name: str
    trust: str
    decision: str
    rule_name: str
    reason: str
    at: float


class PolicyEngine:
    """Evaluates a tool call against a declarative ruleset. Holds per-turn counters."""

    def __init__(self, ruleset: Mapping, *, registry=None, tier: str | None = None,
                 clock=time.monotonic) -> None:
        self._validate(ruleset)
        self._defaults = ruleset["defaults"]
        self._rules = list(ruleset["rule"])
        self._registry = registry
        self._tier = tier
        self._clock = clock
        self._calls_this_turn: dict[str, int] = {}
        self._recent: dict[str, Deque[float]] = {}
        self._halted_turns: set[str] = set()
        self.audit: list[AuditRecord] = []

    # -- construction ------------------------------------------------------------
    @classmethod
    def from_toml(cls, path: str | Path, **kwargs) -> "PolicyEngine":
        p = Path(path)
        try:
            with p.open("rb") as fh:
                data = tomllib.load(fh)
        except FileNotFoundError:
            raise PolicyError(
                f"no policy ruleset at {p}. The engine does not fall back to a built-in "
                f"policy: a missing ruleset is an operator error, and inventing one here "
                f"would mean the running policy is not the reviewed policy."
            ) from None
        except tomllib.TOMLDecodeError as e:
            raise MalformedRuleset(f"{p} is not valid TOML: {e}") from None
        return cls(data, **kwargs)

    @staticmethod
    def _validate(ruleset: Mapping) -> None:
        if "defaults" not in ruleset or "rule" not in ruleset:
            raise MalformedRuleset(
                "a ruleset needs `defaults` and at least one `rule` "
                "(contracts/mcp/v1/policy-ruleset.schema.json)")
        decision = ruleset["defaults"].get("decision")
        if decision != Decision.DENY:
            raise MalformedRuleset(
                f"defaults.decision is {decision!r}; the contract pins it to \"deny\" with "
                f"`const`. Allow-by-default means a forgotten tool registration becomes an "
                f"open door — changing this needs a superseding ADR, not a config edit.")
        if not ruleset["rule"]:
            raise MalformedRuleset("`rule` must hold at least one entry")
        for r in ruleset["rule"]:
            if not r.get("name"):
                raise MalformedRuleset(
                    "every rule needs a `name`: it appears verbatim in AuditRecord.rule_name "
                    "and is what someone reads during an incident review")
            scope = r.get("confirmation_scope")
            if scope is not None and scope != "per_invocation":
                raise MalformedRuleset(
                    f"confirmation_scope={scope!r}; only `per_invocation` is permitted. A "
                    f"session-wide \"yes to all\" is how confirmation prompts become rubber "
                    f"stamps, which is the failure confirmation exists to avoid.")
            # ADR-0034 rule 4. A rule must decide or constrain. A rule with neither
            # validated under policy-ruleset 1.0.0 and did nothing at all — silently,
            # while reading in the file as though it did something. That is the defect
            # ADR-0034 was written about, so it is refused at load rather than at
            # review.
            if "decision" not in r and not any(
                    k in r for k in ("max_calls_per_turn", "rate_limit_per_minute")):
                raise MalformedRuleset(
                    f"rule {r['name']!r} carries neither a `decision` nor a constraint "
                    f"(`max_calls_per_turn` or `rate_limit_per_minute`). Such a rule does "
                    f"nothing, and reads in the file as though it does something. "
                    f"policy-ruleset.schema.json 1.1.0, ADR-0034 rule 4.")

    # -- evaluation --------------------------------------------------------------
    def evaluate(self, *, tool_name: str, trust: TrustContext, call_id: str = "",
                 side_effect: str | None = None, tags: Iterable[str] = ()) -> PolicyDecision:
        """Decide one call. Records an audit entry either way."""
        d = self._decide(tool_name=tool_name, trust=trust,
                         side_effect=side_effect, tags=set(tags))
        if self._defaults.get("audit", True):
            self.audit.append(AuditRecord(
                turn_id=trust.turn_id, call_id=call_id, tool_name=tool_name,
                trust=trust.level.wire_name, decision=d.decision,
                rule_name=d.rule_name, reason=d.reason, at=time.time()))
        if d.allowed:
            self._count(tool_name, trust.turn_id)
        return d

    def _decide(self, *, tool_name: str, trust: TrustContext,
                side_effect: str | None, tags: set[str]) -> PolicyDecision:
        if trust.turn_id in self._halted_turns:
            return PolicyDecision(Decision.DENY, "runaway containment",
                                  "this turn was halted after exceeding max_calls_per_turn")

        # The G1 DoD clause: an unregistered tool is denied before any rule is consulted.
        if self._registry is not None and not self._registry.knows(tool_name):
            return PolicyDecision(
                Decision.DENY, "unregistered tool",
                f"`{tool_name}` is not in the capability registry. ADR-0012 is default-deny: "
                f"a tool nobody declared has no side-effect class and no owner, so there is "
                f"nothing to evaluate — and no rule that could match it by accident.")

        if side_effect is None and self._registry is not None:
            side_effect = self._registry.side_effect_of(tool_name)
        capability = tool_name.split(".", 1)[0] if "." in tool_name else tool_name

        # ── Pass 1: constraint rules, evaluated regardless of position ──────────────
        #
        # A rule carrying limits but NO `decision` constrains without deciding. The
        # schema's "first match wins" governs which rule DECIDES; a rule that decides
        # nothing cannot win a match, so position must not determine whether it applies.
        #
        # This is not a liberty taken with the contract — it is the only reading under
        # which the shipped `config/policy/default.toml` does what it says. Its last rule
        # is:
        #
        #     [[rule]]
        #     name = "runaway containment"
        #     match.any = true
        #     max_calls_per_turn = 40
        #     on_exceeded = "halt_turn"
        #
        # Under strict positional first-match-wins that rule is unreachable: "reads are
        # broadly permitted" matches first and returns `allow`, so a tool-calling loop
        # would run unbounded while the policy file appeared to bound it. Dead policy that
        # looks live is worse than absent policy — it answers the review question wrongly.
        #
        # Two tests in tests/unit/test_policy_engine.py failed against the positional
        # reading and are what surfaced this. Worth raising with the contract owner: the
        # Match description in policy-ruleset.schema.json does not mention constraint-only
        # rules, so the contract and the default policy currently disagree about whether a
        # containment rule at the bottom of the file does anything.
        for rule in self._rules:
            if "decision" in rule or "max_calls_per_turn" not in rule:
                continue
            if not self._matches(rule, tool_name, capability, side_effect, trust, tags):
                continue
            if self._over_turn_limit(rule, tool_name, trust.turn_id):
                if rule.get("on_exceeded", "deny_call") == "halt_turn":
                    self._halted_turns.add(trust.turn_id)
                    return PolicyDecision(Decision.DENY, rule["name"],
                                          "max_calls_per_turn exceeded; turn halted")
                return PolicyDecision(Decision.DENY, rule["name"],
                                      "max_calls_per_turn exceeded")

        # ── Pass 2: the deciding rule. First match wins, as the schema states ───────
        for rule in self._rules:
            if "decision" not in rule:
                continue
            if not self._matches(rule, tool_name, capability, side_effect, trust, tags):
                continue

            if self._over_turn_limit(rule, tool_name, trust.turn_id):
                if rule.get("on_exceeded", "deny_call") == "halt_turn":
                    self._halted_turns.add(trust.turn_id)
                    return PolicyDecision(Decision.DENY, rule["name"],
                                          "max_calls_per_turn exceeded; turn halted")
                return PolicyDecision(Decision.DENY, rule["name"],
                                      "max_calls_per_turn exceeded")

            if self._over_rate_limit(rule, tool_name):
                return PolicyDecision(Decision.DENY, rule["name"],
                                      f"rate limit of {rule['rate_limit_per_minute']}/min "
                                      f"exceeded for `{tool_name}`")

            return PolicyDecision(rule["decision"], rule["name"],
                                  rule.get("reason", ""),
                                  rule.get("confirmation_scope"))

        return PolicyDecision(
            Decision.DENY, "default",
            "no rule matched, and the default is deny "
            "(policy-ruleset.schema.json pins defaults.decision to \"deny\")")

    def _matches(self, rule: Mapping, tool_name: str, capability: str,
                 side_effect: str | None, trust: TrustContext, tags: set[str]) -> bool:
        m = rule.get("match")
        if not m:
            # No `match` block is a wildcard by the schema's own words: "an absent
            # condition is a wildcard", and a Match with no conditions is all wildcards.
            return True
        if m.get("any"):
            return True
        if "tool" in m and not fnmatch.fnmatchcase(tool_name, m["tool"]):
            return False
        if "capability" in m and m["capability"] != capability:
            return False
        if "side_effect" in m and m["side_effect"] != side_effect:
            return False
        if "trust" in m and TrustLevel.parse(m["trust"]) != trust.level:
            return False
        if "tier" in m and self._tier is not None and m["tier"] != self._tier:
            return False
        if "tags" in m and not set(m["tags"]).issubset(tags):
            return False
        return True

    # -- counters ----------------------------------------------------------------
    def _count(self, tool_name: str, turn_id: str) -> None:
        self._calls_this_turn[turn_id] = self._calls_this_turn.get(turn_id, 0) + 1
        self._recent.setdefault(tool_name, deque()).append(self._clock())

    def _over_turn_limit(self, rule: Mapping, tool_name: str, turn_id: str) -> bool:
        limit = rule.get("max_calls_per_turn")
        return limit is not None and self._calls_this_turn.get(turn_id, 0) >= limit

    def _over_rate_limit(self, rule: Mapping, tool_name: str) -> bool:
        limit = rule.get("rate_limit_per_minute")
        if limit is None:
            return False
        window = self._recent.setdefault(tool_name, deque())
        cutoff = self._clock() - 60.0
        while window and window[0] < cutoff:
            window.popleft()
        return len(window) >= limit

    def end_turn(self, turn_id: str) -> None:
        self._calls_this_turn.pop(turn_id, None)
        self._halted_turns.discard(turn_id)
