"""Helper for `scripts/verify_memory.sh`. Prints TSV, never prose.

Separate from the shell driver for the reason `_preflight_table.py` is: two quoting regimes
must never fight over the same backslashes, and a Python block inside a heredoc turns `\n`
into a real newline before Python sees it. That has cost three attempts in this repository
already; the split is cheaper.

Commands
    reachable                 is Qdrant answering on the configured URL
    write    <collection>      store one record, print its id
    read     <collection> <id> read it back, print what came out
    semantic <collection>      a dissimilar query retrieves the right fact
    embedder                   which embedder is available, and why

EXIT CODES ARE THE SAME CONTRACT AS EVERYWHERE ELSE
    0 pass · 1 the thing being checked failed · 2 this script is broken.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

for _stream in (sys.stdout, sys.stderr):
    try:
        # newline="" or Python translates \n to os.linesep and welds a CR onto every field,
        # which `read -r` then keeps. §9.11 records the day that cost.
        _stream.reconfigure(encoding="utf-8", errors="replace", newline="")
    except (AttributeError, ValueError):
        pass

QDRANT_URL = "http://127.0.0.1:6333"


def emit(verdict: str, detail: str) -> None:
    sys.stdout.write(f"{verdict}\t{detail}\n")


class DeterministicEmbedder:
    """A stand-in when the real model cannot be fetched.

    NOT runtime code, and deliberately not in `src/lionel/`. A fake embedder that ships
    with the service is one that gets used by accident, and the failure mode is a memory
    system that appears to work and recalls nonsense.

    It is a fixture with one job: give persistence something to persist. A run that uses it
    proves the STORE survives a restart. It proves nothing whatever about retrieval quality,
    and `verify_memory.sh` says which embedder it used in every line it prints.
    """

    name = "deterministic-fixture"

    def __init__(self, dims: int):
        self.dims = dims

    def embed(self, texts):
        out = []
        for t in texts:
            v = [0.0] * self.dims
            for i, ch in enumerate(t.encode("utf-8")):
                v[(i * 31 + ch) % self.dims] += 1.0
            norm = sum(x * x for x in v) ** 0.5 or 1.0
            out.append(tuple(x / norm for x in v))
        return out


def get_embedder(spec):
    """The real one if its cache is warm, the fixture otherwise. Never silently."""
    from lionel.memory import EmbeddingUnavailable, FastEmbedEmbedder

    try:
        e = FastEmbedEmbedder(spec)
        e.embed(["warmup"])
        return e, "fastembed", spec.name
    except EmbeddingUnavailable as exc:
        first = str(exc).split(".")[0]
        return DeterministicEmbedder(spec.dims), "fixture", first


def cmd_reachable() -> int:
    from lionel.memory import QdrantBackend, EmbeddingSpec

    spec = EmbeddingSpec.from_lock()
    try:
        b = QdrantBackend(QDRANT_URL, spec=spec)
        b.client.get_collections()
    except Exception as exc:
        emit("fail", f"{type(exc).__name__}: {str(exc).splitlines()[0][:120]}")
        return 1
    emit("pass", f"Qdrant answering at {QDRANT_URL}")
    return 0


def _service(collection: str):
    from lionel.memory import EmbeddingSpec, QdrantBackend
    from lionel.memory.service import MemoryConfig, MemoryService

    spec = EmbeddingSpec.from_lock()
    embedder, which, detail = get_embedder(spec)
    cfg = MemoryConfig.from_toml()
    backend = QdrantBackend(QDRANT_URL, spec=spec)
    backend.ensure_collection(collection, dims=spec.dims)
    svc = MemoryService(backend=backend, embedder=embedder, config=cfg, spec=spec)
    return svc, backend, which, detail


TEXT = ("Efe prefers Turkish for casual conversation and English for architecture "
        "discussions, and said so on 2026-08-28.")


def cmd_write(collection: str) -> int:
    from lionel.memory import MemoryRecord
    from lionel.memory.service import new_ulid

    svc, backend, which, detail = _service(collection)
    vector = tuple(svc.embedder.embed([TEXT])[0])
    rid = new_ulid()
    backend.upsert(collection, [MemoryRecord(id=rid, text=TEXT, vector=vector,
                                             trust="user_originated",
                                             payload={"kind": "durable"})])
    emit("pass", f"{rid}\t{which}\t{backend.count(collection)}")
    return 0


def cmd_read(collection: str, rid: str) -> int:
    svc, backend, which, detail = _service(collection)
    vector = tuple(svc.embedder.embed([TEXT])[0])
    hits = backend.search(collection, vector, limit=5)
    match = [h for h in hits if h.id == rid]
    if not match:
        emit("fail", f"record {rid} not found after restart; collection holds "
                     f"{backend.count(collection)} point(s)")
        return 1
    got = match[0]
    if got.text != TEXT:
        emit("fail", f"text changed across the restart: {got.text[:60]!r}")
        return 1
    if got.trust != "user_originated":
        emit("fail", f"trust changed across the restart: {got.trust!r}")
        return 1
    emit("pass", f"{rid}\t{which}\t{backend.count(collection)}")
    return 0


def cmd_embedder() -> int:
    from lionel.memory import EmbeddingSpec

    spec = EmbeddingSpec.from_lock()
    _, which, detail = get_embedder(spec)
    if which == "fastembed":
        emit("pass", f"the pinned model is cached and loads — {detail}")
        return 0
    emit("skip", detail)
    return 1


# The semantic-recall fixture. G2's DoD, carried forward verbatim from v1.0: a dissimilar
# query retrieves the stored fact, and **keyword matching must fail it**. The overlap
# assertion below is what makes that second half real rather than assumed -- a fixture that
# happened to share a word would quietly become a keyword test.
SEMANTIC_TARGET = ("the assistant answers in Turkish when spoken to in Turkish, and in "
                   "English otherwise")
SEMANTIC_DISTRACTORS = [
    "the wake word model runs under ONNX Runtime because tflite is unsupported here",
    "the vector store is pinned by digest and runs inside Docker with a named volume",
    "every capability declares its side effect before the router will dispatch it",
]
SEMANTIC_QUERY = "which language does it reply with"
SEMANTIC_TR_QUERY = "hangi dilde cevap veriyor"


def _words(text: str) -> set:
    return {w.strip(".,:;!?").lower() for w in text.split() if w.strip(".,:;!?")}


def cmd_semantic(collection: str) -> int:
    """Store four facts, query with a phrase sharing no words, expect the right one."""
    from lionel.memory import MemoryRecord
    from lionel.memory.service import new_ulid

    svc, backend, which, detail = _service(collection)
    if which != "fastembed":
        emit("skip", f"needs the pinned model, which is not loadable: {detail}")
        return 1

    corpus = [SEMANTIC_TARGET] + SEMANTIC_DISTRACTORS
    q = _words(SEMANTIC_QUERY)
    # Zero overlap with the TARGET is the load-bearing property: any shared word and a
    # keyword search could find it, which would make this a keyword test wearing a vector
    # store. Overlap with a DISTRACTOR is different and is reported rather than refused --
    # it makes keyword matching actively wrong rather than merely empty, which is a
    # stronger demonstration of the clause, not a weaker one.
    if q & _words(SEMANTIC_TARGET):
        emit("broken", f"the query shares {sorted(q & _words(SEMANTIC_TARGET))} with the "
                       f"target; this would be a keyword test, not a semantic one")
        return 2
    lures = sorted(q & set().union(*(_words(t) for t in SEMANTIC_DISTRACTORS)))

    vectors = svc.embedder.embed(corpus)
    ids = [new_ulid() for _ in corpus]
    backend.upsert(collection, [
        MemoryRecord(id=i, text=t, vector=tuple(v), trust="user_originated",
                     payload={"kind": "durable"})
        for i, t, v in zip(ids, corpus, vectors)])

    qv = tuple(svc.embedder.embed([SEMANTIC_QUERY])[0])
    hits = backend.search(collection, qv, limit=4)
    if not hits:
        emit("fail", "the query returned nothing at all")
        return 1
    top = hits[0]
    if top.text != SEMANTIC_TARGET:
        emit("fail", f"top hit was {top.text[:60]!r}, not the language fact")
        return 1

    # The Turkish half is reported, never asserted. all-MiniLM-L6-v2 is an English model;
    # ADR-0018 chose a multilingual STT for exactly this reason and the embedding model was
    # never claimed to be one. Whichever way this goes it is a fact worth having before G6c.
    tr_top = backend.search(collection, tuple(svc.embedder.embed([SEMANTIC_TR_QUERY])[0]),
                            limit=1)
    tr = "tr:hit" if tr_top and tr_top[0].text == SEMANTIC_TARGET else "tr:miss"
    emit("pass", f"{tr}	0 words shared with the target; "
                 f"{len(lures)} shared with a distractor {lures}")
    return 0


def cmd_drop(collection: str) -> int:
    from lionel.memory import EmbeddingSpec, QdrantBackend

    b = QdrantBackend(QDRANT_URL, spec=EmbeddingSpec.from_lock())
    if b.client.collection_exists(collection):
        b.client.delete_collection(collection)
    emit("pass", f"{collection} removed")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        emit("broken", "no command given")
        return 2
    cmd, args = argv[0], argv[1:]
    table = {
        "reachable": (cmd_reachable, 0),
        "write": (cmd_write, 1),
        "read": (cmd_read, 2),
        "embedder": (cmd_embedder, 0),
        "semantic": (cmd_semantic, 1),
        "drop": (cmd_drop, 1),
    }
    if cmd not in table:
        emit("broken", f"unknown command {cmd!r}; verify_memory.sh and this file disagree")
        return 2
    fn, arity = table[cmd]
    if len(args) != arity:
        emit("broken", f"{cmd} takes {arity} argument(s), got {len(args)}")
        return 2
    try:
        return fn(*args)
    except Exception as exc:  # a broken helper is exit 2, never a silent failure
        emit("broken", f"{type(exc).__name__}: {str(exc).splitlines()[0][:160]}")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
