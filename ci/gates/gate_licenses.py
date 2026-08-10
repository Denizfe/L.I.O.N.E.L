#!/usr/bin/env python3
"""GATE: licence policy.  ADR-0013."""
import re
from _lib import Gate, load_policy, ROOT, load_yaml

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9.\-]", "", (s or "").lower())

def main():
    p = load_policy(); g = Gate("licenses", "Licence policy", ["ADR-0013"])
    cfg = p["licenses"]
    allow = {norm(x) for x in cfg["allow"]}
    review = {norm(x["id"]): x for x in cfg["review_required"]}
    registry = {e["artifact"]: e for e in cfg.get("unresolved_registry", [])}
    for e in registry.values():
        if not e.get("owner") or not e.get("resolve_by"):
            g.check()
            g.fail("LIC-005", f"licence registry entry `{e.get('artifact')}` has no owner or resolve_by",
                "Deferring a licence question is fine. Deferring it with no owner and no gate "
                "means it is not deferred, it is dropped.",
                "Add `owner` and `resolve_by` in ci/policy/policy.yaml.")

    # ADR-0031. A review_required licence that has been ruled on. Policed the same way the
    # unresolved registry is: the escape hatch needs an owner and a route to removal, or it
    # becomes the loophole. `scope` is mandatory because the ruling is about a USE, not about
    # the artifact — "reviewed" with no stated scope is indistinguishable from "waved through".
    accepted = {e["artifact"]: e for e in cfg.get("review_accepted", [])}
    for e in accepted.values():
        for field in ("license", "owner", "scope", "revisit_at"):
            g.check()
            if not e.get(field):
                g.fail("LIC-006", f"accepted-review entry `{e.get('artifact')}` has no `{field}`",
                    "A reviewed licence records who ruled, what the ruling permits, and when it "
                    "must be re-made. Missing any of those turns the register into a way to "
                    "silence the gate rather than a way to answer it.",
                    "Add `license`, `owner`, `scope` and `revisit_at` in ci/policy/policy.yaml.")

    lock = ROOT / "artifacts.lock.yaml"
    if not lock.exists():
        from _lib import gate_error
        gate_error("artifacts.lock.yaml missing")
    d = load_yaml(lock)

    for sec in ("models", "images", "source"):
        for name, a in (d.get(sec) or {}).items():
            if a.get("status") == "NOT_YET_BUILT":
                continue
            g.check()
            lic = a.get("license")
            if not lic:
                g.fail("LIC-001", f"`{sec}.{name}` declares no licence",
                    "ADR-0013 records a licence per artifact so a licensing question is a lookup "
                    "rather than an archaeology exercise months later.",
                    "Add `license:` — check the upstream MODEL_CARD or repository.",
                    "artifacts.lock.yaml")
                continue

            n = norm(lic)
            if any(a_ in n for a_ in allow):
                continue
            hit = next((v for k, v in review.items() if k in n), None)
            acc = accepted.get(f"{sec}.{name}")
            if hit and acc and norm(acc.get("license", "")) == n:
                # Reviewed and ruled on. The constraint does not disappear — it is restated
                # on every run, because a bounded permission that stops being visible is
                # indistinguishable from no constraint at all.
                g.note(f"{sec}.{name}: {lic} — REVIEWED, {acc['scope']} "
                       f"(owner `{acc['owner']}`, revisit at {acc['revisit_at']})")
            elif hit:
                g.fail("LIC-002", f"`{sec}.{name}` licence needs review: {lic}", hit["why"],
                    "Confirm the intended use is permitted, or replace the artifact. If the use "
                    "is permitted, record it in `licenses.review_accepted` with an owner, the "
                    "scope it permits and a revisit gate (ADR-0031).",
                    "artifacts.lock.yaml")
            elif f"{sec}.{name}" in registry:
                e = registry[f"{sec}.{name}"]
                g.note(f"{sec}.{name}: licence unresolved, registered to `{e['owner']}` "
                       f"for {e['resolve_by']} — {e['why']}")
            elif "verify" in n or "same as" in n or "ambiguous" in n:
                g.fail("LIC-003", f"`{sec}.{name}` licence is unresolved: “{lic[:80]}”",
                    "An artifact whose licence is 'verify before release' is a deferred decision. "
                    "Deferred is acceptable; forgotten is not, so the gate keeps asking.",
                    "Read the upstream MODEL_CARD and record the actual identifier.",
                    "artifacts.lock.yaml")
            else:
                g.fail("LIC-004", f"`{sec}.{name}` licence `{lic}` is not on the allowlist",
                    f"Allowed: {', '.join(cfg['allow'])}. An unrecognised licence has not been "
                    "assessed, and unassessed is not the same as permissive.",
                    "Add it to `licenses.allow` after review, or replace the artifact.",
                    "artifacts.lock.yaml")

            if a.get("license_risk"):
                g.note(f"{sec}.{name}: {str(a['license_risk'])[:150]}")
    g.report_and_exit()

if __name__ == "__main__": main()
