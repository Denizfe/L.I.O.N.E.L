#!/usr/bin/env python3
"""GATE: architecture checksum.  ADR-0030.

Architecture_Freeze.md §2 records a checksum over the architecture-defining file set, and
§7 criterion 5 makes "checksum recorded against the commit SHA" a Phase-entry criterion.
Neither was checked by anything until this gate existed.

WHAT IT ACTUALLY PROTECTS
    Not "did someone edit an ADR" — git already answers that, better. It protects the claim
    the freeze document makes about ITSELF: that the recorded number is a property of the
    commit, reproducible by anyone who clones it.

    That claim was false for eight days. `.gitattributes` pinned `eol=lf` for seven
    extensions but not `.proto`, so a Windows clone checked three files out as CRLF and
    computed a different checksum from the same commit. Every gate passed. The audit passed.
    The defect was invisible because nothing recomputed the number anywhere other than where
    it was first computed — which is exactly what CI is for.
"""
from _checksum import GROUPS, collect, compute, recorded_checksum, recorded_counts, FREEZE_DOC
from _lib import Gate


def main():
    g = Gate("checksum", "Architecture checksum", ["ADR-0030", "ADR-0013"])

    recorded = recorded_checksum()
    g.check()
    if recorded is None:
        g.fail("CHECKSUM-002", f"no `sha256:` value recorded in `{FREEZE_DOC}` §2",
            "Architecture_Freeze.md §2 asserts a deterministic checksum over the architecture. "
            "An assertion with no value to compare against is unfalsifiable, and an "
            "unfalsifiable claim in a freeze document is worse than no claim: it is trusted.",
            f"Run `python3 scripts/architecture_checksum.py` and record the value in {FREEZE_DOC} §2.")
        g.report_and_exit()

    actual, rows = compute()

    # Membership before value. If a group has gained or lost a file, "the checksum changed"
    # is technically true and practically useless — the actionable finding is which group
    # changed shape, and that is also the failure a reviewer cannot spot in a hex diff.
    expected_counts = recorded_counts()
    for name, count, _digest in rows:
        want = expected_counts.get(name)
        if want is None:
            continue
        g.check()
        if count != want:
            verb = "gained" if count > want else "lost"
            g.fail("CHECKSUM-003",
                f"architecture group `{name}` {verb} files: {count} on disk, §2 records {want}",
                "The checksum set defines what IS the architecture. A file entering or leaving "
                "it changes the frozen scope, which Architecture_Freeze.md §4 says requires an "
                "ADR — not merely a recomputed number.",
                f"If the change is intended, write the ADR, then update {FREEZE_DOC} §2 and bump "
                "the architecture version (§5 step 7).", FREEZE_DOC)

    g.check()
    if actual != recorded:
        g.fail("CHECKSUM-001", f"architecture checksum drift: recorded `{recorded[:16]}…`, "
                               f"computed `{actual[:16]}…`",
            "Architecture_Freeze.md §2's checksum is the freeze's only mechanical claim about "
            "itself, and §7 criterion 5 makes it a Phase-entry criterion. If it does not "
            "reproduce, the architecture in the repository is not the architecture that was "
            "frozen — and nobody can tell which parts differ without recomputing by hand.",
            "Either revert the change to the architecture-defining set, or — if the change is "
            f"intended and carries an ADR — update {FREEZE_DOC} §2 and bump the architecture "
            "version. `python3 scripts/architecture_checksum.py` prints the new value.",
            FREEZE_DOC)
    else:
        g.note(f"checksum reproduces: sha256:{actual[:32]}…")

    total = sum(n for _, n, _ in rows)
    g.note(f"{total} files across {len(GROUPS)} groups: "
           + " · ".join(f"{n} {c}" for n, c, _ in rows))
    # Content is hashed as it sits on disk, so line-ending normalisation is part of the
    # result. Said out loud on every run because it is the one property of this gate that
    # is invisible until it breaks, and it broke once already.
    g.note("line endings are part of the checksum — `.gitattributes` must keep `eol=lf`")

    g.report_and_exit()


if __name__ == "__main__":
    main()
