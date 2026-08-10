#!/usr/bin/env python3
"""GATE: ADR validation.  ADR-0016, ADR-0029."""
import re
from _lib import Gate, load_policy, ROOT, rel, read_text

# ADR-0029. An Accepted ADR's Decision is immutable; three append-only operations may modify
# the document. `## Erratum — 2026-08-02: optional trailing title`, and the parenthesised
# form ADR-0003 used before the convention settled.
_ERRATA_HEADING = re.compile(
    r"^##\s+(?P<kind>Erratum|Correction|Amendment)\b(?P<rest>.*)$", re.M)
_ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def check_errata(g, cfg, num, txt, r):
    """ADR-009 — shape of Erratum / Correction / Amendment sections.

    Shape only, and deliberately so. ADR-0029 rule 3 — an Erratum may not change what is
    permitted — is the rule that actually matters and the one no gate can evaluate. Checking
    the date and the verbatim quote catches the mechanical half; a reviewer still has to
    judge whether a correction is a correction. A gate that implied otherwise would give
    false assurance about exactly the operation ADR-0029 calls most open to abuse.
    """
    kinds = set(cfg.get("errata_sections", []))
    quote_from = str(cfg.get("errata_quote_required_from", "9999-12-31"))

    matches = list(_ERRATA_HEADING.finditer(txt))
    for i, m in enumerate(matches):
        kind = m.group("kind")
        if kind not in kinds:
            continue
        g.check()
        date = _ISO_DATE.search(m.group("rest"))
        if not date:
            g.fail("ADR-009", f"`## {kind}` in ADR-{num} carries no ISO date",
                "ADR-0029 rule 4: an undated correction cannot be ordered against the decision "
                "it corrects, so a reader cannot tell whether it applied when the thing they "
                "are investigating happened.",
                f"Write `## {kind} — YYYY-MM-DD: short title`.", r)
            continue

        # Rule 2 applies only to corrections — an Amendment adds scope and has no original
        # wording to quote.
        if kind == "Amendment" or date.group(0) < quote_from:
            if kind != "Amendment" and date.group(0) < quote_from:
                g.note(f"ADR-{num} `{kind} — {date.group(0)}` predates ADR-0029 "
                       f"({quote_from}); rule 2's verbatim quote is not enforced against it "
                       "and cannot be added — rule 1 forbids editing the body")
            continue

        body = txt[m.end(): matches[i + 1].start() if i + 1 < len(matches) else len(txt)]
        g.check()
        if not re.search(r"^\s*>", body, re.M):
            g.fail("ADR-009", f"`## {kind} — {date.group(0)}` in ADR-{num} quotes nothing",
                "ADR-0029 rule 2: an Erratum must quote verbatim the wording it corrects. The "
                "quote is what separates 'the text was wrong' from 'the decision changed' — "
                "without it, a reader cannot tell a correction from a rewrite, and the "
                "distinction is the whole mechanism.",
                "Add a blockquote of the original wording before giving the correction.", r)

def main():
    p = load_policy(); g = Gate("adr", "ADR validation", ["ADR-0016", "ADR-0029"])
    cfg = p["adr"]
    d = ROOT / cfg["dir"]
    if not d.is_dir():
        from _lib import gate_error
        gate_error(f"ADR directory missing: {cfg['dir']}")

    files = sorted(d.glob("ADR-*.md"))
    ids = {}
    for f in files:
        m = re.match(r"ADR-(\d{4})-", f.name)
        if not m:
            g.check(); g.fail("ADR-005", f"malformed ADR filename `{f.name}`",
                "ADR-0016 requires ADR-NNNN-kebab-title.md so the set sorts and greps predictably.",
                "Rename to `ADR-NNNN-short-title.md`.", rel(f))
            continue
        ids[m.group(1)] = f

    g.check()
    if len(files) != cfg["expected_count"]:
        g.fail("ADR-001", f"expected {cfg['expected_count']} ADRs, found {len(files)}",
            "The ADR count is declared in policy so an accidental deletion, or an addition that "
            "skipped review, shows up as a failing build rather than as silence.",
            f"Add the missing ADR, or update `adr.expected_count` in ci/policy/policy.yaml as "
            "part of the same change that adds one.")

    # Contiguous numbering: a gap means a decision was deleted rather than superseded.
    nums = sorted(int(n) for n in ids)
    for expect, actual in zip(range(1, len(nums) + 1), nums):
        if expect != actual:
            g.check()
            g.fail("ADR-002", f"numbering gap: ADR-{expect:04d} missing",
                "ADR-0016 makes ADRs immutable once accepted. A gap means one was deleted, and a "
                "deleted decision takes its rationale with it — the exact loss ADRs exist to prevent.",
                f"Restore ADR-{expect:04d}, or supersede it with a new ADR that explains the change.")
            break

    exempt = {e["id"]: e for e in cfg.get("shape_exempt", [])}
    for num, f in sorted(ids.items()):
        txt = read_text(f); r = rel(f)
        g.check()

        if not re.search(r"^\|\s*Status\s*\|", txt, re.M):
            g.fail("ADR-003", "no Status row", "ADR-0016 requires a status so a superseded decision "
                "cannot be mistaken for a live one.", "Add a `| Status | ... |` row.", r)
        else:
            sm = re.search(r"^\|\s*Status\s*\|\s*(.+?)\s*\|", txt, re.M)
            val = sm.group(1) if sm else ""
            if not any(s.lower() in val.lower() for s in cfg["valid_statuses"]):
                g.fail("ADR-006", f"unrecognised status `{val[:60]}`",
                    f"Valid: {', '.join(cfg['valid_statuses'])}. An unrecognised status cannot be "
                    "acted on by tooling or trusted by a reader.",
                    "Use one of the valid statuses.", r)
            if "superseded" in val.lower() and not re.search(r"ADR-\d{4}", val):
                g.fail("ADR-007", "superseded without naming the successor",
                    "ADR-0016: a superseded ADR is kept for its rationale. Without a forward link "
                    "the reader has no way to find what replaced it.",
                    "Write `Superseded by [ADR-NNNN](ADR-NNNN-....md)`.", r)

        check_errata(g, cfg, num, txt, r)

        if num in exempt:
            g.note(f"ADR-{num} shape-exempt: {exempt[num]['why']}")
        else:
            for sec in cfg["required_sections"]:
                if sec not in txt:
                    g.fail("ADR-004", f"missing section `{sec}`",
                        "ADR-0016 mandates all six. `Alternatives Rejected` is the one that gets "
                        "dropped, and without it a decision is a preference wearing a decision's "
                        "clothes. `Verification` is the one that makes it checkable.",
                        f"Add a `{sec}` section.", r)

    # Every ADR-NNNN referenced anywhere must exist.
    for f in list(files) + [d / "README.md"]:
        if not f.exists():
            continue
        for m in re.finditer(r"\(ADR-(\d{4})-[a-z0-9-]+\.md\)", read_text(f)):
            g.check()
            if m.group(1) not in ids:
                g.fail("ADR-008", f"dangling reference to ADR-{m.group(1)}",
                    "A link to a nonexistent ADR sends the reader nowhere and hides that the "
                    "referenced decision was never written.",
                    f"Create ADR-{m.group(1)} or fix the reference.", rel(f))
    g.report_and_exit()

if __name__ == "__main__": main()
