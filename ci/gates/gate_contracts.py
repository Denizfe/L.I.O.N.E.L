#!/usr/bin/env python3
"""GATE: contract metadata and manifest consistency.  contracts/README.md."""
import json, glob
from _lib import Gate, load_policy, ROOT, rel, read_text, load_json

def main():
    p = load_policy(); g = Gate("contracts", "Contract metadata", ["ADR-0003", "ADR-0009"])
    cfg = p["contracts"]

    files = sorted((ROOT / "contracts").rglob("*.schema.json"))
    for f in files:
        r = rel(f); g.check()
        try:
            d = json.loads(read_text(f))
        except Exception:
            continue                       # gate_jsonschema owns syntax
        x = d.get("x-lionel")
        if not x:
            g.fail("CONTRACT-001", "no `x-lionel` block",
                "contracts/README.md requires provenance, ownership and compatibility policy on "
                "every schema. Without them nobody can judge the blast radius of a change.",
                "Add an `x-lionel` block with version, adr, stability, plane, owner, producer, "
                "consumers and compatibility.", r)
            continue

        for k in cfg["required_x_lionel"]:
            if k not in x:
                g.fail("CONTRACT-002", f"`x-lionel.{k}` missing",
                    "`producer` and `consumers` make the cost of a change visible BEFORE the "
                    "change. A schema with five consumers is not one edit, it is five coordinated "
                    "ones — and 'just add a required field' stops looking cheap.",
                    f"Add `{k}` to the x-lionel block.", r)

        for k in cfg["required_compatibility"]:
            if k not in (x.get("compatibility") or {}):
                g.fail("CONTRACT-003", f"`compatibility.{k}` missing",
                    "Compatibility notes are what a consumer reads to upgrade safely; "
                    "`breaking_changes` is append-only because the history is the point.",
                    f"Add `compatibility.{k}`.", r)

        if x.get("plane") not in cfg["valid_planes"]:
            g.fail("CONTRACT-004", f"invalid plane `{x.get('plane')}`",
                f"ADR-0006 defines exactly {cfg['valid_planes']}. An unrecognised plane means "
                "the control/data separation cannot be checked for that schema.",
                f"Use one of {cfg['valid_planes']}.", r)
        if x.get("stability") not in cfg["valid_stability"]:
            g.fail("CONTRACT-005", f"invalid stability `{x.get('stability')}`",
                f"Valid: {cfg['valid_stability']}. Stability decides whether a change needs an ADR.",
                f"Use one of {cfg['valid_stability']}.", r)
        if x.get("owner") not in cfg["valid_owners"]:
            g.fail("CONTRACT-006", f"invalid owner `{x.get('owner')}`",
                "Ownership decides who must be consulted on a change. An owner outside the "
                "declared module set means nobody is accountable.",
                f"Use one of {cfg['valid_owners']}.", r)

        if not x.get("consumers"):
            g.fail("CONTRACT-007", "empty `consumers`",
                "A schema with no declared consumer is dead weight. Either something reads it "
                "and the list is wrong, or nothing does and it should be deleted.",
                "List the consuming components, or remove the schema.", r)

    # MANIFEST must match what is on disk, or the register lies.
    man = ROOT / cfg["manifest"]
    g.check()
    if not man.exists():
        g.fail("CONTRACT-008", f"manifest missing: {cfg['manifest']}",
            "MANIFEST.json is the contract-set inventory and negotiation source.",
            "Create it.", cfg["manifest"])
    else:
        m = load_json(man)
        for plane, spec in (m.get("planes") or {}).items():
            listed = set(spec.get("schemas", spec.get("files", [])))
            d = ROOT / "contracts" / spec["path"]
            actual = {q.name for q in d.iterdir() if q.is_file()} if d.is_dir() else set()
            g.check()
            if listed != actual:
                only_m, only_d = listed - actual, actual - listed
                g.fail("CONTRACT-009",
                    f"manifest/disk mismatch in `{plane}`" +
                    (f" — manifest-only: {sorted(only_m)}" if only_m else "") +
                    (f" — disk-only: {sorted(only_d)}" if only_d else ""),
                    "A stale inventory is worse than none because it gets trusted. Someone will "
                    "read MANIFEST.json to find a contract and conclude it does not exist.",
                    "Regenerate MANIFEST.json rather than hand-editing it.", cfg["manifest"])

    g.check()
    inv = ROOT / "contracts" / "Contract_Inventory.md"
    if not inv.exists():
        g.fail("CONTRACT-010", "Contract_Inventory.md missing",
            "The register is how a reader finds a contract and judges change cost.",
            "Regenerate it from the x-lionel blocks.", "contracts/Contract_Inventory.md")
    g.report_and_exit()

if __name__ == "__main__": main()
