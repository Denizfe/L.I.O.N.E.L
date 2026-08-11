#!/usr/bin/env python3
"""PreToolUse guard: an Accepted ADR's body is append-only (ADR-0029 rule 1).

WHAT THIS PROTECTS
    ADR-0029 defines three ways to modify an Accepted ADR — Supersede, Amend, Erratum — and
    rule 1 says the original body is never edited in place. `ADR-009` checks the SHAPE of
    errata sections. Nothing checks rule 1 itself, which is the load-bearing one: an
    in-place edit destroys the evidence that a correction was needed, and makes "was this a
    correction or a reversal?" unanswerable.

WHAT IT DOES NOT PROTECT — read this before trusting it
    It sees `Edit` and `Write`. It does NOT see `sed -i` through `Bash`, an editor, or
    anything outside this session. **It is a guardrail, not a proof.** The durable fix is a
    gate that hashes each Accepted ADR's body above its first errata heading and fails on
    drift — same shape as `gate_checksum`. That is a new blocking rule and needs an ADR, so
    it is not here yet.

WHAT IS ALLOWED
    * Editing the `| Status |` row — ADR-0016 always permitted this, and it is how an ADR
      becomes Accepted or Superseded.
    * Appending anything at or below the first `## Erratum|Correction|Amendment` heading.
    * Any change to an ADR that is not Accepted.

Exit 0 allow · exit 2 block, with stderr shown to the model.
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

ADR_PATH = re.compile(r"docs[/\\]decisions[/\\]ADR-\d{4}-[a-z0-9-]+\.md$")
ERRATA_HEADING = re.compile(r"^##\s+(Erratum|Correction|Amendment)\b", re.M)
STATUS_ROW = re.compile(r"^\|\s*Status\s*\|", re.M)

BLOCK = """BLOCKED — ADR-{num} is Accepted, and its body is append-only (ADR-0029 rule 1).

You tried to edit text {where}.

An Accepted ADR's Decision is immutable and its body is never rewritten. Use one of the
three permitted operations instead:

  Erratum    the text was wrong; the decision was always what you are correcting it to.
             Append `## Erratum — {today}: short title`, QUOTING the original wording
             verbatim in a blockquote, then give the correction. The quote is what
             separates a correction from a rewrite.

  Amendment  you are adding scope and contradicting nothing.
             Append `## Amendment — {today}: short title`.

  Supersede  the decision itself changes. Write a NEW ADR; set this one's Status to
             `Superseded by ADR-NNNN` with a forward link, and leave its text alone.

The `| Status |` row is the one line you may edit in place.

See ADR-0029, and CLAUDE.md rule 3."""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never fail closed on a malformed payload; the gate is the backstop

    tool = payload.get("tool_name", "")
    if tool not in ("Edit", "Write"):
        return 0

    ti = payload.get("tool_input", {}) or {}
    path = str(ti.get("file_path", ""))
    if not ADR_PATH.search(path.replace("\\", "/")):
        return 0

    f = Path(path)
    if not f.is_file():
        return 0  # creating a new ADR

    try:
        current = f.read_text(encoding="utf-8")
    except OSError:
        return 0

    status = STATUS_ROW.search(current)
    if not status:
        return 0
    status_line = current[status.start(): current.find("\n", status.start())]
    if "accepted" not in status_line.lower():
        return 0  # Proposed / Provisional ADRs are still being written

    num = re.search(r"ADR-(\d{4})", path)
    num = num.group(1) if num else "????"
    today = payload.get("_today", "YYYY-MM-DD")
    if today == "YYYY-MM-DD":
        from datetime import date
        today = date.today().isoformat()

    # Write replaces the file wholesale — always a rewrite of the body.
    if tool == "Write":
        print(BLOCK.format(num=num, today=today,
                           where="by overwriting the whole file"), file=sys.stderr)
        return 2

    old = ti.get("old_string", "")
    if not old:
        return 0

    # The Status row may be edited in place. Everything else above the first errata
    # heading is the frozen body.
    if STATUS_ROW.search(old) and old.count("\n") <= 1:
        return 0

    idx = current.find(old)
    if idx == -1:
        return 0  # will not apply anyway; let the tool report its own error

    first_errata = ERRATA_HEADING.search(current)
    boundary = first_errata.start() if first_errata else len(current)

    if idx + len(old) <= boundary:
        print(BLOCK.format(num=num, today=today,
                           where="in the frozen body, above the first errata section"),
              file=sys.stderr)
        return 2

    if idx < boundary:
        print(BLOCK.format(num=num, today=today,
                           where="spanning the boundary between the frozen body and the "
                                 "appended sections"), file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
