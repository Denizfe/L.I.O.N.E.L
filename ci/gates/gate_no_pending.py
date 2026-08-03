#!/usr/bin/env python3
"""GATE: forbidden placeholder values.  ADR-0013."""
import re
from _lib import Gate, load_policy, repo_files, rel, read_text

def main():
    p = load_policy(); g = Gate("no-pending", "Forbidden placeholder values", ["ADR-0013"])
    bad = p["placeholders"]["forbidden_tokens"]
    ok  = p["placeholders"]["allowed_tokens"]
    g.note(f"`{'`, `'.join(ok)}` are legitimate documented states, not placeholders.")
    pat = re.compile("|".join(re.escape(t) for t in bad))
    for f in repo_files(include={".yaml", ".yml", ".json", ".toml", ".sh", ".proto"}):
        r = rel(f)
        # The policy file names the forbidden tokens; the ADRs and reports discuss them.
        # artifacts.lock.yaml documents the placeholder rule in its own header.
        # `ci/` excluded: gates and their self-test necessarily CONTAIN the strings
        # they hunt. Flagging them would invite weakening the pattern, which is how
        # a gate quietly stops catching real violations.
        if r.startswith(("ci/", "docs/")):
            continue
        for i, line in enumerate(read_text(f).splitlines(), 1):
            m = pat.search(line)
            if not m:
                continue
            g.check()
            g.fail("PLACEHOLDER-001",
                f"placeholder `{m.group(0)}` present",
                "ADR-0013: a fabricated value that looks real is strictly worse than an absent "
                "one, because it looks verified and gets trusted. A lockfile full of PENDING "
                "hashes reports green while pinning nothing.",
                "Resolve the real value, or mark the entry UNRESOLVED with a classified blocker "
                "and a reproducible alternative (see Artifact_Verification_Report.md §5).",
                r, i)
    g.check(1)
    g.report_and_exit()

if __name__ == "__main__": main()
