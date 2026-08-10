#!/usr/bin/env python3
"""GATE: generated documents are not stale.  ADR-0030.

`CI_Inventory.md` and `Policy_Gates.md` are generated from the gates. Both ended their own
text with "Regenerate rather than hand-edit" — for months, while no generator existed and
nothing checked them.

They drifted exactly as far as you would expect. CI_Inventory claimed 16 gates against 17 on
disk and 8/8 self-test coverage against 10/10. Policy_Gates catalogued 88 rules against 127
and omitted `l0-conformance` entirely — the keystone gate, absent from the rule catalogue,
in a document whose whole purpose is to be the complete catalogue.

A stale generated document is worse than a missing one. Missing is visibly missing; stale is
confidently wrong, and it is read by exactly the people with the least context to doubt it.
"""
import subprocess
import sys

from _lib import Gate, ROOT

GENERATORS = [
    ("scripts/generate_ci_docs.py", ["CI_Inventory.md", "Policy_Gates.md"]),
]


def main():
    g = Gate("generated-docs", "Generated documents are current", ["ADR-0030", "ADR-0016"])

    for script, produces in GENERATORS:
        path = ROOT / script
        g.check()
        if not path.is_file():
            g.fail("GEN-002", f"generator `{script}` is missing",
                "Its outputs — " + ", ".join(f"`{p}`" for p in produces) + " — say they are "
                "generated. Without the generator they cannot be regenerated, cannot be "
                "checked, and become hand-maintained files carrying a note that says they are "
                "not.",
                f"Restore `{script}`, or stop describing its outputs as generated.", script)
            continue

        # --check must not write. It reports staleness through its exit code so the gate can
        # run on a read-only checkout and so CI never silently "fixes" a document instead of
        # failing on it — a pipeline that repairs the evidence stops being a pipeline.
        r = subprocess.run([sys.executable, str(path), "--check"],
                           capture_output=True, text=True, cwd=str(ROOT))
        out = ((r.stdout or "") + (r.stderr or "")).strip()

        if r.returncode == 0:
            for line in out.splitlines():
                if line.strip():
                    g.note(f"{script}: {line.strip()}")
            continue

        g.check()
        if r.returncode == 1:
            stale = [p for p in produces if p in out] or produces
            g.fail("GEN-001",
                f"stale generated document(s): {', '.join(f'`{p}`' for p in stale)}",
                "Every one of these documents tells its reader to trust it and tells its editor "
                "to regenerate it. When the two disagree, the reader loses — and this is not "
                "hypothetical: Policy_Gates.md once omitted the l0-conformance gate entirely "
                "while claiming to be the complete rule catalogue.",
                f"Run `python3 {script}` and commit the result.", script)
        else:
            g.fail("GEN-002", f"`{script} --check` exited {r.returncode}",
                "A generator that cannot run cannot verify its outputs. That is a broken tool, "
                "not a stale document, and the two need different fixes.",
                f"Run `python3 {script} --check` and fix the error.\n{out[:400]}", script)

    g.report_and_exit()


if __name__ == "__main__":
    main()
