#!/usr/bin/env python3
"""PostToolUse: say so immediately when an edit moves the architecture checksum.

Architecture_Freeze.md §2 pins a SHA-256 over 72 files. `gate_checksum` enforces it, but
only when someone runs the gates — which in practice is minutes later, or at push. Editing
one ADR and learning about it at `run_gates` turns a two-second fact ("right, that was the
ADR") into a debugging question ("why is the build red?").

This never blocks. It is a note, not a gate: the change may be entirely intended, and the
correct response is usually to finish the work and then bump the version per §5 step 7.

Reuses `ci/gates/_checksum.py` — the same implementation the gate and the script use, so
this cannot drift from them.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Windows consoles default to cp1252 and cannot encode the em-dashes below. Same reason as
# ci/gates/_lib.py — a hook that dies in its own error message is worse than no hook.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ci" / "gates"))


def normalise(path: str) -> Path | None:
    """Resolve a tool's file_path against ROOT, whatever shape it arrives in.

    Git Bash hands out MSYS paths (`/c/Users/...`), which `Path.resolve()` on Windows turns
    into `C:\\c\\Users\\...` — a real directory-looking path that is simply wrong, so
    `relative_to(ROOT)` raises and the hook returns silently. A hook that quietly does
    nothing is the failure mode this repository exists to prevent, so the MSYS form is
    handled rather than swallowed.
    """
    if not path:
        return None
    m = re.match(r"^/([a-zA-Z])/(.*)$", path)
    if m:
        path = f"{m.group(1).upper()}:/{m.group(2)}"
    try:
        p = Path(path).resolve()
    except OSError:
        return None
    if not p.is_absolute():
        p = (ROOT / path).resolve()
    return p


def in_checksum_set(target: Path) -> bool:
    from _checksum import GROUPS, collect
    for _name, patterns in GROUPS:
        if any(p.resolve() == target for p in collect(patterns)):
            return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    target = normalise(str((payload.get("tool_input") or {}).get("file_path", "")))
    if target is None:
        return 0

    try:
        if not in_checksum_set(target):
            return 0
        rel = target.relative_to(ROOT).as_posix()
        from _checksum import compute, recorded_checksum
        actual, _rows = compute()
        recorded = recorded_checksum()
    except Exception:
        return 0

    if recorded is None or actual == recorded:
        return 0

    print(
        f"`{rel}` is in the architecture checksum set, and the checksum has moved:\n"
        f"  recorded  sha256:{recorded[:16]}…  (Architecture_Freeze.md §2)\n"
        f"  computed  sha256:{actual[:16]}…\n"
        f"`gate_checksum` will fail until §2 is updated. Under Architecture_Freeze.md §4 an\n"
        f"architecture change needs an ADR; §5 step 7 requires recomputing the checksum and\n"
        f"bumping the architecture version. Record §2 LAST — the freeze document is not\n"
        f"itself in the set, so writing the new value does not move it again.",
        file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
