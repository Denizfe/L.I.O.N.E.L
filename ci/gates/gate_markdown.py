#!/usr/bin/env python3
"""GATE: markdown lint — internal links, heading hierarchy, trailing whitespace.

The valuable check here is BROKEN INTERNAL LINKS. A docs tree whose cross-references
rot is worse than one with none, because readers trust it and follow it into nothing.
"""
import re
from _lib import Gate, load_policy, repo_files, rel, read_text, ROOT

LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

def main():
    p = load_policy(); g = Gate("markdown", "Markdown lint", [])
    cfg = p["markdown"]

    exempt = set(cfg.get("exempt_paths", []))
    for f in repo_files(include={".md"}):
        r, txt = rel(f), read_text(f)
        if r in exempt:
            g.note(f"{r} exempt — {cfg.get('exempt_reasons', {}).get(r, 'declared in policy')}")
            continue
        lines = txt.splitlines()
        g.check()

        if cfg.get("check_internal_links"):
            for i, line in enumerate(lines, 1):
                for text, target in LINK.findall(line):
                    if target.startswith(("http://", "https://", "mailto:", "#")):
                        continue
                    tgt = target.split("#", 1)[0]
                    if not tgt:
                        continue
                    dest = (f.parent / tgt).resolve()
                    if not dest.exists():
                        g.fail("MD-LINK",
                            f"broken link `{tgt}` (text: “{text[:40]}”)",
                            "A docs tree whose cross-references rot is worse than one with none: "
                            "readers trust the link and follow it into nothing, then stop trusting "
                            "the rest of the tree.",
                            f"Fix the path or remove the link. Resolved to: {dest}", r, i)

        if cfg.get("check_heading_hierarchy"):
            prev = 0
            for i, line in enumerate(lines, 1):
                m = re.match(r"^(#{1,6})\s+\S", line)
                if not m:
                    continue
                lvl = len(m.group(1))
                if prev and lvl - prev > cfg.get("max_heading_jump", 1):
                    g.fail("MD-HEADING",
                        f"heading jumps from h{prev} to h{lvl}",
                        "Skipped levels break document outline and screen-reader navigation, and "
                        "usually mean a section was deleted without re-levelling its children.",
                        f"Use h{prev + 1} here, or add the intermediate heading.", r, i)
                prev = lvl

        if cfg.get("forbid_trailing_whitespace"):
            n = sum(1 for line in lines if line != line.rstrip() and not line.strip() == "")
            if n:
                g.fail("MD-WS",
                    f"{n} line(s) with trailing whitespace",
                    "Trailing whitespace produces noisy diffs that bury real changes in review.",
                    "Strip it. Most editors can do this on save.", r)
    g.check(1)
    g.report_and_exit()

if __name__ == "__main__": main()
