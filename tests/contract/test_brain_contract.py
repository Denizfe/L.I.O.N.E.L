"""ADR-0027 layer 2 — the five brain contracts, checked against each other.

Phase 3 builds `src/lionel/brain/` against `tool-spec`, `stream-event`, `provider-request`,
`provider-response` and `provider-capabilities`. All five are `stability: stable`, all five
are inside the architecture checksum set, and **none of them has ever had a consumer**.

That is the same position `memory-record.schema.json` was in for twenty-six days before its
first consumer found that it described a state it forbade (ADR-0037). `Phase2_Final_Signoff.md`
§1 records the pattern: every one of G2's four defects was in something reviewed, frozen, and
never executed. `Phase3_Entry_Checklist.md` item 5 therefore says the first thing to write is
the contract test, not the provider. This is that test, and it ran before any provider code
existed.

WHAT A GATE CANNOT SEE, AND THIS CAN
    `jsonschema` (JSON-004) validates each schema against its metaschema and each schema's
    own examples. It never compares two schemas to each other. Every finding pinned below is
    a pair of contracts describing one concept and disagreeing — which is precisely the
    class ADR-0037's Consequences left open: *"A schema's prose and its examples can
    disagree, and nothing notices."* One level up, so can two schemas.

WHY THESE TESTS ASSERT THE DEFECT RATHER THAN THE FIX
    Editing any of these schemas moves a stable surface inside the checksum set, which
    `Architecture_Freeze.md` §4 reserves to Efe. ADR-0037 practised exactly this: it pinned
    the broken behaviour with a test that said, in its assertion message, that a change in
    the result means the schema moved and needs a decision. On acceptance the test inverts.
    A red test in the suite would be a worse record of the same fact.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

try:
    import jsonschema
except ImportError:  # pragma: no cover - jsonschema is CI tooling
    jsonschema = None

try:
    import tomllib
except ImportError:  # pragma: no cover - 3.11+ per pyproject
    tomllib = None

EVENTS = ROOT / "contracts" / "events" / "v1"
CORE = ROOT / "contracts" / "core" / "v1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def valid(schema: dict, instance) -> bool:
    """Self-contained fragments only. Nothing here crosses a `$ref` to another file, so no
    resolver is needed and ADR-0007's offline guarantee is not quietly leaned on."""
    return jsonschema.Draft202012Validator(schema).is_valid(instance)


class BrainContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool_spec = load(EVENTS / "tool-spec.schema.json")
        cls.stream = load(EVENTS / "stream-event.schema.json")
        cls.request = load(EVENTS / "provider-request.schema.json")
        cls.response = load(EVENTS / "provider-response.schema.json")
        cls.caps = load(EVENTS / "provider-capabilities.schema.json")
        cls.cancellation = load(EVENTS / "cancellation.schema.json")
        cls.core_health = load(CORE / "health-status.schema.json")


class TestTheContractsAgreeWhereTheyShould(BrainContracts):
    """The coherence that already holds. Here so that losing it is a failure rather than a
    thing somebody notices later."""

    def test_the_provider_enum_is_the_same_everywhere_it_appears(self):
        enums = {
            "provider-capabilities": self.caps["properties"]["provider"]["enum"],
            "provider-response": self.response["properties"]["provider"]["enum"],
            "stream-event": self.stream["properties"]["provider"]["enum"],
        }
        first = enums["provider-capabilities"]
        for where, values in enums.items():
            with self.subTest(schema=where):
                self.assertEqual(first, values,
                                 f"{where} lists different providers. ADR-0001 ships three; "
                                 f"a fourth added in one schema and not the others is a "
                                 f"provider that exists for telemetry and not for health.")

    @unittest.skipIf(tomllib is None, "tomllib requires Python 3.11+")
    def test_the_configured_provider_and_its_fallbacks_are_in_the_enum(self):
        """`[brain] provider = "ollama"` is what actually gets constructed. A value the
        contract does not list is a startup failure that no gate would have caught."""
        cfg = tomllib.loads((ROOT / "config" / "lionel.toml").read_text(encoding="utf-8"))
        allowed = set(self.caps["properties"]["provider"]["enum"])
        brain = cfg["brain"]
        self.assertIn(brain["provider"], allowed)
        for name in brain["fallback_chain"]:
            with self.subTest(provider=name):
                self.assertIn(name, allowed)

    def test_the_request_offers_tools_as_the_tool_spec_ir(self):
        """ADR-0009's whole argument: nothing above the adapter constructs a vendor shape.
        If `tools` ever stops being a `$ref` to ToolSpec, provider independence has become
        a comment."""
        self.assertEqual(
            "https://lionel.local/contracts/events/v1/tool-spec.schema.json",
            self.request["properties"]["tools"]["items"]["$ref"])

    def test_stop_reason_is_duplicated_and_still_identical(self):
        """Two verbatim copies of one enum, with no `$ref` between them. They agree today.
        This test exists because nothing else would notice the day they stop — adding
        `refusal` to one of them is a one-line change that reads as complete."""
        self.assertEqual(self.stream["$defs"]["StopReason"]["enum"],
                         self.response["properties"]["stop_reason"]["enum"],
                         "StreamEvent.StopReason and ProviderResponse.stop_reason have "
                         "drifted. They are copies, not references.")


@unittest.skipIf(jsonschema is None, "jsonschema not installed (pyproject `ci` extra)")
class TestHealthStatusIsDescribedTwice(BrainContracts):
    """**No object can satisfy both HealthStatus contracts.**

    `contracts/core/v1/health-status.schema.json` calls itself the *"uniform health report
    for every service and provider"*, names `brain_gateway` in its own producer list,
    requires `service`, and sets `additionalProperties: false`.
    `provider-capabilities.schema.json` defines a second `HealthStatus` in `$defs` with no
    `service` field and `additionalProperties: false`.

    So the core schema rejects a provider's health report for omitting `service`, and the
    provider schema rejects the same report for including it. Phase 3's DoD clause —
    *"`health()` correctly reports not ready while Ollama loads a model"* — cannot be
    written until one of them wins.
    """

    def setUp(self):
        self.hs = self.caps["$defs"]["HealthStatus"]
        self.report = {"live": True, "ready": False, "state": "loading",
                       "checked_at": "2026-09-02T06:00:00Z", "load_progress": 0.4}

    def test_the_core_schema_claims_the_brain_gateway_as_a_producer(self):
        """This is what makes it a contradiction rather than two unrelated shapes."""
        self.assertIn("brain_gateway", self.core_health["x-lionel"]["producer"])

    def test_a_report_the_provider_schema_accepts_is_rejected_by_the_core_schema(self):
        self.assertTrue(valid(self.hs, self.report))
        self.assertFalse(
            valid(self.core_health, self.report),
            "The core HealthStatus now accepts a report with no `service`. That is a "
            "schema change to a stable surface — see ADR-0039 and Architecture_Freeze §4.")

    def test_a_report_the_core_schema_accepts_is_rejected_by_the_provider_schema(self):
        with_service = dict(self.report, service="brain_gateway")
        self.assertTrue(valid(self.core_health, with_service))
        self.assertFalse(
            valid(self.hs, with_service),
            "ProviderCapabilities.HealthStatus now accepts `service`. If that was "
            "intended, the two definitions should be one `$ref` rather than two objects.")

    def test_the_two_state_enums_differ(self):
        core = set(self.core_health["properties"]["state"]["enum"])
        prov = set(self.hs["properties"]["state"]["enum"])
        self.assertEqual({"starting", "shutting_down"}, core - prov,
                         "The state enums have moved. A provider that reports `starting` "
                         "is unrepresentable in the provider schema and fine in the core "
                         "one, which is the drift this pins.")
        self.assertEqual(set(), prov - core)


@unittest.skipIf(jsonschema is None, "jsonschema not installed (pyproject `ci` extra)")
class TestUsageIsDescribedTwice(BrainContracts):
    """`token_counts_estimated` exists on the terminal usage and not on the streamed one.

    Both objects are `additionalProperties: false`, so this is not a widening — a `usage`
    StreamEvent carrying the flag is invalid. And the mid-stream event is exactly where it
    is needed: ADR-0009's ceiling **halts generation**, so the guard runs while tokens are
    still being produced. The flag's own description says the guard *"applies a safety
    margin rather than trusting the number"* — at the one point where it cannot read it.
    """

    def setUp(self):
        self.stream_usage = self.stream["$defs"]["Usage"]
        self.response_usage = self.response["properties"]["usage"]

    def test_the_response_can_say_the_counts_are_estimated_and_the_stream_cannot(self):
        counted = {"input_tokens": 100, "output_tokens": 50, "token_counts_estimated": True}
        self.assertTrue(valid(self.response_usage, counted))
        self.assertFalse(
            valid(self.stream_usage, counted),
            "StreamEvent.Usage now accepts `token_counts_estimated`. If the schema moved, "
            "ADR-0039's first item is discharged and this test should invert.")

    def test_the_two_objects_otherwise_carry_the_same_fields(self):
        """Pinned so the gap stays exactly one field. Two of anything drift by more than
        one field the moment nobody is comparing them."""
        stream_fields = set(self.stream_usage["properties"])
        response_fields = set(self.response_usage["properties"])
        self.assertEqual({"token_counts_estimated"}, response_fields - stream_fields)
        self.assertEqual(set(), stream_fields - response_fields)


@unittest.skipIf(jsonschema is None, "jsonschema not installed (pyproject `ci` extra)")
class TestIdentifiersArePinnedInOnePlaceAndNotTheOther(BrainContracts):
    """The G2 defect shape, arriving in a different contract.

    `QdrantBackend` could not store a conforming record because the contract pinned record
    ids to a ULID and Qdrant accepts an integer or a UUID — an id whose shape was decided in
    one place and not honoured in the other. Both cases below are the same thing one step
    earlier: an identifier constrained where it is defined and unconstrained where it is
    used.
    """

    def test_a_cancellation_token_id_is_a_ulid_in_one_schema_and_any_string_in_the_other(self):
        """`cancellation.schema.json` pins `token_id` to a ULID. `ProviderRequest`
        requires `cancellation_token_id`, calls it *"Non-optional"* in its description, and
        types it `string` — so the empty string satisfies it, and ADR-0025's 200 ms
        cancellation clause has nothing to look the token up by."""
        token = self.cancellation["properties"]["token_id"]
        self.assertEqual("^[0-9A-HJKMNP-TV-Z]{26}$", token["pattern"])

        field = self.request["properties"]["cancellation_token_id"]
        self.assertNotIn("pattern", field,
                         "ProviderRequest.cancellation_token_id now carries a pattern — "
                         "ADR-0039's third item is discharged and this test should invert.")
        self.assertTrue(valid(field, ""),
                        "the empty string is currently a valid cancellation token id")

    def test_a_tool_name_is_pinned_in_tool_spec_and_free_everywhere_it_is_reported(self):
        """`ToolSpec.name` is `<capability>.<operation>`, lowercase by construction, and its
        description says why: ADR-0023, where `.lower()` under a Turkish locale maps `I` to
        dotless `ı` and silently breaks comparison. `ToolCallDelta.name` and
        `ProviderResponse.tool_calls[].name` name the same tool and constrain nothing."""
        spec_name = self.tool_spec["properties"]["name"]
        self.assertEqual("^[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*$", spec_name["pattern"])
        self.assertFalse(valid(spec_name, "İSTANBUL.read"))

        delta_name = self.stream["$defs"]["ToolCallDelta"]["properties"]["name"]
        call_name = self.response["properties"]["tool_calls"]["items"]["properties"]["name"]
        for where, field in (("StreamEvent.ToolCallDelta", delta_name),
                             ("ProviderResponse.tool_calls", call_name)):
            with self.subTest(schema=where):
                self.assertNotIn("pattern", field,
                                 f"{where}.name now carries a pattern — ADR-0039's fourth "
                                 f"item is discharged and this test should invert.")
                self.assertTrue(valid(field, "İSTANBUL.read"),
                                f"{where} currently accepts a tool name ToolSpec forbids")


if __name__ == "__main__":
    unittest.main()
