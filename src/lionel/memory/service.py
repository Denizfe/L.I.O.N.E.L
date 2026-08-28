"""The Memory Service.  ADR-0010.

WHAT MAKES THIS A MEMORY SERVICE AND NOT A VECTOR INDEX
    ADR-0004 was superseded because it exposed Qdrant's own surface, which made every
    caller a de-facto memory-policy author. The policy lives here, and it is the whole
    difference:

        ingestion     salience decides whether an item is worth keeping. `stored: false`
                      is a NORMAL outcome, and the contract says so in as many words.
        dedup         a near-duplicate folds into the existing record rather than
                      accumulating a second copy that competes with it at recall.
        decay         episodic memory expires; durable and decision memory does not.
        ranking       hybrid -- similarity, recency, importance -- weighted from
                      config/lionel.toml [memory.ranking], with the components returned
                      so ranking is debuggable rather than a black box.
        provenance    every record records where it came from and at what trust.
        forget        a real redaction path, tombstoned so consolidation cannot resurrect
                      the text from an earlier summary.

    `contracts/mcp/v1/memory-service.schema.json` and
    `contracts/events/v1/memory-record.schema.json` are both `stability: stable`. This
    module implements them; it does not get to disagree with them.

TRUST DOES NOT LAUNDER
    A record keeps the trust it was ingested at, forever, and `recall` returns the MINIMUM
    trust across its results as `trust_floor`. The caller folds that into the turn's
    TrustContext. Storing a hostile document's contents and recalling them a day later must
    not turn external content into user-originated content -- that is the injection path
    ADR-0012 exists to close, and memory is the obvious way round it.

THE CLOCK IS INJECTED
    G2's DoD requires episodic decay "observed under an accelerated clock". A service that
    read the wall clock directly could only be tested by waiting thirty days.
"""
from __future__ import annotations

import math
import os
import time
import tomllib
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from . import (
    Embedder,
    EmbeddingSpec,
    MemoryConfigurationError,
    MemoryRecord,
    VectorBackend,
    assert_dimensions,
)

__all__ = [
    "MemoryConfig",
    "MemoryService",
    "StoredRecord",
    "new_ulid",
    "cosine",
]

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "config" / "lionel.toml"

# Crockford base32, minus I L O U. The contract pins record ids to
# `^[0-9A-HJKMNP-TV-Z]{26}$`, and tests/contract/ulid_guard.py checks every literal in the
# repository against the same alphabet.
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid(now_ms: int | None = None, *, rand: Callable[[int], bytes] | None = None) -> str:
    """A ULID: 48 bits of millisecond timestamp, 80 bits of randomness, base32.

    Sortable by construction, which matters because consolidation walks records in
    creation order and a random id would need a separate index to do it.
    """
    ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    rnd = (rand or os.urandom)(10)
    value = (ms << 80) | int.from_bytes(rnd, "big")
    out = []
    for i in range(25, -1, -1):
        out.append(_CROCKFORD[(value >> (i * 5)) & 0x1F])
    return "".join(out)


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity, clamped to [0, 1].

    Clamped rather than allowed negative: the contract scores results in [0, 1], and a
    negative similarity folded into a weighted sum could make a recency bonus produce a
    result that "matches" nothing.
    """
    if len(a) != len(b):
        raise ValueError(f"cannot compare vectors of width {len(a)} and {len(b)}")
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, min(1.0, sum(x * y for x, y in zip(a, b)) / (na * nb)))


@dataclass(frozen=True)
class MemoryConfig:
    """`[memory]` and `[memory.ranking]` from config/lionel.toml.

    Read rather than defaulted. The contract's `score` description points at
    `[memory.ranking]` by name, so a service that carried its own defaults would let the
    file and the behaviour disagree silently.
    """

    durable_collection: str
    episodic_collection: str
    episodic_ttl_days: int
    dedup_similarity_threshold: float
    weight_similarity: float
    weight_recency: float
    weight_importance: float
    salience_threshold: float = 0.35

    @classmethod
    def from_toml(cls, path: Path | str | None = None) -> "MemoryConfig":
        p = Path(path) if path is not None else CONFIG_PATH
        if not p.is_file():
            raise MemoryConfigurationError(
                f"{p} is missing; [memory] is not optional and there is no default. The "
                f"ranking weights are referenced by name from "
                f"contracts/mcp/v1/memory-service.schema.json."
            )
        data = tomllib.loads(p.read_text(encoding="utf-8"))
        mem = data.get("memory")
        if not mem:
            raise MemoryConfigurationError(f"no [memory] section in {p.name} (ADR-0010).")
        rank = mem.get("ranking")
        if not rank:
            raise MemoryConfigurationError(
                f"no [memory.ranking] section in {p.name}. The contract calls the score a "
                f"HYBRID rank 'weighted per config/lionel.toml [memory.ranking]'; without "
                f"it there is nothing to weight by."
            )
        try:
            cfg = cls(
                durable_collection=mem["durable_collection"],
                episodic_collection=mem["episodic_collection"],
                episodic_ttl_days=int(mem["episodic_ttl_days"]),
                dedup_similarity_threshold=float(mem["dedup_similarity_threshold"]),
                weight_similarity=float(rank["weight_similarity"]),
                weight_recency=float(rank["weight_recency"]),
                weight_importance=float(rank["weight_importance"]),
            )
        except KeyError as e:
            raise MemoryConfigurationError(
                f"[memory] in {p.name} is missing {e}. Every key here is load-bearing; "
                f"a missing one would be silently substituted by a default that no "
                f"reviewer chose."
            ) from None
        total = cfg.weight_similarity + cfg.weight_recency + cfg.weight_importance
        if abs(total - 1.0) > 1e-6:
            raise MemoryConfigurationError(
                f"[memory.ranking] weights sum to {total}, not 1.0. The contract bounds "
                f"`score` to [0, 1]; weights that do not sum to one produce scores outside "
                f"it, and a score of 1.4 compares against a min_score of 0.3 in a way "
                f"nobody intended."
            )
        return cfg


@dataclass(frozen=True)
class StoredRecord:
    """A `MemoryRecord` from contracts/events/v1, as this service holds it.

    Frozen: redaction and supersession produce a new record rather than mutating one, so a
    caller holding a reference cannot be surprised by a record changing underneath it.
    """

    id: str
    text: str
    kind: str
    trust_level: str
    created_at: datetime
    embedding_model: str
    embedding_dims: int
    vector: tuple[float, ...] = ()
    salience: float = 0.5
    importance: float = 0.5
    confidence: float = 1.0
    provenance: dict[str, Any] = field(default_factory=lambda: {"origin": "text_input"})
    last_accessed_at: datetime | None = None
    access_count: int = 0
    expires_at: datetime | None = None
    superseded_by: str | None = None
    redacted: bool = False
    redacted_at: datetime | None = None
    language: str | None = None
    tags: tuple[str, ...] = ()

    def to_contract(self) -> dict[str, Any]:
        """The record as `memory-record.schema.json` shapes it.

        `vector` is deliberately absent: the contract has no such field. The embedding is
        the backend's business, and putting it on the wire would invite a caller to search
        with it.
        """
        def iso(d: datetime | None) -> str | None:
            return None if d is None else d.astimezone(timezone.utc).isoformat()

        return {
            "id": self.id,
            "text": self.text,
            "kind": self.kind,
            "trust_level": self.trust_level,
            "salience": self.salience,
            "importance": self.importance,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "created_at": iso(self.created_at),
            "last_accessed_at": iso(self.last_accessed_at),
            "access_count": self.access_count,
            "expires_at": iso(self.expires_at),
            "superseded_by": self.superseded_by,
            "redacted": self.redacted,
            "redacted_at": iso(self.redacted_at),
            "embedding_model": self.embedding_model,
            "embedding_dims": self.embedding_dims,
            "language": self.language,
            "tags": list(self.tags),
        }


# Trust levels, weakest first. `recall` returns the minimum across its results, so the
# order here is what "minimum" means.
_TRUST_ORDER = ["external_content", "untrusted", "tool_output", "user_originated", "operator"]


class MemoryService:
    """Memory policy. The backend stores; this decides.

    `backend` is a `VectorBackend` and `embedder` an `Embedder` — both ports, so this class
    has no idea Qdrant exists. That is ADR-0010's swappability claim made structural rather
    than asserted.
    """

    def __init__(self, *, backend: VectorBackend, embedder: Embedder,
                 config: MemoryConfig | None = None, spec: EmbeddingSpec | None = None,
                 clock: Callable[[], datetime] | None = None):
        self.backend = backend
        self.embedder = embedder
        self.config = config or MemoryConfig.from_toml()
        self.spec = spec or EmbeddingSpec.from_lock()
        # Injected so G2's "episodic decay under an accelerated clock" is a test rather
        # than a thirty-day wait.
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._records: dict[str, StoredRecord] = {}

    # -- collections ------------------------------------------------------------------
    def collection_for(self, kind: str) -> str:
        """Two collections, from ADR-0004 and preserved by ADR-0010 as internal schema.

        `decision` shares the durable collection: an ADR indexed on merge never expires,
        which is the same retention policy durable memory has.
        """
        return (self.config.episodic_collection if kind == "episodic"
                else self.config.durable_collection)

    def ensure_collections(self) -> None:
        for name in (self.config.durable_collection, self.config.episodic_collection):
            self.backend.ensure_collection(name, dims=self.spec.dims)

    # -- ingestion --------------------------------------------------------------------
    def salience(self, text: str, *, kind: str, importance: float, tags: Sequence[str]) -> float:
        """How worth keeping this is. ADR-0010's ingestion policy, not 'store everything'.

        Deliberately simple and deliberately explicit. ADR-0010's Costs section says
        salience heuristics need tuning and that tuning needs the eval harness (ADR-0021),
        which is G-later. What matters now is that the decision EXISTS and is visible:
        a threshold nobody can see is a threshold nobody can tune.
        """
        score = 0.25
        words = len(text.split())
        if words >= 4:
            score += 0.2
        if words >= 12:
            score += 0.1
        if kind in ("durable", "decision"):
            score += 0.2          # curated kinds are asked for, not inferred
        if tags:
            score += 0.1
        score += 0.15 * importance
        return max(0.0, min(1.0, score))

    def remember(self, text: str, *, kind: str, importance: float = 0.5,
                 tags: Sequence[str] = (), language: str | None = None,
                 trust: str = "user_originated", provenance: dict[str, Any] | None = None,
                 ) -> dict[str, Any]:
        """`memory.remember`. Returns the contract's output object.

        `stored: false` is a normal outcome twice over — below threshold, or a duplicate.
        """
        if not text or not text.strip():
            raise ValueError("memory.remember requires non-empty text (contract: minLength 1)")
        if kind not in ("durable", "episodic", "decision"):
            raise ValueError(
                f"unknown kind {kind!r}. The contract's enum is durable/episodic/decision, "
                f"and adding a value is a MAJOR change because retention policy keys on it "
                f"— an unknown kind has no defined expiry."
            )
        if trust not in _TRUST_ORDER:
            raise ValueError(f"unknown trust level {trust!r}")

        sal = self.salience(text, kind=kind, importance=importance, tags=tags)
        if sal < self.config.salience_threshold:
            return {"stored": False, "id": None,
                    "reason": "below_salience_threshold", "duplicate_of": None}

        vector = tuple(self.embedder.embed([text])[0])
        assert_dimensions(vector, self.spec, where="memory.remember")

        dup = self._duplicate_of(vector, kind=kind)
        if dup is not None:
            # Fold into the existing record rather than storing a rival copy. Importance
            # takes the max: being told something twice is evidence it matters.
            existing = self._records[dup]
            self._records[dup] = replace(existing,
                                         importance=max(existing.importance, importance),
                                         access_count=existing.access_count + 1)
            return {"stored": False, "id": None,
                    "reason": "duplicate_of_existing", "duplicate_of": dup}

        now = self.clock()
        rec = StoredRecord(
            id=new_ulid(int(now.timestamp() * 1000)),
            text=text, kind=kind, trust_level=trust, created_at=now,
            embedding_model=self.spec.name, embedding_dims=self.spec.dims,
            vector=vector, salience=sal, importance=importance,
            provenance=provenance or {"origin": "text_input"},
            expires_at=(now + timedelta(days=self.config.episodic_ttl_days)
                        if kind == "episodic" else None),
            language=language, tags=tuple(tags),
        )
        self._records[rec.id] = rec
        self.backend.upsert(self.collection_for(kind), [self._as_backend_record(rec)])
        return {"stored": True, "id": rec.id, "reason": "stored", "duplicate_of": None}

    def _duplicate_of(self, vector: Sequence[float], *, kind: str) -> str | None:
        threshold = self.config.dedup_similarity_threshold
        for rid, rec in self._records.items():
            if rec.redacted or rec.kind != kind or not rec.vector:
                continue
            if cosine(vector, rec.vector) >= threshold:
                return rid
        return None

    @staticmethod
    def _as_backend_record(rec: StoredRecord) -> MemoryRecord:
        return MemoryRecord(id=rec.id, text=rec.text, vector=rec.vector,
                            trust=rec.trust_level,
                            payload={"kind": rec.kind, "tags": list(rec.tags)})

    # -- retrieval --------------------------------------------------------------------
    def recall(self, query: str, *, kind: str = "any", limit: int = 8,
               min_score: float = 0.3) -> dict[str, Any]:
        """`memory.recall`. Hybrid rank, with components exposed.

        Expired, redacted and superseded records are excluded here rather than by the
        backend: retention is policy, and a backend that enforced it would be making the
        decision ADR-0010 took away from it.
        """
        if not query or not query.strip():
            raise ValueError("memory.recall requires a non-empty query")
        qv = tuple(self.embedder.embed([query])[0])
        assert_dimensions(qv, self.spec, where="memory.recall")
        now = self.clock()

        scored = []
        for rec in self._records.values():
            if rec.redacted or rec.superseded_by is not None:
                continue
            if rec.expires_at is not None and rec.expires_at <= now:
                continue
            if kind != "any" and rec.kind != kind:
                continue
            components = {
                "similarity": cosine(qv, rec.vector),
                "recency": self._recency(rec, now),
                "importance": rec.importance,
            }
            score = (self.config.weight_similarity * components["similarity"]
                     + self.config.weight_recency * components["recency"]
                     + self.config.weight_importance * components["importance"])
            if score < min_score:
                continue
            scored.append((score, components, rec))

        scored.sort(key=lambda t: t[0], reverse=True)
        top = scored[:limit]

        results = []
        for score, components, rec in top:
            touched = replace(rec, last_accessed_at=now, access_count=rec.access_count + 1)
            self._records[rec.id] = touched
            results.append({"record": touched.to_contract(),
                            "score": round(min(1.0, score), 6),
                            "score_components": {k: round(v, 6) for k, v in components.items()}})

        return {"results": results, "trust_floor": self._trust_floor([r for _, _, r in top])}

    def _recency(self, rec: StoredRecord, now: datetime) -> float:
        """1.0 today, halving every `episodic_ttl_days`.

        The same curve for every kind. Durable memory does not expire, but a durable fact
        recorded yesterday is still likelier to be what was meant than one from a year ago.
        """
        age_days = max(0.0, (now - rec.created_at).total_seconds() / 86400.0)
        return 0.5 ** (age_days / max(1, self.config.episodic_ttl_days))

    @staticmethod
    def _trust_floor(records: Iterable[StoredRecord]) -> str:
        """The weakest trust among results.

        `operator` when there are none: an empty recall introduces no content, so it must
        not drag a turn's trust down. Returning the weakest level for zero records would
        make every query that found nothing a de-facto downgrade.
        """
        levels = [r.trust_level for r in records if r.trust_level in _TRUST_ORDER]
        if not levels:
            return "operator"
        return min(levels, key=_TRUST_ORDER.index)

    # -- redaction --------------------------------------------------------------------
    def forget(self, record_id: str, *, reason: str | None = None) -> dict[str, Any]:
        """`memory.forget`. Text cleared, record tombstoned, vector removed.

        The tombstone stays so consolidation cannot resurrect the content from an earlier
        summary — the contract says so, and a delete that left no tombstone would make
        "forget" true only until the next consolidation run.
        """
        rec = self._records.get(record_id)
        if rec is None or rec.redacted:
            return {"redacted": False, "tombstoned": rec is not None}
        now = self.clock()
        self._records[record_id] = replace(
            rec, text="", vector=(), redacted=True, redacted_at=now,
            provenance={**rec.provenance, "detail": reason} if reason else rec.provenance,
        )
        self.backend.delete(self.collection_for(rec.kind), [record_id])
        return {"redacted": True, "tombstoned": True}

    # -- consolidation ----------------------------------------------------------------
    def consolidate(self, *, older_than_days: int = 7, dry_run: bool = True) -> dict[str, Any]:
        """`memory.consolidate`. Episodic → durable.

        `dry_run` defaults to true, as the contract does. A background job that rewrites
        memory should have to be asked twice.

        Redacted records are never a source. That is the whole reason forget tombstones
        instead of deleting: a summary built from a redacted record would reintroduce the
        text the user asked to remove.
        """
        now = self.clock()
        cutoff = now - timedelta(days=older_than_days)
        sources = [r for r in self._records.values()
                   if r.kind == "episodic" and not r.redacted
                   and r.superseded_by is None and r.created_at <= cutoff]
        if dry_run or not sources:
            return {"consolidated": len(sources), "created_durable_ids": []}

        text = " ".join(r.text for r in sources)[:8192]
        vector = tuple(self.embedder.embed([text])[0])
        durable = StoredRecord(
            id=new_ulid(int(now.timestamp() * 1000)),
            text=text, kind="durable", trust_level=self._trust_floor(sources),
            created_at=now, embedding_model=self.spec.name, embedding_dims=self.spec.dims,
            vector=vector, salience=max(r.salience for r in sources),
            importance=max(r.importance for r in sources),
            provenance={"origin": "consolidation",
                        "source_record_ids": [r.id for r in sources]},
        )
        self._records[durable.id] = durable
        self.backend.upsert(self.config.durable_collection,
                            [self._as_backend_record(durable)])
        for r in sources:
            self._records[r.id] = replace(r, superseded_by=durable.id)
        return {"consolidated": len(sources), "created_durable_ids": [durable.id]}

    # -- migration --------------------------------------------------------------------
    def reindex(self, new_spec: EmbeddingSpec, new_embedder: Embedder) -> dict[str, Any]:
        """ADR-0010's embedding migration. Re-embed in place, lose nothing.

        Possible only because `embedding_model` is stored per record rather than once
        globally — the memory-record contract says exactly that, and calls the alternative
        "unrecoverable data loss disguised as gradually worsening recall".
        """
        old_name = self.spec.name
        live = [r for r in self._records.values() if not r.redacted and r.text]
        if not live:
            return {"reindexed": 0, "from": old_name, "to": new_spec.name}
        vectors = new_embedder.embed([r.text for r in live])
        for rec, vec in zip(live, vectors):
            v = tuple(vec)
            assert_dimensions(v, new_spec, where="reindex")
            self._records[rec.id] = replace(rec, vector=v, embedding_model=new_spec.name,
                                            embedding_dims=new_spec.dims)
        self.spec = new_spec
        self.embedder = new_embedder
        self.ensure_collections()
        for rec in live:
            r = self._records[rec.id]
            self.backend.upsert(self.collection_for(r.kind), [self._as_backend_record(r)])
        return {"reindexed": len(live), "from": old_name, "to": new_spec.name}
