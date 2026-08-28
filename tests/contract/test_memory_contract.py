"""ADR-0027 layer 2 — the Memory Service's outputs are what the contract says they are.

`tests/unit/test_memory_service.py` checks what the service DOES. This checks that what it
returns is the shape `contracts/mcp/v1/memory-service.schema.json` and
`contracts/events/v1/memory-record.schema.json` describe. They fail differently: a unit
failure means the policy is wrong, a contract failure means the implementation and the
frozen architecture disagree.

Both schemas are `stability: stable` and inside the architecture checksum set, so one side
moving without the other is exactly what this notices. The Memory Service is the first
consumer either has ever had — until 2026-08-28 they described an interface nothing
implemented, which is a contract that cannot be wrong because nothing tests it against
reality.
"""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

from lionel.memory import EmbeddingSpec, MemoryRecord  # noqa: E402
from lionel.memory.service import MemoryConfig, MemoryService  # noqa: E402

CONTRACTS = ROOT / "contracts"
DIMS = 384
T0 = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _registry_arg(schema):
    store = {}
    for p in CONTRACTS.rglob("*.schema.json"):
        doc = _load(p)
        if "$id" in doc:
            store[doc["$id"]] = doc
    try:
        from referencing import Registry, Resource
        registry = Registry().with_resources(
            [(uri, Resource.from_contents(doc)) for uri, doc in store.items()])
        return {"registry": registry}
    except ImportError:
        return {"resolver": jsonschema.RefResolver(base_uri="", referrer=schema, store=store)}


def validator_for(schema: dict):
    """Validate a fragment against the same `$ref` graph the whole contract set uses.

    Nothing is fetched: the `https://lionel.local/...` URIs are identifiers, and the store
    maps them onto files. ADR-0007's guarantee would be a lie if this suite needed the
    network to check the offline configuration.
    """
    cls = jsonschema.validators.validator_for(schema, default=jsonschema.Draft202012Validator)
    return cls(schema, **_registry_arg(schema))


def errors(schema: dict, instance) -> list[str]:
    return [f"{'.'.join(str(x) for x in e.path) or '(root)'}: {e.message}"
            for e in sorted(validator_for(schema).iter_errors(instance),
                            key=lambda e: list(e.path))]


def vec(*leading: float) -> tuple[float, ...]:
    return tuple(list(leading) + [0.0] * (DIMS - len(leading)))


class ScriptedEmbedder:
    def __init__(self, mapping):
        self.mapping = mapping

    def embed(self, texts):
        return [self.mapping.get(t, vec(0.0, 0.0, 1.0)) for t in texts]


class FakeBackend:
    def __init__(self):
        self.c = {}

    def ensure_collection(self, name, *, dims):
        self.c.setdefault(name, {})

    def upsert(self, collection, records):
        d = self.c.setdefault(collection, {})
        n = 0
        for r in records:
            d[r.id] = r
            n += 1
        return n

    def search(self, collection, vector, *, limit=10):
        return list(self.c.get(collection, {}).values())[:limit]

    def delete(self, collection, ids):
        d = self.c.setdefault(collection, {})
        return sum(1 for i in ids if d.pop(i, None) is not None)

    def count(self, collection):
        return len(self.c.get(collection, {}))


TEXT = "Efe prefers Turkish for casual conversation and English for architecture"
QUERY = "hangi dilde konusuyoruz"


def build():
    svc = MemoryService(
        backend=FakeBackend(),
        embedder=ScriptedEmbedder({TEXT: vec(1.0), QUERY: vec(0.98, 0.02)}),
        config=MemoryConfig.from_toml(),
        spec=EmbeddingSpec(name="sentence-transformers/all-MiniLM-L6-v2", dims=DIMS),
        clock=lambda: T0,
    )
    svc.ensure_collections()
    return svc


@unittest.skipIf(jsonschema is None, "jsonschema not installed (pyproject `ci` extra)")
class TestTheSurfaceMatchesTheContract(unittest.TestCase):
    def setUp(self):
        self.contract = _load(CONTRACTS / "mcp" / "v1" / "memory-service.schema.json")
        self.record_schema = _load(CONTRACTS / "events" / "v1" / "memory-record.schema.json")
        self.svc = build()

    def _tool(self, defs_name: str) -> dict:
        """A tool's `$defs` entry, reached the way the contract reaches it.

        Resolved through `properties.tools` rather than read straight out of `$defs`, so a
        `$defs` entry that stops being referenced fails here instead of being validated
        against forever.
        """
        by_ref = {v["$ref"].rsplit("/", 1)[-1]: v["$ref"]
                  for v in self.contract["properties"]["tools"]["properties"].values()}
        self.assertIn(defs_name, by_ref,
                      f"{defs_name} is in $defs but no tool references it")
        return self.contract["$defs"][by_ref[defs_name].rsplit("/", 1)[-1]]

    def test_the_service_implements_every_required_tool(self):
        required = self.contract["properties"]["tools"]["required"]
        for tool in required:
            method = tool.split(".", 1)[1]
            self.assertTrue(callable(getattr(self.svc, method, None)),
                            f"{tool} is required by the contract and MUST NOT become "
                            f"optional; there is no {method}() on the service")

    def test_forget_is_required_by_the_contract(self):
        """The compatibility note says so in as many words: *"memory.forget is required
        from v1.0.0 and MUST NOT become optional."* Asserted rather than assumed, because
        the way it would go missing is a refactor nobody reads the note during."""
        self.assertIn("memory.forget", self.contract["properties"]["tools"]["required"])

    def test_a_stored_record_validates_against_memory_record(self):
        rid = self.svc.remember(TEXT, kind="durable", importance=0.8,
                                tags=["preference"], language="en")["id"]
        self.assertEqual([], errors(self.record_schema,
                                    self.svc._records[rid].to_contract()))

    def test_remember_output_validates(self):
        out = self.svc.remember(TEXT, kind="durable", importance=0.8)
        self.assertEqual([], errors(self._tool("RememberTool")["properties"]["output"], out))

    def test_a_refusal_also_validates(self):
        """`stored: false` is a normal outcome, so the refusal shape is as much a part of
        the contract as the success shape."""
        out = self.svc.remember("no", kind="episodic", importance=0.0)
        self.assertFalse(out["stored"])
        self.assertEqual([], errors(self._tool("RememberTool")["properties"]["output"], out))

    def test_a_duplicate_response_validates(self):
        a, b = "the project root lives under Projects", "project root: under Projects"
        svc = MemoryService(
            backend=FakeBackend(),
            embedder=ScriptedEmbedder({a: vec(1.0), b: vec(1.0, 0.02)}),
            config=MemoryConfig.from_toml(),
            spec=EmbeddingSpec(name="sentence-transformers/all-MiniLM-L6-v2", dims=DIMS),
            clock=lambda: T0)
        svc.ensure_collections()
        svc.remember(a, kind="durable", importance=0.6)
        out = svc.remember(b, kind="durable", importance=0.6)
        self.assertEqual(out["reason"], "duplicate_of_existing")
        self.assertEqual([], errors(self._tool("RememberTool")["properties"]["output"], out))

    def test_recall_output_validates(self):
        self.svc.remember(TEXT, kind="durable", importance=0.8, language="en")
        out = self.svc.recall(QUERY, limit=3)
        self.assertTrue(out["results"], "the fixture must return something, or this "
                                        "validates an empty list against a schema for lists")
        self.assertEqual([], errors(self._tool("RecallTool")["properties"]["output"], out))

    def test_an_empty_recall_output_validates(self):
        out = self.svc.recall("nothing has been stored")
        self.assertEqual([], errors(self._tool("RecallTool")["properties"]["output"], out))

    def test_forget_output_validates(self):
        rid = self.svc.remember(TEXT, kind="durable", importance=0.8)["id"]
        out = self.svc.forget(rid, reason="user said this was wrong")
        self.assertEqual([], errors(self._tool("ForgetTool")["properties"]["output"], out))

    def test_consolidate_output_validates(self):
        out = self.svc.consolidate(older_than_days=7)
        self.assertEqual([], errors(self._tool("ConsolidateTool")["properties"]["output"],
                                    out))

    def test_the_recall_score_stays_inside_the_contract_bounds(self):
        """The schema bounds `score` to [0, 1]. It is a weighted sum, so the bound holds
        only because `MemoryConfig` refuses weights that do not sum to one — two rules in
        different files that have to agree."""
        self.svc.remember(TEXT, kind="durable", importance=1.0, language="en")
        for r in self.svc.recall(QUERY)["results"]:
            self.assertGreaterEqual(r["score"], 0.0)
            self.assertLessEqual(r["score"], 1.0)

    def test_the_record_id_matches_the_contract_pattern(self):
        pattern = self.record_schema["properties"]["id"]["pattern"]
        rid = self.svc.remember(TEXT, kind="durable", importance=0.8)["id"]
        self.assertRegex(rid, pattern)

    def test_every_kind_the_contract_allows_round_trips(self):
        enum = self.record_schema["properties"]["kind"]["enum"]
        self.assertEqual(set(enum), {"durable", "episodic", "decision"})
        for i, kind in enumerate(enum):
            text = f"a sufficiently long sentence number {i} for kind {kind}"
            svc = MemoryService(
                backend=FakeBackend(), embedder=ScriptedEmbedder({text: vec(1.0, i)}),
                config=MemoryConfig.from_toml(),
                spec=EmbeddingSpec(name="sentence-transformers/all-MiniLM-L6-v2",
                                   dims=DIMS),
                clock=lambda: T0)
            svc.ensure_collections()
            rid = svc.remember(text, kind=kind, importance=0.9)["id"]
            self.assertEqual([], errors(self.record_schema,
                                        svc._records[rid].to_contract()),
                             f"kind={kind}")

    def test_the_embedding_model_is_recorded_per_record(self):
        """"Per-record so re-indexing is possible" — the alternative is "unrecoverable
        data loss disguised as gradually worsening recall"."""
        rid = self.svc.remember(TEXT, kind="durable", importance=0.8)["id"]
        rec = self.svc._records[rid].to_contract()
        self.assertEqual(rec["embedding_model"], "sentence-transformers/all-MiniLM-L6-v2")
        self.assertEqual(rec["embedding_dims"], DIMS)

    def test_a_tombstone_validates(self):
        """ADR-0037, accepted 2026-08-28. Until then this asserted the opposite.

        `minLength: 1` and "its text is cleared" could not both hold, so a tombstone was a
        record the record contract rejected — on the one path both schemas call mandatory.
        The schema is 1.1.0 and the conditional resolves it.
        """
        rid = self.svc.remember(TEXT, kind="durable", importance=0.8)["id"]
        self.svc.forget(rid)
        rec = self.svc._records[rid].to_contract()
        self.assertEqual(rec["text"], "")
        self.assertIsNotNone(rec["redacted_at"])
        self.assertEqual([], errors(self.record_schema, rec))

    def test_a_live_record_with_empty_text_is_still_refused(self):
        """The half of ADR-0037 that is a narrowing in effect, if not in form.

        Relaxing `minLength` unconditionally would have been one line. It would also make
        an empty-texted LIVE record valid — one that recalls nothing, matches nothing, and
        looks like a working memory in every listing.
        """
        rid = self.svc.remember(TEXT, kind="durable", importance=0.8)["id"]
        rec = self.svc._records[rid].to_contract()
        rec["text"] = ""
        self.assertNotEqual([], errors(self.record_schema, rec))

    def test_a_tombstone_without_a_date_is_refused(self):
        """A tombstone that cannot be ordered against a consolidation run cannot answer
        the one question anyone asks it."""
        rid = self.svc.remember(TEXT, kind="durable", importance=0.8)["id"]
        self.svc.forget(rid)
        rec = self.svc._records[rid].to_contract()
        rec.pop("redacted_at")
        self.assertNotEqual([], errors(self.record_schema, rec))

    def test_the_conditional_actually_applies(self):
        """The trap this schema fell into for one commit.

        JSON Schema applies every applicable keyword: a base `properties.text.minLength: 1`
        cannot be relaxed by `then`. Leaving it in place produced a conditional that read
        correctly and did nothing — the shape this repository has spent a week naming. The
        assertion is on the schema's structure, because the symptom is silence.
        """
        base = self.record_schema["properties"]["text"]
        self.assertNotIn("minLength", base,
                         "minLength belongs in the if/then branches; a base constraint "
                         "silently overrides the conditional that appears to relax it")
        self.assertEqual(self.record_schema["then"]["properties"]["text"]["minLength"], 0)
        self.assertEqual(self.record_schema["else"]["properties"]["text"]["minLength"], 1)


if __name__ == "__main__":
    unittest.main()
