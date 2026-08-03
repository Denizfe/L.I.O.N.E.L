#!/usr/bin/env python3
"""GATE: dependency policy.  ADR-0013."""
import re
from _lib import Gate, load_policy, ROOT, rel, read_text

def main():
    p = load_policy(); g = Gate("dependencies", "Dependency policy", ["ADR-0013"])
    cfg = p["dependencies"]
    man = ROOT / cfg["manifest"]

    g.check()
    if not man.exists():
        g.note(f"{cfg['manifest']} not present yet — dependency policy is inert until Phase 1 "
               "creates it. The gate is wired now so it cannot be forgotten then.")
        g.report_and_exit()

    txt = read_text(man)
    deps = re.findall(r'^\s*"([A-Za-z0-9_.\-\[\]]+)\s*([<>=!~^].*?)?"\s*,?\s*$', txt, re.M)

    for name, bound in deps:
        base = re.sub(r"\[.*\]", "", name).strip()
        g.check()
        if cfg.get("require_version_bounds") and not bound:
            g.fail("DEP-001", f"`{base}` has no version bound",
                "ADR-0013: an unbounded dependency means a rebuild months later resolves to a "
                "different tree. 'It worked last week' becomes unanswerable.",
                f'Add a bound, e.g. `"{base}>=x.y"`.', rel(man))
        for fb in cfg.get("forbid_packages", []):
            if base == fb["name"]:
                g.fail("DEP-002", f"forbidden package `{base}`", fb["why"],
                    "Remove it and use the existing equivalent.", rel(man))

    lock = ROOT / cfg["require_lockfile"]
    g.check()
    if not lock.exists():
        g.note(f"{cfg['require_lockfile']} absent — required from {cfg['lockfile_required_at']}. "
               "Not a violation during Phase 0, since nothing is installed yet.")
    g.report_and_exit()

if __name__ == "__main__": main()
