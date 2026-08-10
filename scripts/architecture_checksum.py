#!/usr/bin/env python3
"""Recompute the architecture checksum recorded in Architecture_Freeze.md §2.

    python3 scripts/architecture_checksum.py            # print the checksum
    python3 scripts/architecture_checksum.py --verify   # compare against the freeze doc
    python3 scripts/architecture_checksum.py --verify sha256:<value>   # against a literal

    Exit 0 match / nothing to compare · 1 drift or group-membership change.

WHY THIS EXISTS
    The checksum in Architecture_Freeze.md §2 was originally computed ad hoc. A number
    nobody can recompute identifies nothing: it cannot detect drift, and it cannot be
    checked by a reviewer.

    This is the human-facing entry point. `ci/gates/gate_checksum.py` is the enforcing one,
    and both call the same implementation in `ci/gates/_checksum.py` — see the note there
    about why the algorithm does not live in this file.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ci" / "gates"))

from _checksum import GROUPS, collect, compute, recorded_checksum, recorded_counts  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def main() -> int:
    checksum, rows = compute()
    expected_counts = recorded_counts()
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

    drift = []
    for name, count, _ in rows:
        want = expected_counts.get(name)
        if want is not None and want != count:
            drift.append(f"group '{name}' holds {count} files; Architecture_Freeze.md §2 records {want}")
    for line in drift:
        print(f"  MEMBERSHIP  {line}")
    if drift:
        print()

    if "--verify" not in sys.argv:
        return 1 if drift else 0

    i = sys.argv.index("--verify")
    expected = sys.argv[i + 1] if len(sys.argv) > i + 1 else None
    if expected is None:
        expected = recorded_checksum()
        if expected is None:
            print("  no sha256: line found in Architecture_Freeze.md — nothing to verify against")
            return 1
    expected = expected.removeprefix("sha256:")

    if expected != checksum:
        print(f"  DRIFT  expected sha256:{expected}")
        print(f"         actual   sha256:{checksum}")
        print()
        print("  The architecture has changed since the recorded checksum. Under")
        print("  Architecture_Freeze.md §4 this either needs an ADR, or the recorded checksum")
        print("  needs updating along with the architecture version (§5 step 7).")
        return 1

    print("  MATCH  the architecture is unchanged since the recorded checksum")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
