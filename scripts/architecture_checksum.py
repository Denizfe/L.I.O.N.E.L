#!/usr/bin/env python3
"""Recompute the architecture checksum recorded in Architecture_Freeze.md §2.

    python3 scripts/architecture_checksum.py            # print the checksum
    python3 scripts/architecture_checksum.py --verify <sha256:...>   # exit 1 on drift

WHY THIS EXISTS
    The checksum in Architecture_Freeze.md §2 was originally computed ad hoc. A
    number nobody can recompute identifies nothing: it cannot detect drift, and it
    cannot be checked by a reviewer. This script reproduces the recorded value
    (sha256:fab0610a…) exactly, which is what makes the freeze verifiable.

THE ALGORITHM  (as described in Architecture_Freeze.md §2)
    Files are partitioned into five groups. Within a group, files are sorted by
    POSIX-relative path. The group's digest is sha256 over the concatenation of
    (path bytes ‖ file bytes) for each file, with no separator. The architecture
    checksum is sha256 over the five RAW group digests concatenated in the order
    below — raw 32-byte digests, not their hex text.

    Adding a file to any group changes that group's digest and the checksum. That
    is the point: the checksum is a fingerprint of the frozen architecture, and
    §4 of Architecture_Freeze.md names which changes are allowed to move it.

LINE ENDINGS
    Content is hashed as it sits on disk. `.gitattributes` pins every extension in
    the checksum set to `eol=lf`, so a checkout on Windows and one on Linux hash
    identically. Without that pin the same commit produces two different checksums
    on two machines — which is exactly what happened to `*.proto` before it was
    added to `.gitattributes`.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

# Windows consoles default to cp1252 and cannot encode the ellipsis below. Same
# reason as ci/gates/_lib.py — see the comment there.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]

# Order is load-bearing: the final digest concatenates group digests in this order.
GROUPS: list[tuple[str, list[str]]] = [
    ("ADRs",      ["docs/decisions/ADR-*.md"]),
    ("contracts", ["contracts/core/v1/*.schema.json",
                   "contracts/mcp/v1/*.schema.json",
                   "contracts/events/v1/*.schema.json",
                   "contracts/media/v1/*.schema.json",
                   "contracts/grpc/v1/*.proto",
                   "contracts/MANIFEST.json"]),
    ("policy",    ["config/**/*.toml", "config/*.json", "ci/policy/policy.yaml"]),
    ("artifacts", ["artifacts.lock.yaml"]),
    ("plan",      ["MASTER_PLAN_v2.md"]),
]

# Expected membership, from Architecture_Freeze.md §2. A group that has grown or
# shrunk is reported: the checksum would still compute, but silently, and a silent
# change of scope is how a freeze stops meaning anything.
EXPECTED_COUNTS = {"ADRs": 28, "contracts": 31, "policy": 8, "artifacts": 1, "plan": 1}


def collect(patterns: list[str]) -> list[Path]:
    files: set[Path] = set()
    for pattern in patterns:
        files.update(p for p in ROOT.glob(pattern) if p.is_file())
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def group_digest(files: list[Path]) -> str:
    h = hashlib.sha256()
    for f in files:
        h.update(f.relative_to(ROOT).as_posix().encode("utf-8"))
        h.update(f.read_bytes())
    return h.hexdigest()


def compute() -> tuple[str, list[tuple[str, int, str]], list[str]]:
    rows: list[tuple[str, int, str]] = []
    warnings: list[str] = []
    final = hashlib.sha256()
    total = 0
    for name, patterns in GROUPS:
        files = collect(patterns)
        digest = group_digest(files)
        rows.append((name, len(files), digest))
        final.update(bytes.fromhex(digest))
        total += len(files)
        expected = EXPECTED_COUNTS[name]
        if len(files) != expected:
            warnings.append(f"group '{name}' holds {len(files)} files; §2 records {expected}")
    if total != sum(EXPECTED_COUNTS.values()):
        warnings.append(f"{total} files hashed; §2 records {sum(EXPECTED_COUNTS.values())}")
    return final.hexdigest(), rows, warnings


def main() -> int:
    checksum, rows, warnings = compute()
    total = sum(n for _, n, _ in rows)

    print()
    print("ARCHITECTURE CHECKSUM")
    print(f"sha256:{checksum}")
    print()
    for name, count, digest in rows:
        noun = "file " if count == 1 else "files"
        print(f"  {name:<11} {count:>2} {noun}  sha256:{digest[:32]}…")
    print()
    print(f"  {total} files hashed")
    print()
    for w in warnings:
        print(f"  WARNING  {w}")
    if warnings:
        print()

    if "--verify" in sys.argv:
        try:
            expected = sys.argv[sys.argv.index("--verify") + 1]
        except IndexError:
            print("  --verify needs a checksum argument")
            return 2
        expected = expected.removeprefix("sha256:")
        if expected != checksum:
            print(f"  DRIFT  expected sha256:{expected}")
            print(f"         actual   sha256:{checksum}")
            print()
            print("  The architecture has changed since the freeze. Under")
            print("  Architecture_Freeze.md §4 this either needs an ADR, or the recorded")
            print("  checksum needs updating along with the architecture version.")
            return 1
        print("  MATCH  the architecture is unchanged since the recorded checksum")

    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
