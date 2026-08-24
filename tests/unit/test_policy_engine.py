"""The G1 default-deny proof, and ADR-0012's trust gate.  ADR-0027 layer 1.

MASTER_PLAN_v2 §10, Gate G1: *"Policy Engine denies an unregistered tool by default."*

The trust tests here are a G4 criterion arriving early on purpose — *"a simulated
prompt-injection payload embedded in a file read fails to reach any write tool"*. The
mechanism is structural and exists as soon as the engine does, so testing it now means G4
inherits a proof rather than a plan.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lionel.capabilities import CapabilityRegistry, RegistryError  # noqa: E402
from lionel.policy import (  # noqa: E402
    Decision,
    MalformedRuleset,
    PolicyEngine,
    PolicyError,
    TrustContext,
    TrustLevel,
    TrustSource,
)

REGISTRY_PATH = ROOT / "config" / "capabilities.registry.json"
POLICY_PATH = ROOT / "config" / "policy" / "default.toml"


def registry() -> CapabilityRegistry:
    return CapabilityRegistry.from_json(REGISTRY_PATH)


def engine(**kw) -> PolicyEngine:
    return PolicyEngine.from_toml(POLICY_PATH, registry=registry(), **kw)


def turn(level=TrustLevel.USER_ORIGINATED, turn_id="turn-1") -> TrustContext:
    return TrustContext.for_turn(turn_id, initial=level)


class TestDefaultDeny(unittest.TestCase):
    """G1's DoD clause."""

    def setUp(self):
        self.e = engine()

    def test_unregistered_tool_is_denied(self):
        d = self.e.evaluate(tool_name="wildcard.exfiltrate", trust=turn())
        self.assertEqual(d.decision, Decision.DENY)
        self.assertEqual(d.rule_name, "unregistered tool")
        self.assertIn("capability registry", d.reason)

    def test_shell_is_denied_because_it_does_not_exist(self):
        """ADR-0011 abolished shell execution; there is nothing to allowlist."""
        d = self.e.evaluate(tool_name="shell.exec", trust=turn(TrustLevel.OPERATOR))
        self.assertEqual(d.decision, Decision.DENY)

    def test_operator_trust_does_not_rescue_an_unregistered_tool(self):
        """Registration is not a trust question. The highest trust still has nothing to run."""
        d = self.e.evaluate(tool_name="unknown.thing", trust=turn(TrustLevel.OPERATOR))
        self.assertEqual(d.decision, Decision.DENY)

    def test_malformed_tool_names_are_denied(self):
        for bad in ("filesystem", "Filesystem.Read", "filesystem.", ".read",
                    "filesystem.read.extra", "", "filesystem read"):
            with self.subTest(name=bad):
                self.assertEqual(
                    self.e.evaluate(tool_name=bad, trust=turn()).decision, Decision.DENY)

    def test_a_registered_read_is_allowed(self):
        """The proof must not be vacuous: an engine that denies everything proves nothing."""
        d = self.e.evaluate(tool_name="filesystem.read_file", trust=turn())
        self.assertEqual(d.decision, Decision.ALLOW, d.reason)


class TestTrustGate(unittest.TestCase):
    """ADR-0012: structural, not a filter."""

    def setUp(self):
        self.e = engine()

    def test_write_allowed_from_user_originated_content(self):
        d = self.e.evaluate(tool_name="github.create_issue", trust=turn())
        self.assertEqual(d.decision, Decision.ALLOW, d.reason)

    def test_write_denied_once_a_file_read_degrades_the_turn(self):
        """G4's DoD, early. No classifier, no prompt engineering — arithmetic on a minimum."""
        t = turn()
        t.add_source(TrustSource("file:notes.md", TrustLevel.EXTERNAL_CONTENT,
                                 "contents of a file the model read"))
        d = self.e.evaluate(tool_name="github.create_issue", trust=t)
        self.assertEqual(d.decision, Decision.DENY)
        self.assertIn("injected content", d.reason)

    def test_degradation_is_permanent_within_the_turn(self):
        t = turn()
        t.add_source(TrustSource("web:page", TrustLevel.EXTERNAL_CONTENT))
        t.add_source(TrustSource("efe", TrustLevel.OPERATOR, "a later, more trusted source"))
        self.assertEqual(t.level, TrustLevel.EXTERNAL_CONTENT,
                         "trust rose again; ADR-0012's minimum is not being applied")

    def test_degradation_is_recorded_for_the_audit_trail(self):
        t = turn()
        t.add_source(TrustSource("file:evil.md", TrustLevel.EXTERNAL_CONTENT))
        self.assertEqual(t.degraded_by, "file:evil.md")
        self.assertIsNotNone(t.degraded_at)

    def test_a_turn_with_no_sources_is_untrusted(self):
        t = TrustContext(turn_id="empty")
        self.assertEqual(t.level, TrustLevel.EXTERNAL_CONTENT)

    def test_untrusted_is_an_alias_for_external_content(self):
        self.assertEqual(TrustLevel.parse("untrusted"), TrustLevel.EXTERNAL_CONTENT)
        self.assertEqual(TrustLevel.parse("UNTRUSTED"), TrustLevel.EXTERNAL_CONTENT)

    def test_unknown_trust_level_is_refused(self):
        with self.assertRaises(MalformedRuleset):
            TrustLevel.parse("mostly_fine")


class TestAudit(unittest.TestCase):
    def test_allows_are_logged_as_well_as_denies(self):
        e = engine()
        e.evaluate(tool_name="filesystem.read_file", trust=turn(), call_id="c1")
        e.evaluate(tool_name="nope.nope", trust=turn(), call_id="c2")
        decisions = [(a.call_id, a.decision) for a in e.audit]
        self.assertIn(("c1", Decision.ALLOW), decisions)
        self.assertIn(("c2", Decision.DENY), decisions)

    def test_audit_names_the_rule(self):
        e = engine()
        e.evaluate(tool_name="filesystem.read_file", trust=turn())
        self.assertEqual(e.audit[0].rule_name, "reads are broadly permitted")


class TestLimits(unittest.TestCase):
    # The per-minute rate limit is per TOOL; the containment cap is per TURN. These use a
    # fresh turn id per call so the two limits are measured separately — the first draft
    # reused one turn, hit the 40-call containment cap at call 41, and failed for the wrong
    # reason. That failure is also what proved the containment rule had come alive.
    def test_rate_limit_denies_past_the_ceiling(self):
        clock = [0.0]
        e = engine(clock=lambda: clock[0])
        # config/policy/default.toml allows 120 reads per minute.
        for i in range(120):
            self.assertTrue(
                e.evaluate(tool_name="filesystem.read_file",
                           trust=turn(turn_id=f"t{i}")).allowed)
        d = e.evaluate(tool_name="filesystem.read_file", trust=turn(turn_id="t-last"))
        self.assertEqual(d.decision, Decision.DENY)
        self.assertIn("rate limit", d.reason)

    def test_rate_limit_window_rolls_forward(self):
        clock = [0.0]
        e = engine(clock=lambda: clock[0])
        for i in range(120):
            e.evaluate(tool_name="filesystem.read_file", trust=turn(turn_id=f"t{i}"))
        clock[0] += 61.0
        self.assertTrue(
            e.evaluate(tool_name="filesystem.read_file",
                       trust=turn(turn_id="t-after")).allowed)

    def test_runaway_containment_halts_the_turn(self):
        clock = [0.0]
        e = engine(clock=lambda: clock[0])
        t = turn()
        for i in range(40):
            e.evaluate(tool_name="filesystem.read_file", trust=t)
            clock[0] += 1.0  # stay under the per-minute ceiling; this tests the turn cap
        d = e.evaluate(tool_name="filesystem.read_file", trust=t)
        self.assertEqual(d.decision, Decision.DENY)
        self.assertIn("halted", d.reason.lower() + " " + d.rule_name.lower())

    def test_a_halted_turn_stays_halted(self):
        clock = [0.0]
        e = engine(clock=lambda: clock[0])
        t = turn()
        for _ in range(41):
            e.evaluate(tool_name="filesystem.read_file", trust=t)
            clock[0] += 1.0
        self.assertEqual(
            e.evaluate(tool_name="filesystem.read_file", trust=t).decision, Decision.DENY)

    def test_a_new_turn_is_not_halted(self):
        clock = [0.0]
        e = engine(clock=lambda: clock[0])
        t = turn()
        for _ in range(41):
            e.evaluate(tool_name="filesystem.read_file", trust=t)
            clock[0] += 1.0
        clock[0] += 120.0
        self.assertTrue(
            e.evaluate(tool_name="filesystem.read_file",
                       trust=turn(turn_id="turn-2")).allowed)


class TestRulesetValidation(unittest.TestCase):
    """The schema pins default-deny. The engine refuses to run a ruleset that does not."""

    def test_allow_by_default_is_refused(self):
        with self.assertRaises(MalformedRuleset) as cm:
            PolicyEngine({"defaults": {"decision": "allow"},
                          "rule": [{"name": "r", "decision": "allow"}]})
        self.assertIn("open door", str(cm.exception))

    def test_session_wide_confirmation_is_refused(self):
        with self.assertRaises(MalformedRuleset) as cm:
            PolicyEngine({"defaults": {"decision": "deny"},
                          "rule": [{"name": "r", "decision": "confirm",
                                    "confirmation_scope": "session"}]})
        self.assertIn("rubber stamp", str(cm.exception))

    def test_an_unnamed_rule_is_refused(self):
        with self.assertRaises(MalformedRuleset):
            PolicyEngine({"defaults": {"decision": "deny"},
                          "rule": [{"decision": "allow"}]})

    def test_missing_ruleset_file_does_not_silently_default(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(PolicyError) as cm:
                PolicyEngine.from_toml(Path(d) / "absent.toml")
            self.assertIn("does not fall back", str(cm.exception))

    def test_empty_rule_list_is_refused(self):
        with self.assertRaises(MalformedRuleset):
            PolicyEngine({"defaults": {"decision": "deny"}, "rule": []})


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self.r = registry()

    def test_the_shipped_registry_loads(self):
        self.assertGreater(len(self.r), 0)

    def test_every_capability_declares_its_governance_fields(self):
        for cap in self.r:
            with self.subTest(capability=cap.name):
                self.assertIn(cap.owner, {"capabilities", "memory", "platform", "sensory",
                                          "core-orchestration", "architecture"})
                self.assertIsInstance(cap.requires_network, bool)
                self.assertIsInstance(cap.offline_allowed, bool)

    def test_no_shell_capability(self):
        """ADR-0011. ARCH-001 guards the directory; this guards the registry."""
        self.assertNotIn("shell", self.r)

    def test_l0_excludes_network_capabilities(self):
        """ADR-0007: at L0 a networked capability is absent, not degraded."""
        at_l0 = {c.name for c in self.r.available_at("l0")}
        for cap in self.r:
            if cap.requires_network and not cap.offline_allowed:
                self.assertNotIn(cap.name, at_l0)

    def test_secrets_are_uris_and_are_not_resolved(self):
        for key, uri in self.r.secret_uris().items():
            with self.subTest(key=key):
                self.assertTrue(uri.startswith("secret://"),
                                f"{key} is not a secret URI — ADR-0015 forbids "
                                f"interpolation, and {uri!r} is what interpolation looks like")

    def test_a_missing_registry_is_an_error_not_an_empty_one(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RegistryError) as cm:
                CapabilityRegistry.from_json(Path(d) / "absent.json")
            self.assertIn("denies everything", str(cm.exception))

    def test_a_capability_missing_governance_fields_is_refused(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.json"
            p.write_text(json.dumps({"capabilities": {"x": {"transport": "stdio"}}}),
                         encoding="utf-8")
            with self.assertRaises(RegistryError) as cm:
                CapabilityRegistry.from_json(p)
            self.assertIn("requires_network", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
