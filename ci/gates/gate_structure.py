#!/usr/bin/env python3
"""GATE: repository structure.  MASTER_PLAN_v2 §8, ADR-0011."""
import fnmatch
from _lib import Gate, load_policy, ROOT, rel

def main():
    p = load_policy(); g = Gate("structure", "Repository structure", ["ADR-0011", "MASTER_PLAN_v2 §8"])
    cfg = p["repository"]

    for path in cfg["required_paths"]:
        g.check()
        if not (ROOT / path).is_file():
            g.fail("STRUCT-001", f"required file missing: `{path}`",
                "MASTER_PLAN_v2 §8 fixes the repository layout. A missing anchor file means "
                "either the layout drifted or a milestone was skipped.",
                f"Create `{path}` or update ci/policy/policy.yaml if the layout genuinely changed "
                "— but a layout change needs an ADR first.")

    for d in cfg["required_dirs"]:
        g.check()
        if not (ROOT / d).is_dir():
            g.fail("STRUCT-002", f"required directory missing: `{d}`",
                "MASTER_PLAN_v2 §8 layout.", f"Create `{d}/`.")

    for entry in cfg["forbidden_paths"]:
        g.check()
        if (ROOT / entry["path"]).exists():
            g.fail("STRUCT-003", f"forbidden path exists: `{entry['path']}`", entry["why"],
                f"Delete `{entry['path']}`. Its absence is a recorded decision, not an oversight.")

    # Phase 0 forbids runtime code. This is the loudest architectural signal in the repo.
    if cfg.get("runtime_code_forbidden_until"):
        offenders = []
        for glob in cfg["runtime_code_globs"]:
            offenders += [q for q in ROOT.glob(glob) if q.is_file()]
        g.check()
        if offenders:
            g.fail("STRUCT-004",
                f"{len(offenders)} runtime source file(s) present during Phase 0",
                f"MASTER_PLAN_v2: no implementation code until {cfg['runtime_code_forbidden_until']} "
                "is signed off. Contracts and ADRs land before the code they constrain — that "
                "ordering is what made the v1.0→v2.0 migration cost zero lines of rework.",
                f"Remove them, or sign off {cfg['runtime_code_forbidden_until']} and update "
                "`repository.runtime_code_forbidden_until` in ci/policy/policy.yaml.")
            for q in offenders[:10]:
                g.note(f"runtime file: {rel(q)}")
        else:
            g.note(f"0 runtime source files — Phase 0 discipline holds")
    g.report_and_exit()

if __name__ == "__main__": main()
