"""ADR-0027 layer 2 — the five coordinators satisfy their contract with stubs.

MASTER_PLAN_v2 §10, Gate G1: *"coordinators satisfy contract tests with stub
implementations."* That sentence is easy to satisfy vacuously — five empty classes pass any
test that only checks they exist. These check the two properties ADR-0008 actually decided:

  1. **The state-ownership rule.** SessionCoordinator holds all mutable session state;
     the other four are stateless. Enforced here by construction, not by inspection: the
     four are frozen dataclasses, so caching something on `self` raises at runtime.

  2. **The single policy chokepoint.** ADR-0008: *"policy enforcement has exactly one
     chokepoint — ToolRouter — so it cannot be bypassed."* A denial must stop a dispatch
     before anything is sent, and there must be no argument that skips the check.
"""
import dataclasses
import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lionel.capabilities import CapabilityRegistry  # noqa: E402
from lionel.coordinators import (  # noqa: E402
    STATELESS_COORDINATORS,
    ContextAssembler,
    InterruptController,
    NotYetImplemented,
    SessionCoordinator,
    SessionPhase,
    ToolRouter,
    TurnExecutor,
)
from lionel.policy import PolicyEngine, TrustContext, TrustLevel, TrustSource  # noqa: E402


def router() -> ToolRouter:
    return ToolRouter(
        registry=CapabilityRegistry.from_json(ROOT / "config" / "capabilities.registry.json"),
        policy=PolicyEngine.from_toml(
            ROOT / "config" / "policy" / "default.toml",
            registry=CapabilityRegistry.from_json(
                ROOT / "config" / "capabilities.registry.json")))


class TestAllFiveExist(unittest.TestCase):
    def test_the_set_is_five(self):
        five = {SessionCoordinator, TurnExecutor, ContextAssembler, ToolRouter,
                InterruptController}
        self.assertEqual(len(five), 5)

    def test_each_documents_what_it_does_not_know(self):
        """ADR-0008's table has two columns, and the second is the one that decays."""
        for cls in (SessionCoordinator, TurnExecutor, ContextAssembler, ToolRouter,
                    InterruptController):
            with self.subTest(coordinator=cls.__name__):
                doc = inspect.getdoc(cls) or ""
                self.assertIn("not know", doc.lower(),
                              f"{cls.__name__} does not say what it is not responsible for")


class TestStateOwnership(unittest.TestCase):
    """ADR-0008's hard prerequisite for L2."""

    def test_the_four_are_frozen(self):
        for cls in STATELESS_COORDINATORS:
            with self.subTest(coordinator=cls.__name__):
                self.assertTrue(dataclasses.is_dataclass(cls))
                self.assertTrue(cls.__dataclass_params__.frozen,
                                f"{cls.__name__} is mutable; ADR-0008 makes it stateless, and "
                                f"a rule enforced only by review decays the first time "
                                f"someone caches something on self 'just for now'")

    def test_assigning_state_after_construction_raises(self):
        r = router()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            r.cached_results = {}          # type: ignore[attr-defined]
        a = ContextAssembler()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            a.last_prompt = "..."          # type: ignore[attr-defined]

    def test_session_coordinator_is_the_one_that_holds_state(self):
        s = SessionCoordinator("session-1")
        s.wake()
        self.assertEqual(s.state.phase, SessionPhase.LISTENING)
        s.enqueue("turn-1")
        self.assertEqual(s.state.queued_turns, ["turn-1"])
        s.sleep()
        self.assertEqual(s.state.phase, SessionPhase.ASLEEP)
        self.assertIsNone(s.state.current_turn)

    def test_session_coordinator_does_not_execute_turns_itself(self):
        """It owns the queue, not the execution. Without an executor it says so."""
        s = SessionCoordinator("session-1")
        s.enqueue("turn-1")
        with self.assertRaises(NotYetImplemented) as cm:
            s.run_next()
        self.assertIn("G3", cm.exception.gate)


class TestPolicyChokepoint(unittest.TestCase):
    """ADR-0008: exactly one door, and it cannot be bypassed."""

    def setUp(self):
        self.r = router()

    def _turn(self, level=TrustLevel.USER_ORIGINATED, turn_id="t1") -> TrustContext:
        return TrustContext.for_turn(turn_id, initial=level)

    def test_an_unregistered_tool_is_refused_before_dispatch(self):
        with self.assertRaises(PermissionError) as cm:
            self.r.dispatch(tool_name="wildcard.exfiltrate", arguments={},
                            trust=self._turn())
        self.assertIn("unregistered tool", str(cm.exception))

    def test_a_degraded_turn_cannot_reach_a_write_tool(self):
        """G4's DoD clause, through the router rather than the engine."""
        t = self._turn()
        t.add_source(TrustSource("file:README.md", TrustLevel.EXTERNAL_CONTENT))
        with self.assertRaises(PermissionError) as cm:
            self.r.dispatch(tool_name="github.create_issue", arguments={}, trust=t)
        self.assertIn("injected content", str(cm.exception))

    def test_an_allowed_call_reaches_the_unimplemented_dispatch(self):
        """The distinction that makes this test non-vacuous.

        A denial raises PermissionError; an ALLOWED call must get past the policy and fail
        for a different reason — that MCP dispatch is G4. If both raised the same thing,
        this suite could not tell a working chokepoint from a broken router.
        """
        with self.assertRaises(NotYetImplemented) as cm:
            self.r.dispatch(tool_name="filesystem.read_file", arguments={},
                            trust=self._turn())
        self.assertIn("G4", cm.exception.gate)

    def test_dispatch_offers_no_way_to_skip_the_check(self):
        params = set(inspect.signature(ToolRouter.dispatch).parameters)
        for escape in ("force", "skip_policy", "unchecked", "bypass", "trusted"):
            self.assertNotIn(escape, params,
                             f"ToolRouter.dispatch accepts `{escape}`; a chokepoint with an "
                             f"override is a chokepoint with a documented bypass")
        self.assertIn("trust", params,
                      "dispatch does not take a trust context, so it cannot be evaluating one")

    def test_discovery_respects_the_tier(self):
        """ADR-0007: at L0 a networked capability is absent, not degraded."""
        at_l0 = set(self.r.discover("l0"))
        at_l1 = set(self.r.discover("l1"))
        self.assertTrue(at_l0.issubset(at_l1))
        self.assertNotIn("github", at_l0, "github requires the network; L0 must not offer it")


class TestShellsFailHonestly(unittest.TestCase):
    """A stub that returns a plausible value is worse than one that raises."""

    def test_memory_recall_raises_rather_than_returning_empty(self):
        with self.assertRaises(NotYetImplemented) as cm:
            ContextAssembler().assemble(state=SessionCoordinator("s").state,
                                        utterance="hello")
        self.assertIn("G2", cm.exception.gate)

    def test_cancellation_fanout_raises(self):
        with self.assertRaises(NotYetImplemented):
            InterruptController().cancel(turn_id="t1")

    def test_the_one_cancellation_primitive_that_exists_is_wired(self):
        """ADR-0014's supervisor is real, so InterruptController can already use it."""
        from lionel.platform.process_supervisor import ProcessSupervisor
        sup = ProcessSupervisor()
        ic = InterruptController(supervisor=sup)
        ic.kill_supervised_processes()          # must not raise
        self.assertEqual(sup.running(), [])

    def test_windowing_is_real_because_it_needs_no_collaborator(self):
        a = ContextAssembler(token_budget=2)
        self.assertEqual(a.window([{"i": 1}, {"i": 2}, {"i": 3}]), [{"i": 2}, {"i": 3}])


if __name__ == "__main__":
    unittest.main()
