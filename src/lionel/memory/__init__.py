"""Memory Service ports and adapters.  ADR-0010, ADR-0036.

WHAT IS HERE AND WHAT IS NOT
    ADR-0010 puts a Memory Service in front of the vector store and demotes Qdrant to one
    adapter behind a `VectorBackend` port. This module is the port, the Qdrant adapter, and
    the embedding pin — the parts ADR-0036 decided. Ingestion policy, dedup, decay,
    ranking, provenance and `forget` are the Memory Service itself, and they are G2's work.

    `qdrant_client` and `fastembed` are imported LAZILY, inside the adapter that needs
    them. Two reasons, and the second is the important one:

      1. `python -m unittest` must run with neither installed. ADR-0027 layer 1 is pure
         logic with no I/O, and a module-level import would make every memory test depend
         on a 200 MB ONNX Runtime wheel being present in CI.
      2. A missing package must produce a NAMED error at the point of use, not an
         ImportError from three frames down at import time. ADR-0007's whole argument is
         that degradation must be legible: "fastembed is not installed" and "the model
         cache is cold and there is no network" are different sentences, and a caller that
         sees neither gets an empty recall instead — which reads exactly like "you have no
         memories about that".

THE PIN IS AN ASSERTION, NOT A SENTENCE
    `artifacts.lock.yaml` is the only artifact in the lock with `sha256: null`, and it
    justifies that by saying the pin *is* "the identifier plus a dimension assertion that
    fails loudly on substitution". Until 2026-08-28 no such assertion existed anywhere.
    `EmbeddingSpec.from_lock()` reads the pin and `assert_dimensions()` enforces it, so
    swapping the model is a startup failure rather than a silent re-ranking of every
    memory ever stored.

    The lock is YAML and this repository has no YAML parser at runtime — `pyyaml` is CI
    tooling, and adding it would need an ADR (Architecture_Freeze.md §4). So the reader
    below is narrow on purpose: it looks for two scalars under one key and raises if the
    shape is not what it expects. It never guesses and never defaults.
    `tests/unit/test_memory.py` checks it against a real YAML parse, which is the part that
    would otherwise drift.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Protocol, runtime_checkable

__all__ = [
    "MemoryError_",
    "MemoryConfigurationError",
    "EmbeddingUnavailable",
    "DimensionMismatch",
    "EmbeddingSpec",
    "MemoryRecord",
    "VectorBackend",
    "Embedder",
    "FastEmbedEmbedder",
    "QdrantBackend",
    "assert_dimensions",
    "ulid_to_uuid",
    "uuid_to_ulid",
    "LOCK_PATH",
]

ROOT = Path(__file__).resolve().parents[3]
LOCK_PATH = ROOT / "artifacts.lock.yaml"


# -- errors ----------------------------------------------------------------------------
# Named `MemoryError_` because `MemoryError` is a builtin and shadowing it in a module
# about memory is a debugging session nobody enjoys.
class MemoryError_(Exception):
    """Base for every failure in this module."""


class MemoryConfigurationError(MemoryError_):
    """The service cannot start: a package, a pin or a setting is missing or wrong."""


class EmbeddingUnavailable(MemoryConfigurationError):
    """Embeddings cannot be produced at all.

    Distinct from "no results" on purpose. ADR-0007's guarantee is about the ordinary path
    working with the cable pulled; a cold model cache with no network cannot embed, and the
    honest report of that is a refusal to start, not a recall that returns nothing.
    """


class DimensionMismatch(MemoryConfigurationError):
    """A vector's width disagrees with the pinned embedding model.

    `artifacts.lock.yaml` warns that changing the model "invalidates every stored vector".
    Detected here rather than at the point where retrieval has quietly degraded.
    """


# -- the pin ---------------------------------------------------------------------------
_MODELS_BLOCK = re.compile(r"^  embedding:\n(?P<body>(?:    .*\n|\n)*)", re.M)
_SCALAR = re.compile(r"^    (?P<key>[a-z_]+):\s*(?P<value>[^\n#]+?)\s*$", re.M)


@dataclass(frozen=True)
class EmbeddingSpec:
    """The pinned embedding model, read from `artifacts.lock.yaml`."""

    name: str
    dims: int

    @classmethod
    def from_lock(cls, path: Path | str | None = None) -> "EmbeddingSpec":
        p = Path(path) if path is not None else LOCK_PATH
        if not p.is_file():
            raise MemoryConfigurationError(
                f"{p} is missing. The embedding pin lives there (ADR-0013) and there is no "
                f"default: an unpinned embedding model silently invalidates every stored "
                f"vector the first time it changes."
            )
        text = p.read_text(encoding="utf-8")
        m = _MODELS_BLOCK.search(text)
        if not m:
            raise MemoryConfigurationError(
                f"no `embedding:` entry under two-space indent in {p.name}. This reader is "
                f"deliberately narrow (no YAML parser at runtime — see the module "
                f"docstring); if the lock's shape changed, change this reader with it."
            )
        fields = {mm.group("key"): mm.group("value") for mm in _SCALAR.finditer(m.group("body"))}
        name, dims = fields.get("name"), fields.get("dims")
        if not name or not dims:
            raise MemoryConfigurationError(
                f"`models.embedding` in {p.name} is missing "
                f"{'name' if not name else 'dims'}. The pin IS the identifier plus the "
                f"dimension; half of it pins nothing."
            )
        try:
            width = int(dims)
        except ValueError:
            raise MemoryConfigurationError(
                f"`models.embedding.dims` is {dims!r}, which is not an integer."
            ) from None
        return cls(name=name.strip().strip('"'), dims=width)


def assert_dimensions(vector: Iterable[float], spec: EmbeddingSpec, *, where: str) -> None:
    """Raise unless the vector is exactly as wide as the pin says.

    `where` names the caller, because "384 != 512" on its own does not tell anyone whether
    the model changed, the collection is old, or a test fixture is wrong.
    """
    width = len(list(vector))
    if width != spec.dims:
        raise DimensionMismatch(
            f"{where}: vector has {width} dimensions, but artifacts.lock.yaml pins "
            f"{spec.name} at {spec.dims}. Changing the embedding model invalidates every "
            f"stored vector and requires the documented re-index (ADR-0010); it is not a "
            f"config edit."
        )


# -- records ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MemoryRecord:
    """One stored memory, as the backend sees it.

    `trust` travels with the record because ADR-0012's propagation is structural: a memory
    ingested from external content stays external content when it is recalled, and a port
    that dropped the field would launder it.
    """

    id: str
    text: str
    vector: tuple[float, ...]
    trust: str
    payload: dict[str, Any] = field(default_factory=dict)


# -- the port ---------------------------------------------------------------------------
@runtime_checkable
class VectorBackend(Protocol):
    """Similarity search and nothing else.

    Deliberately small. ADR-0004 was superseded because exposing the store's own surface
    made every caller a memory-policy author; a port that grows ranking or decay methods
    would be that mistake with an extra layer.
    """

    def ensure_collection(self, name: str, *, dims: int) -> None: ...

    def upsert(self, collection: str, records: Iterable[MemoryRecord]) -> int: ...

    def search(self, collection: str, vector: Iterable[float], *,
               limit: int = 10) -> list[MemoryRecord]: ...

    def delete(self, collection: str, ids: Iterable[str]) -> int: ...

    def count(self, collection: str) -> int: ...


@runtime_checkable
class Embedder(Protocol):
    def embed(self, texts: Iterable[str]) -> list[tuple[float, ...]]: ...


# -- adapters ---------------------------------------------------------------------------
class FastEmbedEmbedder:
    """`fastembed` behind the `Embedder` port.  ADR-0036.

    Constructing this does not touch the network or the model cache; `embed()` does. That
    split is what lets a caller distinguish "not configured" from "cannot reach the model",
    which are different problems with different fixes.
    """

    def __init__(self, spec: EmbeddingSpec | None = None):
        self.spec = spec or EmbeddingSpec.from_lock()
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from fastembed import TextEmbedding
        except ImportError as e:
            raise EmbeddingUnavailable(
                f"fastembed is not installed, so no embedding can be produced "
                f"({e}). It is declared in pyproject.toml under ADR-0036; run `uv sync`. "
                f"This is raised rather than returning no results, because a recall that "
                f"silently returns nothing is indistinguishable from having no memories."
            ) from None
        try:
            self._model = TextEmbedding(model_name=self.spec.name)
        except Exception as e:
            raise EmbeddingUnavailable(
                f"fastembed could not load {self.spec.name!r}: {type(e).__name__}: {e}. "
                f"The model is fetched on first use and cached outside this repository, so "
                f"a cold cache with no network fails here. Prime it while online; the "
                f"offline guarantee in ADR-0007 covers the ordinary path, not the first one."
            ) from None
        return self._model

    def embed(self, texts: Iterable[str]) -> list[tuple[float, ...]]:
        model = self._load()
        out = [tuple(float(x) for x in v) for v in model.embed(list(texts))]
        for v in out:
            assert_dimensions(v, self.spec, where="fastembed output")
        return out


_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_CROCKFORD_INDEX = {c: i for i, c in enumerate(_CROCKFORD)}


def ulid_to_uuid(ulid: str) -> str:
    """A record id as Qdrant will accept it.

    Qdrant point ids are "either an unsigned integer or a UUID" -- its own words, in the
    400 it returns for anything else. `memory-record.schema.json` pins record ids to a ULID
    (`^[0-9A-HJKMNP-TV-Z]{26}$`). Neither side is wrong and neither can move: the contract
    is frozen and the store is upstream.

    They are the same 128 bits. A ULID is 26 Crockford-base32 characters over 130 bits with
    the top 2 unused; a UUID is those 16 bytes in hex. So this is a re-spelling, not a
    mapping -- lossless, bijective, and needing no lookup table. `delete(ids)` therefore
    still works from a caller holding only ULIDs, which a random-UUID-plus-payload scheme
    would have broken.

    Found by running the adapter against a real container. No fake backend could have
    reported it: the port permits any string id, and the constraint lives in Qdrant.
    """
    if len(ulid) != 26:
        raise ValueError(f"not a ULID: {ulid!r} is {len(ulid)} characters, expected 26")
    value = 0
    for ch in ulid:
        try:
            value = (value << 5) | _CROCKFORD_INDEX[ch]
        except KeyError:
            raise ValueError(
                f"not a ULID: {ch!r} is not Crockford base32 (I, L, O and U are excluded)"
            ) from None
    raw = value.to_bytes(17, "big")[1:]  # 130 bits carried in 17 bytes; the top 2 are zero
    h = raw.hex()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def uuid_to_ulid(value: str) -> str:
    """The inverse. A record read back from Qdrant carries its contract id again."""
    raw = bytes.fromhex(value.replace("-", ""))
    if len(raw) != 16:
        raise ValueError(f"not a UUID: {value!r}")
    n = int.from_bytes(raw, "big")
    return "".join(_CROCKFORD[(n >> (i * 5)) & 0x1F] for i in range(25, -1, -1))


class QdrantBackend:
    """Qdrant behind the `VectorBackend` port.  ADR-0004 (operational), ADR-0010 (framing).

    The operational decisions ADR-0004 made and ADR-0010 carried forward live here rather
    than in a caller: loopback-only by default, and a URL that can later point at a cluster
    without any caller changing.

    Record ids are re-spelled as UUIDs on the way in and back to ULIDs on the way out --
    see `ulid_to_uuid`. That translation is the adapter's business and nothing above it
    knows it happens, which is the point of the port.
    """

    def __init__(self, url: str = "http://127.0.0.1:6333", *,
                 spec: EmbeddingSpec | None = None, client: Any = None):
        self.spec = spec or EmbeddingSpec.from_lock()
        self.url = url
        self._client = client

    @property
    def client(self):
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient
        except ImportError as e:
            raise MemoryConfigurationError(
                f"qdrant-client is not installed ({e}). It is declared in pyproject.toml "
                f"under ADR-0036; run `uv sync`."
            ) from None
        self._client = QdrantClient(url=self.url)
        return self._client

    def ensure_collection(self, name: str, *, dims: int) -> None:
        if dims != self.spec.dims:
            raise DimensionMismatch(
                f"collection {name!r} would be created at {dims} dimensions, but "
                f"artifacts.lock.yaml pins {self.spec.name} at {self.spec.dims}. A "
                f"collection is only ever as wide as the model that filled it."
            )
        from qdrant_client.models import Distance, VectorParams  # lazy: see module docstring

        if not self.client.collection_exists(name):
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dims, distance=Distance.COSINE),
            )

    def upsert(self, collection: str, records: Iterable[MemoryRecord]) -> int:
        from qdrant_client.models import PointStruct

        points = []
        for r in records:
            assert_dimensions(r.vector, self.spec, where=f"upsert into {collection!r}")
            points.append(PointStruct(
                id=ulid_to_uuid(r.id), vector=list(r.vector),
                payload={"text": r.text, "trust": r.trust, **r.payload},
            ))
        if points:
            self.client.upsert(collection_name=collection, points=points)
        return len(points)

    def search(self, collection: str, vector: Iterable[float], *,
               limit: int = 10) -> list[MemoryRecord]:
        v = list(vector)
        assert_dimensions(v, self.spec, where=f"search in {collection!r}")
        hits = self.client.query_points(
            collection_name=collection, query=v, limit=limit, with_payload=True
        ).points
        out = []
        for h in hits:
            payload = dict(h.payload or {})
            out.append(MemoryRecord(
                id=uuid_to_ulid(str(h.id)), text=payload.pop("text", ""),
                vector=(), trust=payload.pop("trust", "untrusted"), payload=payload,
            ))
        return out

    def delete(self, collection: str, ids: Iterable[str]) -> int:
        wanted = list(ids)
        if wanted:
            self.client.delete(collection_name=collection,
                               points_selector=[ulid_to_uuid(i) for i in wanted])
        return len(wanted)

    def count(self, collection: str) -> int:
        return int(self.client.count(collection_name=collection, exact=True).count)
