"""The Memory Service's policy.  ADR-0010, ADR-0027 layer 1.

Five of G2's DoD clauses are decidable without a container and are decided here:

    forget(id) provably removes a memory from retrieval
    near-duplicate ingestion is deduplicated
    episodic decay observed under an accelerated clock
    re-index against a second embedding model completes without data loss
    qdrant-store absent from the exposed capability surface   (tests/unit/test_memory.py)

The two that are not: `compose down && up` persistence needs a running Qdrant, and the
semantic-recall clause needs the real embedding model. What is testable here is the
RETRIEVAL PATH — that a query which shares no words with a record still reaches it when the
vectors are close — and the tests below say so rather than claiming to have tested MiniLM.

The embedder is scripted rather than hashed. A hash-based fake would make the geometry an
accident of the hash function, and a dedup test that passes because two strings happened to
collide proves nothing about dedup.
"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lionel.memory import EmbeddingSpec, MemoryConfigurationError, MemoryRecord  # noqa: E402
from lionel.memory.service import (  # noqa: E402
    MemoryConfig,
    MemoryService,
    cosine,
    new_ulid,
)

DIMS = 384
T0 = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)


def vec(*leading: float) -> tuple[float, ...]:
    """A 384-wide vector whose first components are given and the rest zero."""
    return tuple(list(leading) + [0.0] * (DIMS - len(leading)))


class ScriptedEmbedder:
    """Explicit text → vector. The geometry of each test is stated, not hoped for."""

    def __init__(self, mapping: dict[str, tuple[float, ...]], default=None):
        self.mapping = mapping
        self.default = default or vec(0.0, 0.0, 1.0)
        self.calls: list[str] = []

    def embed(self, texts):
        out = []
        for t in texts:
            self.calls.append(t)
            out.append(self.mapping.get(t, self.default))
        return out


class FakeBackend:
    def __init__(self):
        self.collections: dict[str, dict[str, MemoryRecord]] = {}
        self.deleted: list[str] = []

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
        n = 0
        for i in ids:
            self.deleted.append(i)
            if c.pop(i, None) is not None:
                n += 1
        return n

    def count(self, collection):
        return len(self.collections.get(collection, {}))


def service(mapping=None, *, now=T0, config=None):
    clock = {"t": now}
    svc = MemoryService(
        backend=FakeBackend(),
        embedder=ScriptedEmbedder(mapping or {}),
        config=config or MemoryConfig.from_toml(),
        spec=EmbeddingSpec(name="test/fake", dims=DIMS),
        clock=lambda: clock["t"],
    )
    svc.ensure_collections()
    return svc, clock


class TestUlid(unittest.TestCase):
    def test_matches_the_contract_pattern(self):
        import re
        pat = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
        for _ in range(200):
            self.assertRegex(new_ulid(), pat)

    def test_never_emits_the_ambiguous_letters(self):
        """Crockford drops I, L, O and U — the first three because they read as 1, 1 and 0,
        and U because it turns up in words nobody wants in an identifier."""
        joined = "".join(new_ulid() for _ in range(200))
        for c in "ILOU":
            self.assertNotIn(c, joined)

    def test_sorts_by_time(self):
        a = new_ulid(1_700_000_000_000)
        b = new_ulid(1_700_000_001_000)
        self.assertLess(a, b, "ULIDs must sort by creation time; consolidation walks them "
                              "in order and a random id would need a second index")


class TestConfig(unittest.TestCase):
    def test_the_shipped_config_loads(self):
        c = MemoryConfig.from_toml()
        self.assertEqual(c.durable_collection, "lionel_memory")
        self.assertEqual(c.episodic_ttl_days, 30)

    def test_weights_that_do_not_sum_to_one_are_refused(self):
        """The contract bounds `score` to [0, 1]. Weights summing to 1.4 produce scores a
        `min_score` of 0.3 compares against in a way nobody intended."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "lionel.toml"
            p.write_text(
                '[memory]\ndurable_collection="a"\nepisodic_collection="b"\n'
                'episodic_ttl_days=30\ndedup_similarity_threshold=0.95\n'
                '[memory.ranking]\nweight_similarity=0.9\nweight_recency=0.3\n'
                'weight_importance=0.2\n', encoding="utf-8", newline="")
            with self.assertRaises(MemoryConfigurationError) as cm:
                MemoryConfig.from_toml(p)
            self.assertIn("sum to", str(cm.exception))

    def test_a_missing_ranking_section_is_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "lionel.toml"
            p.write_text('[memory]\ndurable_collection="a"\nepisodic_collection="b"\n'
                         'episodic_ttl_days=30\ndedup_similarity_threshold=0.95\n',
                         encoding="utf-8", newline="")
            with self.assertRaises(MemoryConfigurationError):
                MemoryConfig.from_toml(p)


class TestIngestionPolicy(unittest.TestCase):
    """`stored: false` is a normal outcome. Storing everything is what an index does."""

    def test_a_thin_low_importance_item_is_not_stored(self):
        svc, _ = service()
        out = svc.remember("ok", kind="episodic", importance=0.0)
        self.assertFalse(out["stored"])
        self.assertEqual(out["reason"], "below_salience_threshold")
        self.assertIsNone(out["id"])

    def test_a_curated_durable_item_is_stored(self):
        svc, _ = service({"Efe prefers Turkish for casual conversation": vec(1.0)})
        out = svc.remember("Efe prefers Turkish for casual conversation",
                           kind="durable", importance=0.8, tags=["preference"])
        self.assertTrue(out["stored"])
        self.assertEqual(out["reason"], "stored")
        self.assertRegex(out["id"], r"^[0-9A-HJKMNP-TV-Z]{26}$")

    def test_rejection_reaches_neither_the_backend_nor_the_embedder(self):
        """A rejected item must not cost an embedding. Salience is cheap; embedding is not,
        and at G6 it is on the latency budget."""
        svc, _ = service()
        svc.remember("no", kind="episodic", importance=0.0)
        self.assertEqual(svc.embedder.calls, [])
        self.assertEqual(svc.backend.count(svc.config.episodic_collection), 0)

    def test_an_unknown_kind_is_refused_by_name(self):
        svc, _ = service()
        with self.assertRaises(ValueError) as cm:
            svc.remember("a long enough sentence to pass salience", kind="fact")
        self.assertIn("no defined expiry", str(cm.exception))


class TestDeduplication(unittest.TestCase):
    def test_a_near_duplicate_folds_into_the_existing_record(self):
        a = "the project root is C:/Users/deniz/Projects/L.I.O.N.E.L"
        b = "project root: C:/Users/deniz/Projects/L.I.O.N.E.L"
        svc, _ = service({a: vec(1.0, 0.02), b: vec(1.0, 0.0)})
        first = svc.remember(a, kind="durable", importance=0.5)
        second = svc.remember(b, kind="durable", importance=0.9)
        self.assertTrue(first["stored"])
        self.assertFalse(second["stored"])
        self.assertEqual(second["reason"], "duplicate_of_existing")
        self.assertEqual(second["duplicate_of"], first["id"])

    def test_the_fold_keeps_the_higher_importance(self):
        """Being told something twice is evidence it matters, so importance takes the max
        rather than the first value seen."""
        a, b = "root is here and this is long enough", "root is here, long enough too"
        svc, _ = service({a: vec(1.0, 0.02), b: vec(1.0, 0.0)})
        rid = svc.remember(a, kind="durable", importance=0.4)["id"]
        svc.remember(b, kind="durable", importance=0.95)
        self.assertAlmostEqual(svc._records[rid].importance, 0.95)

    def test_a_distant_item_is_not_a_duplicate(self):
        a, b = "the first fact about the project root", "an unrelated fact about audio"
        svc, _ = service({a: vec(1.0), b: vec(0.0, 1.0)})
        svc.remember(a, kind="durable", importance=0.6)
        self.assertTrue(svc.remember(b, kind="durable", importance=0.6)["stored"])

    def test_dedup_does_not_cross_kinds(self):
        """A decision and an episodic note may say the same thing and mean different
        things; retention policy keys on kind, so folding them would give one of them the
        wrong expiry."""
        a, b = "we chose ollama for the offline path", "we chose ollama for offline"
        svc, _ = service({a: vec(1.0), b: vec(1.0)})
        svc.remember(a, kind="decision", importance=0.9)
        self.assertTrue(svc.remember(b, kind="episodic", importance=0.9)["stored"])


class TestRecall(unittest.TestCase):
    def test_a_query_sharing_no_words_still_reaches_the_record(self):
        """The retrieval PATH, not the embedding model.

        G2's DoD wants a dissimilar query to retrieve a stored fact where keyword matching
        fails. With a scripted embedder this proves the ranking path carries a
        vector-space hit that shares no tokens — the model itself is checked at G2 against
        a running Qdrant, and this test does not pretend otherwise.
        """
        stored = "the assistant answers in Turkish when spoken to in Turkish"
        query = "hangi dilde cevap veriyor"
        svc, _ = service({stored: vec(1.0), query: vec(0.98, 0.02)})
        svc.remember(stored, kind="durable", importance=0.8)
        self.assertEqual(set(stored.lower().split()) & set(query.lower().split()), set(),
                         "the fixture must share no words, or this tests keyword matching")
        results = svc.recall(query)["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["record"]["text"], stored)

    def test_score_components_are_exposed(self):
        """The contract exposes them "so ranking is debuggable and tunable rather than a
        black box"."""
        t = "a durable fact worth keeping around"
        svc, _ = service({t: vec(1.0)})
        svc.remember(t, kind="durable", importance=0.8)
        r = svc.recall(t)["results"][0]
        self.assertEqual(set(r["score_components"]), {"similarity", "recency", "importance"})
        self.assertAlmostEqual(r["score_components"]["similarity"], 1.0, places=5)

    def test_the_score_is_the_configured_weighted_sum(self):
        t = "a durable fact worth keeping around"
        svc, _ = service({t: vec(1.0)})
        svc.remember(t, kind="durable", importance=0.8)
        r = svc.recall(t)["results"][0]
        c, w = r["score_components"], svc.config
        expected = (w.weight_similarity * c["similarity"]
                    + w.weight_recency * c["recency"]
                    + w.weight_importance * c["importance"])
        self.assertAlmostEqual(r["score"], round(min(1.0, expected), 6), places=5)

    def test_min_score_filters(self):
        t = "a durable fact worth keeping around"
        svc, _ = service({t: vec(1.0), "unrelated query text here": vec(0.0, 1.0)})
        svc.remember(t, kind="durable", importance=0.8)
        self.assertEqual(svc.recall("unrelated query text here", min_score=0.9)["results"], [])

    def test_kind_filters(self):
        t = "an episodic note about this morning"
        svc, _ = service({t: vec(1.0)})
        svc.remember(t, kind="episodic", importance=0.9)
        self.assertEqual(svc.recall(t, kind="durable")["results"], [])
        self.assertEqual(len(svc.recall(t, kind="episodic")["results"]), 1)

    def test_recall_records_access(self):
        t = "a durable fact worth keeping around"
        svc, _ = service({t: vec(1.0)})
        rid = svc.remember(t, kind="durable", importance=0.8)["id"]
        svc.recall(t)
        self.assertEqual(svc._records[rid].access_count, 1)
        self.assertIsNotNone(svc._records[rid].last_accessed_at)


class TestTrustDoesNotLaunder(unittest.TestCase):
    """The injection path ADR-0012 closes, and the obvious way round it."""

    def test_a_record_keeps_the_trust_it_was_ingested_at(self):
        t = "a claim found inside a document someone sent us"
        svc, _ = service({t: vec(1.0)})
        svc.remember(t, kind="durable", importance=0.9, trust="external_content")
        self.assertEqual(svc.recall(t)["results"][0]["record"]["trust_level"],
                         "external_content")

    def test_trust_floor_is_the_minimum_across_results(self):
        a, b = "a fact the user told us directly", "a claim from a fetched web page"
        # 0.8 apart: close enough that one query reaches both, far enough that dedup does
        # not fold them. The first draft used 0.99 and quietly tested dedup instead.
        svc, _ = service({a: vec(1.0), b: vec(0.8, 0.6), "query about both": vec(1.0)})
        svc.remember(a, kind="durable", importance=0.9, trust="user_originated")
        svc.remember(b, kind="durable", importance=0.9, trust="external_content")
        self.assertEqual(svc.recall("query about both", limit=5)["trust_floor"],
                         "external_content")

    def test_an_empty_recall_does_not_downgrade_the_turn(self):
        """Zero results introduce no content, so the floor must not drag trust down.
        Returning the weakest level here would make every miss a silent downgrade."""
        svc, _ = service()
        self.assertEqual(svc.recall("nothing is stored yet")["trust_floor"], "operator")


class TestForget(unittest.TestCase):
    """G2's DoD: `forget(id)` provably removes a memory from retrieval."""

    def test_a_forgotten_record_is_gone_from_retrieval(self):
        t = "something the user later said was wrong"
        svc, _ = service({t: vec(1.0)})
        rid = svc.remember(t, kind="durable", importance=0.9)["id"]
        self.assertEqual(len(svc.recall(t)["results"]), 1)
        out = svc.forget(rid, reason="user said this was wrong")
        self.assertEqual(out, {"redacted": True, "tombstoned": True})
        self.assertEqual(svc.recall(t)["results"], [])

    def test_the_text_is_cleared_and_the_tombstone_remains(self):
        t = "something the user later said was wrong"
        svc, _ = service({t: vec(1.0)})
        rid = svc.remember(t, kind="durable", importance=0.9)["id"]
        svc.forget(rid)
        self.assertIn(rid, svc._records, "the tombstone must remain, or consolidation can "
                                         "resurrect the text from an earlier summary")
        self.assertEqual(svc._records[rid].text, "")
        self.assertEqual(svc._records[rid].vector, ())

    def test_the_vector_leaves_the_backend(self):
        t = "something the user later said was wrong"
        svc, _ = service({t: vec(1.0)})
        rid = svc.remember(t, kind="durable", importance=0.9)["id"]
        svc.forget(rid)
        self.assertIn(rid, svc.backend.deleted)
        self.assertEqual(svc.backend.count(svc.config.durable_collection), 0)

    def test_forgetting_twice_is_not_a_second_redaction(self):
        t = "something the user later said was wrong"
        svc, _ = service({t: vec(1.0)})
        rid = svc.remember(t, kind="durable", importance=0.9)["id"]
        svc.forget(rid)
        self.assertEqual(svc.forget(rid), {"redacted": False, "tombstoned": True})

    def test_forgetting_an_unknown_id_is_not_a_tombstone(self):
        svc, _ = service()
        self.assertEqual(svc.forget("01ARZ3NDEKTSV4RRFFQ69G5FAV"),
                         {"redacted": False, "tombstoned": False})


class TestDecayUnderAnAcceleratedClock(unittest.TestCase):
    """G2's DoD, and the reason the clock is injected rather than read."""

    def test_an_episodic_record_expires_after_the_ttl(self):
        t = "an episodic note from this morning about the build"
        svc, clock = service({t: vec(1.0)})
        svc.remember(t, kind="episodic", importance=0.9)
        self.assertEqual(len(svc.recall(t, kind="episodic")["results"]), 1)
        clock["t"] = T0 + timedelta(days=svc.config.episodic_ttl_days + 1)
        self.assertEqual(svc.recall(t, kind="episodic")["results"], [])

    def test_a_durable_record_does_not_expire(self):
        t = "a durable fact that should outlive the episodic window"
        svc, clock = service({t: vec(1.0)})
        svc.remember(t, kind="durable", importance=0.9)
        clock["t"] = T0 + timedelta(days=3650)
        self.assertEqual(len(svc.recall(t, kind="durable")["results"]), 1)

    def test_recency_decays_but_does_not_delete(self):
        t = "a durable fact that should outlive the episodic window"
        svc, clock = service({t: vec(1.0)})
        svc.remember(t, kind="durable", importance=0.9)
        fresh = svc.recall(t)["results"][0]["score_components"]["recency"]
        clock["t"] = T0 + timedelta(days=svc.config.episodic_ttl_days)
        aged = svc.recall(t)["results"][0]["score_components"]["recency"]
        self.assertAlmostEqual(fresh, 1.0, places=5)
        self.assertAlmostEqual(aged, 0.5, places=5)

    def test_expiry_is_set_only_for_episodic(self):
        a = "an episodic note from this morning about the build"
        b = "a durable fact that should outlive the episodic window"
        svc, _ = service({a: vec(1.0), b: vec(0.0, 1.0)})
        ep = svc._records[svc.remember(a, kind="episodic", importance=0.9)["id"]]
        du = svc._records[svc.remember(b, kind="durable", importance=0.9)["id"]]
        self.assertIsNotNone(ep.expires_at)
        self.assertIsNone(du.expires_at)


class TestConsolidation(unittest.TestCase):
    def test_dry_run_is_the_default_and_changes_nothing(self):
        t = "an episodic note from a fortnight ago about the build"
        svc, clock = service({t: vec(1.0)})
        svc.remember(t, kind="episodic", importance=0.9)
        clock["t"] = T0 + timedelta(days=14)
        before = dict(svc._records)
        out = svc.consolidate(older_than_days=7)
        self.assertEqual(out["consolidated"], 1)
        self.assertEqual(out["created_durable_ids"], [])
        self.assertEqual(svc._records.keys(), before.keys())

    def test_consolidation_supersedes_rather_than_deletes(self):
        """"Consolidation sets `superseded_by` rather than deleting, so the trail
        survives" — memory-record.schema.json."""
        t = "an episodic note from a fortnight ago about the build"
        svc, clock = service({t: vec(1.0), " ".join([t]): vec(1.0)})
        rid = svc.remember(t, kind="episodic", importance=0.9)["id"]
        clock["t"] = T0 + timedelta(days=14)
        out = svc.consolidate(older_than_days=7, dry_run=False)
        self.assertEqual(out["consolidated"], 1)
        self.assertEqual(len(out["created_durable_ids"]), 1)
        self.assertIn(rid, svc._records)
        self.assertEqual(svc._records[rid].superseded_by, out["created_durable_ids"][0])

    def test_a_superseded_record_leaves_retrieval(self):
        t = "an episodic note from a fortnight ago about the build"
        svc, clock = service({t: vec(1.0)})
        svc.remember(t, kind="episodic", importance=0.9)
        clock["t"] = T0 + timedelta(days=14)
        svc.consolidate(older_than_days=7, dry_run=False)
        self.assertEqual(svc.recall(t, kind="episodic")["results"], [])

    def test_a_redacted_record_is_never_a_source(self):
        """The whole reason forget tombstones instead of deleting. A summary built from a
        redacted record reintroduces the text the user asked to remove."""
        t = "an episodic note the user later asked us to forget entirely"
        svc, clock = service({t: vec(1.0)})
        rid = svc.remember(t, kind="episodic", importance=0.9)["id"]
        svc.forget(rid)
        clock["t"] = T0 + timedelta(days=14)
        out = svc.consolidate(older_than_days=7, dry_run=False)
        self.assertEqual(out["consolidated"], 0)
        self.assertEqual(out["created_durable_ids"], [])

    def test_the_summary_inherits_the_weakest_trust_of_its_sources(self):
        a = "an episodic note from an external document we fetched"
        svc, clock = service({a: vec(1.0)}, )
        svc.remember(a, kind="episodic", importance=0.9, trust="external_content")
        clock["t"] = T0 + timedelta(days=14)
        out = svc.consolidate(older_than_days=7, dry_run=False)
        new_id = out["created_durable_ids"][0]
        self.assertEqual(svc._records[new_id].trust_level, "external_content")


class TestReindex(unittest.TestCase):
    """G2's DoD: re-index against a second embedding model completes without data loss.

    Possible only because `embedding_model` is stored per record — the contract calls the
    alternative "unrecoverable data loss disguised as gradually worsening recall"."""

    def test_every_live_record_is_re_embedded_and_none_is_lost(self):
        a = "the first durable fact worth keeping around"
        b = "the second durable fact worth keeping around"
        svc, _ = service({a: vec(1.0), b: vec(0.0, 1.0)})
        ids = [svc.remember(a, kind="durable", importance=0.8)["id"],
               svc.remember(b, kind="durable", importance=0.8)["id"]]
        new_spec = EmbeddingSpec(name="test/other", dims=DIMS)
        new_emb = ScriptedEmbedder({a: vec(0.0, 0.0, 1.0), b: vec(0.0, 0.0, 0.0, 1.0)})
        out = svc.reindex(new_spec, new_emb)
        self.assertEqual(out, {"reindexed": 2, "from": "test/fake", "to": "test/other"})
        for rid in ids:
            self.assertEqual(svc._records[rid].embedding_model, "test/other")
        self.assertEqual(len(svc._records), 2)

    def test_recall_works_against_the_new_model(self):
        a = "the first durable fact worth keeping around"
        svc, _ = service({a: vec(1.0)})
        svc.remember(a, kind="durable", importance=0.8)
        new_spec = EmbeddingSpec(name="test/other", dims=DIMS)
        svc.reindex(new_spec, ScriptedEmbedder({a: vec(0.0, 1.0)}))
        self.assertEqual(len(svc.recall(a)["results"]), 1)

    def test_a_redacted_record_is_not_resurrected_by_reindex(self):
        a = "a durable fact the user asked us to forget"
        svc, _ = service({a: vec(1.0)})
        rid = svc.remember(a, kind="durable", importance=0.8)["id"]
        svc.forget(rid)
        out = svc.reindex(EmbeddingSpec(name="test/other", dims=DIMS), ScriptedEmbedder({}))
        self.assertEqual(out["reindexed"], 0)
        self.assertEqual(svc._records[rid].text, "")


class TestCosine(unittest.TestCase):
    def test_identical_vectors_score_one(self):
        self.assertAlmostEqual(cosine([1, 2, 3], [1, 2, 3]), 1.0)

    def test_orthogonal_vectors_score_zero(self):
        self.assertAlmostEqual(cosine([1, 0], [0, 1]), 0.0)

    def test_opposed_vectors_clamp_to_zero(self):
        """A negative similarity folded into a weighted sum could let a recency bonus
        produce a result that matches nothing."""
        self.assertAlmostEqual(cosine([1, 0], [-1, 0]), 0.0)

    def test_a_width_mismatch_is_an_error_not_a_zero(self):
        with self.assertRaises(ValueError):
            cosine([1, 0], [1, 0, 0])


if __name__ == "__main__":
    unittest.main()
