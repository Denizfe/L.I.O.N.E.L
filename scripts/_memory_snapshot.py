"""Helper for `scripts/memory_backup.sh`. Prints TSV, never prose.

Split from the shell driver for the same reason `_memory_live.py` is: two quoting regimes
must never fight over the same backslashes, and this one additionally speaks multipart
HTTP, which is not something to assemble in Bash.

Commands
    collections                       the configured collections that exist, and their sizes
    sha256   <file>                   digest and size of a file, with the container down
    create   <collection> <outdir>    snapshot -> download -> delete the server-side copy
    restore  <collection> <file>      upload a .snapshot and make it the collection
    points   <collection>             how many points a collection holds
    digest   <collection>             sha256 over its sorted point ids -- what a restore must match
    drop     <collection>             remove a collection (used by the round-trip self-test)

WHY THE SERVER-SIDE SNAPSHOT IS DELETED AFTER DOWNLOAD
    Qdrant writes snapshots inside `/qdrant/snapshots`, which lives in the same named
    volume as the data. A backup that only exists there is not a backup: the single
    `docker compose down -v` this whole script exists to survive takes both. So the copy
    that matters is the one on the host, and the server-side one is removed as soon as the
    host copy is checksummed -- otherwise the volume grows by a full copy of memory on
    every run, silently, until the disk says something about it.

EXIT CODES ARE THE SAME CONTRACT AS EVERYWHERE ELSE
    0 pass · 1 the thing being checked failed · 2 this script is broken.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

for _stream in (sys.stdout, sys.stderr):
    try:
        # newline="" or Python translates \n to os.linesep and welds a CR onto every
        # field, which `read -r` then keeps. Architecture_Freeze.md §9.11 records the day
        # that cost.
        _stream.reconfigure(encoding="utf-8", errors="replace", newline="")
    except (AttributeError, ValueError):
        pass

QDRANT_URL = "http://127.0.0.1:6333"
TIMEOUT = 300  # a snapshot of a large collection is not a fast request


def emit(verdict: str, *fields: object) -> None:
    sys.stdout.write("\t".join([verdict, *(str(f) for f in fields)]) + "\n")


def client():
    from lionel.memory import EmbeddingSpec, QdrantBackend
    return QdrantBackend(QDRANT_URL, spec=EmbeddingSpec.from_lock()).client


def brief(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {str(exc).splitlines()[0][:160]}"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# -- commands --------------------------------------------------------------------------

def cmd_collections() -> int:
    from lionel.memory.service import MemoryConfig
    cfg = MemoryConfig.from_toml()
    try:
        c = client()
        existing = {x.name for x in c.get_collections().collections}
    except Exception as exc:
        emit("fail", brief(exc))
        return 1
    for name in (cfg.durable_collection, cfg.episodic_collection):
        if name in existing:
            emit("pass", name, c.count(name, exact=True).count)
        else:
            emit("skip", name, "collection does not exist yet")
    return 0


def cmd_sha256(path: str) -> int:
    """No Qdrant, no imports from `lionel`. `list` re-computes rather than reading the
    sidecar back at itself, and it must work with the container down."""
    p = Path(path)
    if not p.is_file():
        emit("fail", f"{p} is not a file")
        return 1
    emit("pass", sha256_of(p), p.stat().st_size)
    return 0


def cmd_points(collection: str) -> int:
    try:
        emit("pass", client().count(collection, exact=True).count)
    except Exception as exc:
        emit("fail", brief(exc))
        return 1
    return 0


def cmd_digest(collection: str) -> int:
    """A sha256 over every point id in the collection, sorted.

    `selftest` compared point COUNTS before this existed, and a count is the one property
    a restore of the wrong snapshot is most likely to share. The ids are the cheapest
    thing that actually identifies the contents: they are ULIDs translated to UUIDs by
    `QdrantBackend`, so two collections with the same digest hold the same records.
    """
    ids: list[str] = []
    try:
        c = client()
        offset = None
        while True:
            points, offset = c.scroll(collection, limit=1000, offset=offset,
                                      with_payload=False, with_vectors=False)
            ids.extend(str(p.id) for p in points)
            if offset is None:
                break
    except Exception as exc:
        emit("fail", brief(exc))
        return 1
    h = hashlib.sha256()
    for i in sorted(ids):
        h.update(i.encode("utf-8"))
        h.update(b"\n")
    emit("pass", h.hexdigest(), len(ids))
    return 0


def cmd_drop(collection: str) -> int:
    try:
        client().delete_collection(collection)
    except Exception as exc:
        emit("fail", brief(exc))
        return 1
    emit("pass", collection)
    return 0


def cmd_create(collection: str, outdir: str) -> int:
    try:
        c = client()
        points = c.count(collection, exact=True).count
        desc = c.create_snapshot(collection_name=collection, wait=True)
    except Exception as exc:
        emit("fail", brief(exc))
        return 1
    if desc is None or not getattr(desc, "name", None):
        emit("fail", "Qdrant accepted the request and named no snapshot")
        return 1

    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    target = out / desc.name
    url = f"{QDRANT_URL}/collections/{collection}/snapshots/{desc.name}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
            # Written to a .part and renamed, so an interrupted download can never be
            # mistaken for a backup by `list` or by a later restore.
            part = target.with_suffix(target.suffix + ".part")
            with part.open("wb") as fh:
                for chunk in iter(lambda: resp.read(1 << 20), b""):
                    fh.write(chunk)
            part.replace(target)
    except (urllib.error.URLError, OSError) as exc:
        emit("fail", brief(exc))
        return 1
    finally:
        # Best effort, and deliberately not fatal: a downloaded backup with a stale
        # server-side copy beside it is a wasted gigabyte, not a lost backup.
        try:
            c.delete_snapshot(collection_name=collection, snapshot_name=desc.name, wait=True)
        except Exception:
            pass

    digest = sha256_of(target)
    with target.with_suffix(target.suffix + ".sha256").open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{digest}  {target.name}\n")
    emit("pass", target.as_posix(), digest, target.stat().st_size, points)
    return 0


def cmd_restore(collection: str, path: str) -> int:
    src = Path(path)
    if not src.is_file():
        emit("fail", f"{src} is not a file")
        return 1

    sidecar = src.with_suffix(src.suffix + ".sha256")
    if sidecar.is_file():
        recorded = sidecar.read_text(encoding="utf-8").split()[0]
        actual = sha256_of(src)
        if recorded != actual:
            # Refuse rather than warn. Restoring a corrupt snapshot over a live collection
            # turns one lost copy into two.
            emit("fail", f"checksum mismatch: recorded {recorded[:12]}, file is {actual[:12]}")
            return 1
    else:
        emit("note", f"no .sha256 beside {src.name}; restoring unverified")

    boundary = uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="snapshot"; filename="{src.name}"\r\n'.encode(),
        b"Content-Type: application/octet-stream\r\n\r\n",
        src.read_bytes(),
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    url = f"{QDRANT_URL}/collections/{collection}/snapshots/upload?priority=snapshot"
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace").splitlines()
        emit("fail", f"HTTP {exc.code}: {(detail[0] if detail else '')[:160]}")
        return 1
    except (urllib.error.URLError, OSError, ValueError) as exc:
        emit("fail", brief(exc))
        return 1
    if payload.get("result") is not True:
        emit("fail", f"Qdrant did not confirm the recovery: {json.dumps(payload)[:160]}")
        return 1

    try:
        emit("pass", client().count(collection, exact=True).count)
    except Exception as exc:
        emit("fail", f"restored, then could not be counted -- {brief(exc)}")
        return 1
    return 0


COMMANDS = {
    "collections": (cmd_collections, 0),
    "points": (cmd_points, 1),
    "sha256": (cmd_sha256, 1),
    "digest": (cmd_digest, 1),
    "drop": (cmd_drop, 1),
    "create": (cmd_create, 2),
    "restore": (cmd_restore, 2),
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in COMMANDS:
        emit("broken", f"usage: {' | '.join(COMMANDS)}")
        return 2
    fn, arity = COMMANDS[argv[0]]
    args = argv[1:]
    if len(args) != arity:
        emit("broken", f"{argv[0]} takes {arity} argument(s), got {len(args)}")
        return 2
    try:
        return fn(*args)
    except ImportError as exc:
        emit("broken", f"{brief(exc)} -- is the virtualenv active? ADR-0036 declares qdrant-client")
        return 2
    except Exception as exc:
        emit("broken", brief(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
