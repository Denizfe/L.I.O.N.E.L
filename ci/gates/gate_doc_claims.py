#!/usr/bin/env python3
"""GATE: the counts this repository states about itself are true.  ADR-0030.

THE GAP THIS CLOSES
    ADR-0030 says every invariant this repository records about itself must have a gate.
    `generated-docs` delivers half of that: it covers `CI_Inventory.md` and
    `Policy_Gates.md`, because those have a generator. Everything else asserting a count is
    hand-written prose, and ADR-0030's own Costs section records the remainder as open.

    It is not theoretical, and it is not rare. Preparing architecture 1.4.0 turned up four
    stale claims in one session:

        Architecture_Freeze.md §3   "Self-test 21/21"   — had been 22/22 since 1.2.0
        Architecture_Freeze.md §3   "16 sections"       — policy.yaml had 15
        CI_Inventory / Policy_Gates "23/23"             — the run reported 24/24
        CLAUDE.md                   "# 20/20, 0 broken" — under a heading reading
                                                          "Verify before you claim anything"

    Each was found by a human reading carefully at the one moment they were least likely
    to. That is not a control.

WHY A REGISTRY RATHER THAN A SWEEP
    Most numbers in this repository are supposed to be stale. `Architecture_Freeze.md` §9.x,
    `Phase0_Final_Signoff.md`'s evidence tables and the superseded-checksum block are dated
    records, and this project appends corrections rather than rewriting history on purpose.
    A gate that flagged those would be arguing with the archive.

    So the registry names WHERE current-state claims live; the gate measures WHETHER they
    are true. Adding a claim is a one-line policy diff. The numbers can never go stale
    again, because no number in a checked region is written by hand — it is compared to
    the pipeline on every run.

WHAT IT STILL DOES NOT COVER
    A claim in a document nobody registered. `doc_claims.out_of_scope` names the documents
    left out and why, each with an owner, so the remaining gap is written down rather than
    implied. `Phase1_Entry_Checklist.md` and `Phase0_Final_Signoff.md` are there: both
    interleave current claims with dated records line by line, and separating them needs
    document surgery, not a gate. The `doc-claim-auditor` agent still earns its keep.
"""
import re
import sys
from pathlib import Path

from _lib import Gate, ROOT, gate_error, load_policy, read_text

# The rule catalogue is collected by scripts/generate_ci_docs.py. Importing it is the
# _checksum.py precedent: a second implementation of "how many rules are there" would keep
# producing a confident number while meaning something slightly different, and the
# disagreement would surface as one document contradicting another.
sys.path.insert(0, str(ROOT / "scripts"))


_STATUS = re.compile(r"^\|\s*Status\s*\|\s*(.+?)\s*\|", re.M)


def _pending_adrs() -> int:
    """ADRs whose Status row says Proposed.

    Same notion of "status" gate_adr uses -- the first `| Status | ... |` row. Two
    implementations of "which ADRs are pending" would drift, and the whole point of this
    fact is that it cannot.
    """
    n = 0
    for f in sorted((ROOT / "docs" / "decisions").glob("ADR-*.md")):
        m = _STATUS.search(read_text(f))
        if m and "proposed" in m.group(1).lower():
            n += 1
    return n


def measure() -> dict[str, int]:
    """Ground truth, measured every run. Nothing here reads a document."""
    try:
        import generate_ci_docs as gen
    except Exception as e:  # pragma: no cover - environment problem, not a repo problem
        gate_error("could not import scripts/generate_ci_docs.py", str(e))

    try:
        names = gen.gate_order()
        extra = gen.policy_ids()
        parsed = [gen.parse_gate(n, extra.get(n, set())) for n in names]
        # Totalled per gate, exactly as generate_ci_docs.main() does. A rule id shared by
        # two gates counts twice, because it is two rules being enforced — and because a
        # second definition of "how many rules" would put this gate and the generated
        # documents into permanent, confident disagreement.
        facts = {
            "gates": len(names),
            "rules": sum(len(g["ids"]) for g in parsed),
            "jobs": len(gen.workflow_jobs()),
            "assertions": len(gen.selftest_cases()),
            "adrs": len(sorted((ROOT / "docs" / "decisions").glob("ADR-*.md"))),
            # Top-level keys in policy.yaml. Added at 1.7.0 because the claim
            # "16 configuration sections" in Architecture_Freeze.md §3 was wrong by
            # two on the day it was written and had drifted to four by the time
            # anyone counted — inside the very section this gate already watches,
            # for want of a pattern that matched the sentence.
            "policy_sections": len(load_policy()),
            # Added 2026-08-28. `| **Architecture decisions** | 35 ADRs ... 1 pending:
            # ADR-0035 |` sat in this gate's own registered region for three tags after
            # ADR-0035 was accepted. The gate read `35 ADRs`, found it true, and walked
            # past `1 pending` in the same sentence -- count-shaped claims were measured
            # and a status claim beside them was not. The status is as measurable as the
            # count; it just had no pattern.
            "pending_adrs": _pending_adrs(),
        }
    except Exception as e:
        gate_error("scripts/generate_ci_docs.py changed shape", f"{type(e).__name__}: {e}")
    return facts


def region_of(text: str, heading: str | None) -> tuple[str, int] | None:
    """The lines under `heading`, up to the next heading of the same or higher level.

    `None` means the whole document. Returns (text, line offset) or None if the heading is
    not there — which is itself a finding: a registry entry pointing at a section someone
    renamed checks nothing and reports success.
    """
    if heading is None:
        return text, 0
    lines = text.split("\n")
    level = len(heading) - len(heading.lstrip("#"))
    for i, line in enumerate(lines):
        if line.strip() != heading.strip():
            continue
        for j in range(i + 1, len(lines)):
            s = lines[j]
            if s.startswith("#") and (len(s) - len(s.lstrip("#"))) <= level:
                return "\n".join(lines[i:j]), i
        return "\n".join(lines[i:]), i
    return None


def main():
    p = load_policy()
    g = Gate("doc-claims", "Hand-written counts match what the pipeline reports",
             ["ADR-0030", "ADR-0016"])
    cfg = p.get("doc_claims", {}) or {}
    facts = measure()

    patterns = []
    for spec in cfg.get("patterns", []) or []:
        g.check()
        fact = spec.get("fact")
        if fact not in facts:
            g.fail("CLAIM-002", f"claim pattern `{spec.get('id')}` measures `{fact}`, "
                                f"which this gate does not know how to measure",
                "A pattern pointing at a fact with no measurement behind it silently checks "
                "nothing, and the registry reads as though it does.",
                f"Use one of: {', '.join(sorted(facts))}. Add a new measurement to "
                "`measure()` in ci/gates/gate_doc_claims.py if the fact is real.",
                "ci/policy/policy.yaml")
            continue
        patterns.append((spec["id"], re.compile(spec["regex"]), fact))

    if not patterns:
        gate_error("no usable claim patterns in `doc_claims.patterns`",
                   "A gate with nothing to match passes everything.")

    for entry in cfg.get("documents", []) or []:
        doc = entry["doc"]
        f = ROOT / doc
        g.check()
        if not f.is_file():
            g.fail("CLAIM-002", f"`doc_claims` registers `{doc}`, which does not exist",
                "A registry entry pointing at a missing document checks nothing and reports "
                "success. That is worse than not registering it: the list says the document "
                "is covered.",
                "Remove the entry, or correct the path.", "ci/policy/policy.yaml")
            continue

        text = read_text(f)
        heading = entry.get("region")
        got = region_of(text, heading)
        g.check()
        if got is None:
            g.fail("CLAIM-002", f"`{doc}` has no section `{heading}`",
                "The section was renamed or removed, so this entry now checks an empty "
                "region and the gate goes green on a document nobody is checking.",
                f"Update `region` in ci/policy/policy.yaml to the current heading in {doc}, "
                "or drop the entry.", "ci/policy/policy.yaml")
            continue
        region, offset = got

        historical = entry.get("historical", []) or []
        for h in historical:
            g.check()
            for field in ("line", "why", "owner"):
                if not h.get(field):
                    g.fail("CLAIM-003", f"historical exclusion in `{doc}` has no `{field}`",
                        "Every exemption in this repository carries an owner and a reason. "
                        "One with neither is not an exemption; it is a silently lowered "
                        "standard.",
                        "Add `line`, `why` and `owner`.", "ci/policy/policy.yaml")
                    break
            else:
                if h["line"] not in region:
                    g.fail("CLAIM-003",
                        f"historical exclusion for `{doc}` matches nothing: `{h['line'][:60]}…`",
                        "A stale exclusion survives review because it costs nothing to keep, "
                        "and it teaches the next reader that the list is decorative. It also "
                        "hides the fact that the sentence it protected is gone.",
                        "Remove the entry, or correct the quoted text.", "ci/policy/policy.yaml")

        excluded = [h["line"] for h in historical if h.get("line")]

        for lineno, line in enumerate(region.split("\n"), start=offset + 1):
            if any(x in line for x in excluded):
                continue
            for pid, rx, fact in patterns:
                for m in rx.finditer(line):
                    g.check()
                    want = facts[fact]
                    claimed = [int(x) for x in m.groups() if x and x.isdigit()]
                    if all(c == want for c in claimed):
                        continue
                    g.fail("CLAIM-001",
                        f"`{doc}` claims `{m.group(0).strip()}`; the pipeline reports "
                        f"{fact} = {want}",
                        "ADR-0030: an invariant this repository records about itself must "
                        "have a gate. A stale count is harmless on its own — but a document "
                        "that is wrong about something checkable teaches readers not to "
                        "trust the ones that are not checkable, and those are the ones "
                        "carrying the architecture.",
                        f"Correct the number to {want}. If the line is a dated record rather "
                        f"than a current claim, register it under this document's "
                        f"`historical` list with a `why` and an `owner`.", doc, lineno)

    for entry in cfg.get("out_of_scope", []) or []:
        g.check()
        missing = [k for k in ("doc", "why", "owner", "unblocked_by") if not entry.get(k)]
        if missing:
            g.fail("CLAIM-003",
                f"`doc_claims.out_of_scope` entry is missing {', '.join(missing)}",
                "A document left out of a check needs a reason and someone answerable for "
                "it, or the list becomes the place claims go to stop being checked.",
                "Add `doc`, `why`, `owner` and `unblocked_by`.", "ci/policy/policy.yaml")
            continue
        if not (ROOT / entry["doc"]).is_file():
            g.fail("CLAIM-003",
                f"`out_of_scope` names `{entry['doc']}`, which does not exist",
                "An exclusion for something that is not there is dead policy.",
                "Remove the entry.", "ci/policy/policy.yaml")

    g.note("measured: " + " · ".join(f"{k} {v}" for k, v in sorted(facts.items())))
    checked = len(cfg.get("documents", []) or [])
    skipped = cfg.get("out_of_scope", []) or []
    g.note(f"{checked} document region(s) checked against measurement")
    for e in skipped:
        g.note(f"out of scope: {e.get('doc')} — owner `{e.get('owner')}`, "
               f"unblocked by {e.get('unblocked_by')} ({e.get('why')})")

    g.report_and_exit()


if __name__ == "__main__":
    main()
