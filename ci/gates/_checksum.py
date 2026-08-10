"""The architecture checksum: one implementation, two callers.

NOT RUNTIME CODE. Imported by `ci/gates/gate_checksum.py` and by
`scripts/architecture_checksum.py`.

WHY IT LIVES HERE RATHER THAN IN THE SCRIPT
    The script came first. When the gate was written it needed the same algorithm, and the
    obvious move — copy it — is the one this repository already warns about, in
    CI_Inventory.md §5: `scripts/verify_artifacts.sh` used to carry its own copy of the
    artifact rules, and "duplicated policy across two files is how the two quietly
    disagree, and the disagreement is discovered during an incident."

    Two copies of a *checksum* algorithm would be worse than most duplication, because
    both copies would keep producing confident hex strings while meaning different things.

THE ALGORITHM  (Architecture_Freeze.md §2)
    Files are partitioned into five groups. Within a group, files are sorted by
    POSIX-relative path. The group digest is sha256 over the concatenation of
    (path bytes ‖ file bytes) for each file, with no separator. The architecture checksum
    is sha256 over the five RAW group digests concatenated in GROUPS order — raw 32-byte
    digests, not their hex text.

LINE ENDINGS ARE PART OF THE CHECKSUM
    Content is hashed as it sits on disk. `.gitattributes` sets `* text=auto eol=lf`, so a
    checkout on Windows and one on Linux hash identically. That line is load-bearing: before
    it existed, `*.proto` was unpinned, a Windows clone got CRLF, and the same commit
    produced two different architecture checksums. `gate_checksum` exists so that failure
    mode is caught by CI rather than by an audit eight days later.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

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

FREEZE_DOC = "Architecture_Freeze.md"

# The recorded value, as it appears in the freeze document's §2 block.
_RECORDED = re.compile(r"^sha256:([0-9a-f]{64})$", re.M)


def collect(patterns: list[str], root: Path | None = None) -> list[Path]:
    base = root or ROOT
    files: set[Path] = set()
    for pattern in patterns:
        files.update(p for p in base.glob(pattern) if p.is_file())
    return sorted(files, key=lambda p: p.relative_to(base).as_posix())


def group_digest(files: list[Path], root: Path | None = None) -> str:
    base = root or ROOT
    h = hashlib.sha256()
    for f in files:
        h.update(f.relative_to(base).as_posix().encode("utf-8"))
        h.update(f.read_bytes())
    return h.hexdigest()


def compute(root: Path | None = None) -> tuple[str, list[tuple[str, int, str]]]:
    """Return (checksum, [(group, file_count, group_digest), ...])."""
    base = root or ROOT
    rows: list[tuple[str, int, str]] = []
    final = hashlib.sha256()
    for name, patterns in GROUPS:
        files = collect(patterns, base)
        digest = group_digest(files, base)
        rows.append((name, len(files), digest))
        final.update(bytes.fromhex(digest))
    return final.hexdigest(), rows


def recorded_checksum(root: Path | None = None) -> str | None:
    """The `sha256:…` line from Architecture_Freeze.md §2, or None."""
    doc = (root or ROOT) / FREEZE_DOC
    if not doc.is_file():
        return None
    m = _RECORDED.search(doc.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def recorded_counts(root: Path | None = None) -> dict[str, int]:
    """Per-group file counts as printed in the freeze document's §2 block.

    Parsed rather than hard-coded so the document stays the single source of truth for
    what the frozen architecture is *made of*. A group that silently gains or loses a file
    still produces a valid checksum — just a different one — and "the number changed" is a
    far less useful finding than "the contracts group grew by one file".
    """
    doc = (root or ROOT) / FREEZE_DOC
    if not doc.is_file():
        return {}
    out: dict[str, int] = {}
    for name, count in re.findall(r"^\s{2}(\w+)\s+(\d+)\s+files?\s+sha256:",
                                  doc.read_text(encoding="utf-8"), re.M):
        out[name] = int(count)
    return out
