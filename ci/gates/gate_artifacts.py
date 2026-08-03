#!/usr/bin/env python3
"""GATE: artifact lock validation.  ADR-0013."""
import re
from collections import Counter
from _lib import Gate, load_policy, ROOT, rel, load_yaml, read_text, gate_error

HEX64, HEX40 = re.compile(r"^[0-9a-f]{64}$"), re.compile(r"^[0-9a-f]{40}$")

def main():
    p = load_policy(); g = Gate("artifacts", "Artifact lock validation", ["ADR-0013"])
    cfg = p["artifacts"]
    lock = ROOT / cfg["lockfile"]
    if not lock.exists():
        gate_error(f"lockfile missing: {cfg['lockfile']}")
    d = load_yaml(lock); r = cfg["lockfile"]

    items = [(f"{s}.{k}", v) for s in ("models", "images", "source")
             for k, v in (d.get(s) or {}).items()]
    res = unres = 0
    tiers = Counter()

    for name, a in items:
        st = a.get("status")
        if st == "NOT_YET_BUILT":
            continue
        v = a.get("verification") or {}
        g.check()

        for f_ in ("adr", "purpose", "source_url", "license"):
            if f_ not in a:
                g.fail("ART-001", f"`{name}` missing `{f_}`",
                    "ADR-0013 requires every artifact to record what it is, where it came from, "
                    "and under what licence. A pin without provenance is a number.",
                    f"Add `{f_}` to the entry.", r)
        for f_ in ("tier", "provenance", "method", "retrieved"):
            if f_ not in v:
                g.fail("ART-002", f"`{name}` missing `verification.{f_}`",
                    "A hash is not a hash: where it came from determines what it proves. "
                    "Flattening that is how a lockfile grants false confidence.",
                    f"Add `verification.{f_}`.", r)

        if v.get("tier") and v["tier"] not in cfg["valid_tiers"]:
            g.fail("ART-003", f"`{name}` invalid tier `{v['tier']}`",
                f"Valid tiers: {cfg['valid_tiers']} (see artifacts.lock.yaml header).",
                "Use a declared tier.", r)
        if v.get("provenance") and v["provenance"] not in cfg["valid_provenance"]:
            g.fail("ART-004", f"`{name}` invalid provenance `{v['provenance']}`",
                f"Valid: {cfg['valid_provenance']}.", "Use a declared provenance.", r)

        if st == "RESOLVED":
            res += 1
            if v.get("tier"):
                tiers[v["tier"]] += 1
            if v.get("provenance") == "pinned-model-id":
                if not a.get("pinned_by"):
                    g.fail("ART-005", f"`{name}` pinned-model-id without `pinned_by`",
                        "Not every pin is a file hash — a library-cached model is pinned by "
                        "identifier plus a startup assertion. That is legitimate, but it must be "
                        "declared explicitly rather than granted as a silent exemption.",
                        "Add `pinned_by:` naming the mechanism.", r)
            else:
                h = a.get("sha256") or a.get("digest") or a.get("commit") or a.get("git_blob_sha1")
                if not h:
                    g.fail("ART-006", f"`{name}` is RESOLVED with no pin",
                        "RESOLVED means reproducible. Without a hash it is neither.",
                        "Add a sha256/digest/commit, or set status UNRESOLVED with a blocker.", r)
                else:
                    hh = str(h).replace("sha256:", "")
                    if not (HEX64.match(hh) or HEX40.match(hh)):
                        g.fail("ART-007", f"`{name}` malformed hash `{h}`",
                            "A malformed hash cannot verify anything and will fail closed at "
                            "fetch time — after the download.",
                            "Use 64 lowercase hex (SHA-256) or 40 (SHA-1/git).", r)
                if len(str(v.get("method", ""))) < 40:
                    g.fail("ART-008", f"`{name}` verification.method too thin to audit",
                        "The method is how a reviewer re-derives the hash independently. "
                        "'from the website' is not auditable.",
                        "Describe the exact endpoint or command used.", r)

        elif st == "UNRESOLVED":
            unres += 1
            b = a.get("blocker") or {}
            alts = a.get("alternatives") or []
            if cfg.get("require_blocker_classification"):
                if b.get("classification") not in ("TEMPORARY", "PERMANENT"):
                    g.fail("ART-009", f"`{name}` blocker not classified",
                        "TEMPORARY and PERMANENT demand different responses: one is waited out, "
                        "the other requires changing the design. 'Blocked' without that "
                        "distinction is a shrug.",
                        "Set `blocker.classification` to TEMPORARY or PERMANENT with a reason.", r)
                if not b.get("what"):
                    g.fail("ART-010", f"`{name}` blocker does not say what is blocked",
                        "A blocker nobody can reproduce cannot be cleared by anybody else.",
                        "Describe exactly what fails.", r)
            if cfg.get("require_reproducible_alternative"):
                if not alts:
                    g.fail("ART-011", f"`{name}` proposes no alternative",
                        "An unresolved artifact with no route forward stalls the gate "
                        "indefinitely and nobody knows whose move it is.",
                        "Propose at least one alternative in `alternatives`.", r)
                elif not any(x.get("reproducible") for x in alts):
                    g.fail("ART-012", f"`{name}` has no REPRODUCIBLE alternative",
                        "An alternative that is not reproducible does not solve the problem "
                        "ADR-0013 exists to solve.",
                        "Mark at least one alternative `reproducible: true`, or find one.", r)
        else:
            g.fail("ART-013", f"`{name}` unknown status `{st}`",
                "Valid: RESOLVED, UNRESOLVED, NOT_YET_BUILT.", "Use a declared status.", r)

    m = d.get("meta", {})
    g.check()
    if (m.get("resolved"), m.get("unresolved")) != (res, unres):
        g.fail("ART-014",
            f"[meta] drift: declared {m.get('resolved')}/{m.get('unresolved')}, actual {res}/{unres}",
            "A header that disagrees with the body is a comfortable lie: it is the first thing "
            "read and the last thing updated.",
            f"Set `meta.resolved: {res}` and `meta.unresolved: {unres}`.", r)

    g.check()
    if tiers.get("D", 0) > cfg["max_tier_d"]:
        g.fail("ART-015", f"{tiers['D']} tier-D artifacts, policy allows {cfg['max_tier_d']}",
            "Tier D is a single uncorroborated mirror — reproducible from that source, but not "
            "proven identical to upstream. One is a documented exception; several is a drift "
            "in standards.",
            "Find a corroborating source, or raise `artifacts.max_tier_d` deliberately with a "
            "recorded reason.", r)
    if tiers.get("D"):
        g.note(f"{tiers['D']} tier-D artifact(s) — single uncorroborated mirror. See "
               "Artifact_Verification_Report.md §3.4.")

    # ADR-0018: English-only whisper models are rejected project-wide, not discouraged.
    g.check()
    if re.search(r"ggml-[a-z0-9.\-]*\.en\.bin", read_text(lock)):
        g.fail("ART-016", "an English-only `.en` whisper model is pinned",
            "ADR-0018: `.en` models are English-only by construction, not merely "
            "English-optimised. They cannot serve Turkish at any quality.",
            "Use a multilingual model such as large-v3-turbo.", r)

    g.note(f"tiers: " + " · ".join(f"{t}={tiers[t]}" for t in "ABCD" if tiers.get(t)))
    if unres:
        g.note(f"{unres} UNRESOLVED — G0 blocked by design. See Artifact_Verification_Report.md.")
        g.fail("ART-000", f"{unres} artifact(s) unresolved",
            "ADR-0013: G0 cannot be signed off while any artifact is unpinned. This gate is RED "
            "on purpose until the lockfile reaches zero unresolved.",
            "Follow the alternatives in Artifact_Verification_Report.md §5, then update the "
            "lockfile entry and meta counts.", r)
    g.report_and_exit()

if __name__ == "__main__": main()
