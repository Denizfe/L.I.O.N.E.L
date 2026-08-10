#!/usr/bin/env python3
"""GATE: forbidden TODO markers, with a registry.

A blanket TODO ban gets worked around within a week. This gate allows a TODO only if
it is REGISTERED in ci/policy/policy.yaml with an owner and the gate that removes it.
An unregistered TODO fails; a registered one with no route to removal is rejected at
policy-load time. That turns "we'll fix it later" into a dated commitment.
"""
import fnmatch, re
from _lib import Gate, load_policy, repo_files, rel, read_text

def main():
    p = load_policy(); g = Gate("no-todo", "Forbidden TODO markers", ["MASTER_PLAN_v2 §12"])
    cfg = p["todo"]; registry = cfg.get("registry", [])

    for e in registry:
        if not e.get("owner") or not e.get("unblocked_by"):
            g.check()
            g.fail("TODO-002",
                f"registry entry `{e.get('pattern')}` has no owner or no unblocked_by",
                "An exemption with no route to removal is not an exemption, it is a silently "
                "lowered standard that outlives everyone who remembers agreeing to it.",
                "Add `owner:` and `unblocked_by:` (the gate or milestone that removes it) "
                "to the entry in ci/policy/policy.yaml.")

    def registered(path, line):
        for e in registry:
            if fnmatch.fnmatch(path, e["path_glob"]) and e["pattern"] in line:
                return e
        return None

    # Marker-shaped, not word-shaped. See policy.yaml `marker_patterns`.
    pat = re.compile("|".join(f"(?:{x})" for x in cfg["marker_patterns"]))
    allowed = 0
    for f in repo_files(include={".py", ".sh", ".yaml", ".yml", ".json", ".toml", ".proto", ".md"}):
        r = rel(f)
        # `ci/` and `docs/` remain excluded: the gates and ADRs necessarily contain
        # the strings they govern. The former blanket skip of Policy_Gates.md,
        # CI_Inventory.md and CI_Architecture.md was UNDOCUMENTED and has been removed —
        # the gate now applies to them (Category B review, 2026-08-03).
        if r.startswith(("ci/", "docs/")):
            continue
        for i, line in enumerate(read_text(f).splitlines(), 1):
            m = pat.search(line)
            if not m:
                continue
            e = registered(r, line)
            if e:
                allowed += 1
                continue
            g.check()
            g.fail("TODO-001",
                f"unregistered `{m.group(0)}`",
                "An unregistered TODO is an undated promise. It survives review because it "
                "looks like housekeeping, and it is still there two phases later.",
                "Either do the work now, or register it in ci/policy/policy.yaml under "
                "`todo.registry` with an `owner` and the gate in `unblocked_by`.",
                r, i)
    if allowed:
        g.note(f"{allowed} registered TODO(s) permitted — each has an owner and an unblocking gate.")
    g.check(1)
    g.report_and_exit()

if __name__ == "__main__": main()
