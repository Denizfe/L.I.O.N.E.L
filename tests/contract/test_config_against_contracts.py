"""ADR-0027 layer 2 — the shipped config validates against the frozen contracts.

WHY THIS LAYER EXISTS SEPARATELY FROM THE UNIT TESTS
    `tests/unit/test_policy_engine.py` checks what the engine *does* with the config. This
    checks that the config is what the contract says a config is. They fail differently and
    for different reasons: a unit failure means the engine is wrong, a contract failure
    means the repository is.

    ADR-0027: *"Contract tests catch interface drift at the boundary rather than at
    integration."* The boundary here is `contracts/mcp/v1/*.schema.json`, which is inside
    the architecture checksum set — so a change on the other side of it moves the freeze
    and needs an ADR. This is the test that notices when one side moved and the other
    did not.

    The gates already validate every schema against its own metaschema (`jsonschema` gate)
    and every example inside a schema. Nothing validated the *runtime config files* against
    the schemas that describe them, which is the gap this closes.
"""
import json
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

CONTRACTS = ROOT / "contracts" / "mcp" / "v1"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(schema_name: str):
    """A validator that resolves the local `$ref`s between contracts.

    The schemas reference one another by `https://lionel.local/...` URIs, which are
    identifiers rather than addresses — nothing is fetched. The registry below maps them
    back onto the files in this repository, so validation stays entirely offline. That is
    not a convenience: ADR-0007's guarantee would be a lie if the test suite needed the
    network to check the offline configuration.
    """
    store = {}
    for p in (ROOT / "contracts").rglob("*.schema.json"):
        doc = _load(p)
        if "$id" in doc:
            store[doc["$id"]] = doc
    schema = _load(CONTRACTS / schema_name)
    registry_arg = {}
    try:
        from referencing import Registry, Resource
        registry = Registry().with_resources(
            [(uri, Resource.from_contents(doc)) for uri, doc in store.items()])
        registry_arg = {"registry": registry}
    except ImportError:
        # jsonschema < 4.18 used RefResolver. Fall back rather than skip: this test is
        # worth more than the elegance of one code path.
        registry_arg = {"resolver": jsonschema.RefResolver(base_uri="", referrer=schema,
                                                           store=store)}
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema, **registry_arg)


@unittest.skipIf(jsonschema is None, "jsonschema not installed (pyproject `ci` extra)")
class TestPolicyRuleset(unittest.TestCase):
    def setUp(self):
        with (ROOT / "config" / "policy" / "default.toml").open("rb") as fh:
            self.ruleset = tomllib.load(fh)

    def test_validates_against_the_frozen_schema(self):
        errors = sorted(_validator("policy-ruleset.schema.json").iter_errors(self.ruleset),
                        key=lambda e: list(e.path))
        self.assertEqual(
            [], [f"{'.'.join(str(x) for x in e.path)}: {e.message}" for e in errors])

    def test_default_is_deny(self):
        """The schema pins this with `const`. Asserted here too, because it is the one
        property whose loss would be silent: everything would keep working, better."""
        self.assertEqual(self.ruleset["defaults"]["decision"], "deny")

    def test_a_write_rule_requires_trust(self):
        """ADR-0012's structural gate, read off the policy rather than the engine."""
        writes = [r for r in self.ruleset["rule"]
                  if r.get("match", {}).get("side_effect") == "write"
                  and r.get("decision") == "allow"]
        self.assertTrue(writes, "no rule allows writes; the policy would be vacuous")
        for r in writes:
            self.assertIn("trust", r["match"],
                          f"rule {r['name']!r} allows a write without constraining trust — "
                          f"injected content could reach it")


@unittest.skipIf(jsonschema is None, "jsonschema not installed (pyproject `ci` extra)")
class TestCapabilityRegistry(unittest.TestCase):
    def setUp(self):
        self.doc = _load(ROOT / "config" / "capabilities.registry.json")

    def test_validates_against_the_frozen_schema(self):
        errors = sorted(
            _validator("capabilities-registry.schema.json").iter_errors(self.doc),
            key=lambda e: list(e.path))
        self.assertEqual(
            [], [f"{'.'.join(str(x) for x in e.path)}: {e.message}" for e in errors])

    def test_the_loader_and_the_schema_agree_on_what_is_required(self):
        """A loader that accepts what the schema rejects is a second, weaker contract."""
        from lionel.capabilities import CapabilityRegistry
        reg = CapabilityRegistry.from_json(ROOT / "config" / "capabilities.registry.json")
        self.assertEqual(len(reg), len(self.doc["capabilities"]))


if __name__ == "__main__":
    unittest.main()
