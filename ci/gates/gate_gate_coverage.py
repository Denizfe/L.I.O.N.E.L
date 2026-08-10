#!/usr/bin/env python3
"""GATE: every gate has rejected something.  ADR-0030.

CI_Architecture.md §7 lists seven steps for adding a gate. Step 6 is "Add a planted
violation to ci/self_test.sh", and the document says of it:

    "Step 6 is the one that gets skipped and the one that matters."

It was right, and it was skipped. At the Phase 0 freeze the self-test covered 9 of 17
gates — including, until Finding M1 was closed, none of `l0-conformance`: eight invariants,
24 rules and a network egress guard, with no standing proof that any of it could reject
anything.

WHY A COUNTER IS NOT COVERAGE
    "10/10 planted violations caught" reads like a coverage figure and is not one. It counts
    assertions, not gates. A suite can add its tenth assertion to a gate that already had
    three while another gate has never rejected anything, and the headline number goes up.
    This gate counts gates.

HOW COVERAGE IS DECLARED
    `expect_violation <gate> …` — the normal path, parsed directly.
    `# selftest-covers: <gate> — reason` — for assertions built by hand rather than through
    the helper, which some gates need (gate_secrets is pointed at a temp tree outside the
    repository so that no matching credential literal has to exist in it).

    The pragma is explicit on purpose. Inferring coverage from "the script mentions this
    gate somewhere" would let a comment count as a test, which is the failure this gate
    exists to prevent.
"""
import re
import sys
from pathlib import Path

from _lib import Gate, ROOT, load_policy, read_text

RUNNER = "ci/run_gates.sh"
SUITE = "ci/self_test.sh"

# `--suite <path>` points the gate at a different suite file. This exists so the self-test
# can prove the gate bites: it copies ci/self_test.sh, deletes one assertion from the copy,
# and checks COV-001 fires. Editing the real suite in place would be editing the script
# that is currently executing — bash reads it incrementally, so the plant could change the
# behaviour of the test doing the planting. Same escape hatch, same reason, as
# gate_secrets' `--root`.
_suite_override: Path | None = None
if "--suite" in sys.argv:
    _suite_override = Path(sys.argv[sys.argv.index("--suite") + 1]).resolve()


def suite_path() -> Path:
    return _suite_override or (ROOT / SUITE)


def gates_in_order() -> list[str]:
    m = re.search(r"ORDER=\((.*?)\)", read_text(ROOT / RUNNER), re.S)
    # Strip shell comments: bash permits them inside an array literal, and a parser that
    # returns "#" as a gate name produces a confident, wrong answer.
    raw = m.group(1) if m else ""
    return [w for w in re.sub(r"#.*", " ", raw).split() if w]


def gates_covered() -> tuple[set[str], set[str]]:
    text = read_text(suite_path())
    helper = set(re.findall(r"^\s*expect_violation\s+([a-z0-9-]+)", text, re.M))
    pragma = set(re.findall(r"#\s*selftest-covers:\s*([a-z0-9-]+)", text))
    return helper, pragma


def main():
    g = Gate("gate-coverage", "Every gate has rejected something", ["ADR-0030", "ADR-0016"])
    cfg = load_policy().get("coverage", {}) or {}
    exempt = {e["gate"]: e for e in cfg.get("exempt", []) or []}

    order = gates_in_order()
    g.check()
    if not order:
        from _lib import gate_error
        gate_error(f"could not read ORDER from {RUNNER}")

    helper, pragma = gates_covered()
    covered = helper | pragma
    where = suite_path()
    if _suite_override:
        g.note(f"reading coverage from {where} (--suite override)")

    for name in order:
        g.check()
        if name in covered:
            continue
        if name in exempt:
            e = exempt[name]
            g.note(f"{name}: no planted violation, exempt — owner `{e.get('owner')}`, "
                   f"covered by {e.get('unblocked_by')} ({e.get('why')})")
            continue
        g.fail("COV-001", f"gate `{name}` has no planted violation in {SUITE}",
            "CI_Architecture.md §7 step 6: a gate that has never rejected anything is "
            "unproven. It may be checking the wrong path, matching nothing, or silently "
            "passing on an exception — and every run it makes will be green either way. Two "
            "gates in this repository had real bugs that only the self-test surfaced.",
            f"Plant a violation the gate must catch and assert it with "
            f"`expect_violation {name} \"<RULE-ID>\" \"<what it plants>\"`. If it genuinely "
            f"cannot be tested yet, register it under `coverage.exempt` in ci/policy/policy.yaml "
            f"with an owner and the gate that removes the exemption.", SUITE)

    # The escape hatch gets policed exactly as todo.registry and licenses.unresolved_registry
    # are. An exemption mechanism nobody checks becomes the loophole, which is the usual way
    # this pattern dies.
    for name, e in exempt.items():
        g.check()
        if name not in order:
            g.fail("COV-003", f"`coverage.exempt` names `{name}`, which is not a gate",
                "An exemption for something that does not exist is dead policy. It survives "
                "reviews because it costs nothing to keep, and it teaches the next reader that "
                "the list is decorative.",
                f"Remove the entry, or correct the name to one of: {', '.join(order)}.",
                "ci/policy/policy.yaml")
            continue

        if name in covered:
            g.fail("COV-003", f"gate `{name}` is exempted but IS covered by {SUITE}",
                "A stale exemption is worse than a missing test: it says the gate cannot be "
                "proven while the proof sits in the suite, so the next person to look removes "
                "the test rather than the exemption.",
                f"Delete the `{name}` entry from `coverage.exempt` in ci/policy/policy.yaml.",
                "ci/policy/policy.yaml")
            continue

        for field in ("owner", "unblocked_by", "why"):
            g.check()
            if not e.get(field):
                g.fail("COV-002", f"coverage exemption `{name}` has no `{field}`",
                    "An exemption with no owner and no route to removal is not an exemption, "
                    "it is a silently lowered standard.",
                    "Add `owner`, `unblocked_by` and `why` in ci/policy/policy.yaml.",
                    "ci/policy/policy.yaml")

    proven = len([n for n in order if n in covered])
    g.note(f"gate coverage: {proven}/{len(order)} gates have rejected a planted violation")
    if pragma:
        g.note("declared by pragma rather than expect_violation: " + ", ".join(sorted(pragma)))
    if exempt:
        g.note(f"{len(exempt)} registered exemption(s)")

    g.report_and_exit()


if __name__ == "__main__":
    main()
