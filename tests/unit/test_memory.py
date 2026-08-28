"""The embedding pin, and the two failures that must not look like an empty recall.

ADR-0036's Verification names two things this file has to hold: a dimension assertion that
plants 512 and asserts the refusal, and a cold-cache/no-network path that produces a NAMED
startup error rather than a recall returning nothing.

Everything here runs with neither `qdrant-client` nor `fastembed` installed, which is not a
convenience — it is the point. Those two packages are lazily imported by design, and a test
suite that needed them present could not check what happens when they are absent.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

try:
    import yaml
except ImportError:  # pragma: no cover - pyyaml is CI tooling, not a runtime dependency
    yaml = None

from lionel.memory import (  # noqa: E402
    LOCK_PATH,
    DimensionMismatch,
    Embedder,
    EmbeddingSpec,
    EmbeddingUnavailable,
    FastEmbedEmbedder,
    MemoryConfigurationError,
    MemoryRecord,
    QdrantBackend,
    VectorBackend,
    assert_dimensions,
)


class TestThePin(unittest.TestCase):
    def test_the_shipped_lock_pins_a_model_and_a_width(self):
        spec = EmbeddingSpec.from_lock()
        self.assertEqual(spec.name, "sentence-transformers/all-MiniLM-L6-v2")
        self.assertEqual(spec.dims, 384)

    @unittest.skipIf(yaml is None, "pyyaml is CI tooling and may be absent")
    def test_the_narrow_reader_agrees_with_a_real_yaml_parse(self):
        """The one thing that could drift silently.

        `lionel.memory` reads the lock with a regex, because adding a YAML parser to the
        runtime would need an ADR (Architecture_Freeze.md §4). A narrow reader that quietly
        disagrees with the file is worse than no reader, so the disagreement is what this
        asserts against.
        """
        parsed = yaml.safe_load(LOCK_PATH.read_text(encoding="utf-8"))["models"]["embedding"]
        spec = EmbeddingSpec.from_lock()
        self.assertEqual(spec.name, parsed["name"])
        self.assertEqual(spec.dims, int(parsed["dims"]))

    def test_a_missing_lock_is_an_error_not_a_default(self):
        with self.assertRaises(MemoryConfigurationError) as cm:
            EmbeddingSpec.from_lock(ROOT / "does-not-exist.yaml")
        self.assertIn("no default", str(cm.exception))

    def test_half_a_pin_is_refused(self):
        """The pin IS identifier plus dimension. Either alone pins nothing."""
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "artifacts.lock.yaml"
            p.write_text("models:\n  embedding:\n"
                         "    name: sentence-transformers/all-MiniLM-L6-v2\n",
                         encoding="utf-8", newline="")
            with self.assertRaises(MemoryConfigurationError) as cm:
                EmbeddingSpec.from_lock(p)
            self.assertIn("dims", str(cm.exception))


class TestDimensionAssertion(unittest.TestCase):
    """`artifacts.lock.yaml` says the pin is "a dimension assertion that fails loudly on
    substitution". Until 2026-08-28 no such assertion existed anywhere in the repository."""

    def setUp(self):
        self.spec = EmbeddingSpec.from_lock()

    def test_a_512_wide_vector_is_refused(self):
        with self.assertRaises(DimensionMismatch) as cm:
            assert_dimensions([0.0] * 512, self.spec, where="planted")
        msg = str(cm.exception)
        self.assertIn("512", msg)
        self.assertIn("384", msg)
        self.assertIn("re-index", msg, "the message must name the migration, not just the "
                                       "mismatch — ADR-0010 gives it a path")

    def test_the_right_width_passes(self):
        assert_dimensions([0.0] * 384, self.spec, where="planted")

    def test_the_message_names_its_caller(self):
        """`384 != 512` alone does not say whether the model, the collection or the test
        is wrong, which is the whole difficulty when it fires months later."""
        with self.assertRaises(DimensionMismatch) as cm:
            assert_dimensions([0.0] * 8, self.spec, where="search in 'episodic'")
        self.assertIn("search in 'episodic'", str(cm.exception))

    def test_a_collection_cannot_be_created_at_the_wrong_width(self):
        b = QdrantBackend(spec=self.spec, client=object())
        with self.assertRaises(DimensionMismatch):
            b.ensure_collection("durable", dims=768)


class TestAbsentPackagesFailByName(unittest.TestCase):
    """The failure this file exists for: a missing package must not become an empty recall.

    Both are absent in this environment, so these assert the real path rather than a mock.
    """

    def test_fastembed_absent_raises_a_named_error(self):
        with self.assertRaises(EmbeddingUnavailable) as cm:
            FastEmbedEmbedder(EmbeddingSpec.from_lock()).embed(["hello"])
        msg = str(cm.exception)
        self.assertIn("fastembed", msg)
        self.assertIn("ADR-0036", msg)
        self.assertIn("uv sync", msg, "an error that does not say how to fix it moves the "
                                      "work onto whoever reads the log")

    def test_the_named_error_says_why_it_is_not_an_empty_result(self):
        """The distinction is the reason this raises at all, so it belongs in the text a
        reader actually sees, not only in a docstring."""
        with self.assertRaises(EmbeddingUnavailable) as cm:
            FastEmbedEmbedder(EmbeddingSpec.from_lock()).embed(["hello"])
        self.assertIn("silently returns nothing", str(cm.exception))

    def test_constructing_the_embedder_touches_nothing(self):
        """Construction must not reach the cache or the network. A caller has to be able to
        tell "not configured" from "cannot reach the model"; collapsing them at __init__
        removes the distinction before anyone can act on it."""
        FastEmbedEmbedder(EmbeddingSpec.from_lock())

    def test_qdrant_client_absent_raises_a_named_error(self):
        with self.assertRaises(MemoryConfigurationError) as cm:
            _ = QdrantBackend(spec=EmbeddingSpec.from_lock()).client
        self.assertIn("qdrant-client", str(cm.exception))

    def test_an_injected_client_bypasses_the_import(self):
        sentinel = object()
        self.assertIs(QdrantBackend(spec=EmbeddingSpec.from_lock(), client=sentinel).client,
                      sentinel)


class _FakeBackend:
    """An in-memory VectorBackend. Exists to prove the port is implementable without
    Qdrant — ADR-0010's claim that backends are swappable without touching callers is
    otherwise just a sentence."""

    def __init__(self):
        self.collections: dict[str, dict[str, MemoryRecord]] = {}

    def ensure_collection(self, name, *, dims):
        self.collections.setdefault(name, {})

    def upsert(self, collection, records):
        c = self.collections.setdefault(collection, {})
        n = 0
        for r in records:
            c[r.id] = r
            n += 1
        return n

    def search(self, collection, vector, *, limit=10):
        return list(self.collections.get(collection, {}).values())[:limit]

    def delete(self, collection, ids):
        c = self.collections.setdefault(collection, {})
        return sum(1 for i in ids if c.pop(i, None) is not None)

    def count(self, collection):
        return len(self.collections.get(collection, {}))


class TestThePort(unittest.TestCase):
    def test_a_non_qdrant_backend_satisfies_the_port(self):
        self.assertIsInstance(_FakeBackend(), VectorBackend)

    def test_the_port_check_is_not_vacuous(self):
        """`runtime_checkable` compares method NAMES, not signatures — a weak check, and
        one worth knowing the strength of. It does reject a class missing a method, which
        is what a half-written second backend would look like."""

        class Partial:
            def search(self, collection, vector, *, limit=10): ...

        self.assertNotIsInstance(Partial(), VectorBackend)

    def test_qdrant_satisfies_the_port(self):
        self.assertIsInstance(QdrantBackend(spec=EmbeddingSpec.from_lock(),
                                            client=object()), VectorBackend)

    def test_fastembed_satisfies_the_embedder_port(self):
        self.assertIsInstance(FastEmbedEmbedder(EmbeddingSpec.from_lock()), Embedder)

    def test_a_record_carries_its_trust(self):
        """ADR-0012's propagation is structural. A port that dropped `trust` would launder
        a memory ingested from external content into a trusted one on the way back out."""
        b = _FakeBackend()
        b.upsert("durable", [MemoryRecord(id="1", text="x", vector=(0.0,),
                                          trust="external_content")])
        self.assertEqual(b.search("durable", [0.0])[0].trust, "external_content")

    def test_delete_reports_what_it_removed(self):
        """G2's DoD needs `forget(id)` to be provable. A delete that returns nothing gives
        the Memory Service nothing to assert on."""
        b = _FakeBackend()
        b.upsert("durable", [MemoryRecord(id="1", text="x", vector=(0.0,), trust="user")])
        self.assertEqual(b.delete("durable", ["1"]), 1)
        self.assertEqual(b.count("durable"), 0)


class TestCapabilitySurface(unittest.TestCase):
    def test_qdrant_store_is_absent_from_the_capability_registry(self):
        """ADR-0010 removed `qdrant-store` / `qdrant-find` by name, and G2's DoD checks for
        it. Asserted here as well as in the registry's own tests, because this is the module
        that would make re-adding them convenient."""
        text = (ROOT / "config" / "capabilities.registry.json").read_text(encoding="utf-8")
        for banned in ("qdrant-store", "qdrant-find"):
            self.assertNotIn(f'"{banned}"', text,
                             f"{banned} is on the exposed capability surface; ADR-0010 "
                             f"removed it, and exposing it makes every caller a memory-"
                             f"policy author again")


if __name__ == "__main__":
    unittest.main()
