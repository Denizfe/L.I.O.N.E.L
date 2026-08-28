#!/usr/bin/env python3
"""GATE: dependency policy.  ADR-0013.

DEP-002 read `pyproject.toml` and nothing else until 2026-08-28. It expressed a decision
about what may be INSTALLED and checked only what was DECLARED, so any forbidden package
arriving as somebody else's transitive dependency was invisible to it.

That is not hypothetical. Accepting ADR-0036 added `fastembed`, which depends directly on
`requests` -- the one package `forbid_packages` names. `uv.lock` gained it, every gate
stayed green, and the decision "two HTTP clients is drift, not choice" was quietly untrue.
DEP-003 reads the lock, so what is installed is checked rather than what was written down.
(`huggingface-hub`, the other obvious suspect, uses httpx. Worth checking rather than
assuming: the first draft of this docstring blamed it.)

Transitive arrivals are not automatically wrong: DEP-002 is about which client OUR code
calls, and a vendored library's own HTTP stack is a different question. So DEP-003 is
satisfiable by a registered exemption -- with an owner and a route to removal, like every
other exemption in this repository -- and refuses one that no longer applies.
"""
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

    # ── DEP-003: forbidden packages that arrived transitively ────────────────────
    locked = set(re.findall(r'^name = "([^"]+)"', read_text(lock), re.M))
    declared = {re.sub(r"\[.*\]", "", n).strip() for n, _ in deps}
    exempt = {e["package"]: e for e in cfg.get("transitive_exemptions", []) or []}

    for fb in cfg.get("forbid_packages", []):
        name = fb["name"]
        if name not in locked or name in declared:
            continue  # not installed, or already reported by DEP-002
        g.check()
        e = exempt.get(name)
        if not e:
            g.fail("DEP-003", f"forbidden package `{name}` is installed transitively",
                fb["why"] + " It is not declared, so DEP-002 does not see it — but it is in "
                f"{cfg['require_lockfile']}, which is what actually gets installed.",
                f"Drop whatever pulls it, or register it under "
                f"`dependencies.transitive_exemptions` with `pulled_by`, `why`, `owner` "
                f"and `unblocked_by`.", rel(man))
            continue
        missing = [k for k in ("pulled_by", "why", "owner", "unblocked_by") if not e.get(k)]
        if missing:
            g.fail("DEP-003",
                f"transitive exemption for `{name}` is missing {', '.join(missing)}",
                "An exemption with no owner and no route to removal is not an exemption; it "
                "is a silently lowered standard.",
                "Add the missing fields.", "ci/policy/policy.yaml")
        elif e["pulled_by"] not in locked:
            g.fail("DEP-003",
                f"exemption says `{name}` is pulled by `{e['pulled_by']}`, which is not in "
                f"{cfg['require_lockfile']}",
                "A stale exemption keeps suppressing a check after the reason for it has "
                "gone. This is the shape COV-003 and QUOTE-003 already police.",
                "Re-check what pulls it, or remove the exemption.", "ci/policy/policy.yaml")
        else:
            g.note(f"`{name}` transitively via `{e['pulled_by']}` — owner `{e['owner']}`, "
                   f"unblocked by {e['unblocked_by']}")

    for name in exempt:
        g.check()
        if name not in locked:
            g.fail("DEP-003", f"transitive exemption for `{name}`, which is not installed",
                "An exemption for something that is not there is dead policy, and it will "
                "silently start applying if the package ever returns.",
                "Remove the entry.", "ci/policy/policy.yaml")

    g.report_and_exit()

if __name__ == "__main__": main()
