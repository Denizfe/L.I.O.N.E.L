#!/usr/bin/env python3
"""GATE: JSON Schema validity — meta-validation, examples, $ref resolution, ULIDs."""
import json, re
from _lib import Gate, load_policy, ROOT, rel, read_text, gate_error

def main():
    p = load_policy(); g = Gate("jsonschema", "JSON Schema validation", ["ADR-0027"])
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError as e:
        gate_error("jsonschema/referencing not installed", f"pip install jsonschema  ({e})")

    files = sorted((ROOT / "contracts").rglob("*.schema.json"))
    if not files:
        gate_error("no schemas found under contracts/")

    docs = {}
    for f in files:
        try:
            docs[f] = json.loads(read_text(f))
        except json.JSONDecodeError as e:
            g.check(); g.fail("JSON-001", f"invalid JSON: {e.msg} (line {e.lineno})",
                "A schema that does not parse validates nothing, and every consumer that "
                "depends on it fails at load rather than at review.",
                "Fix the syntax. Common cause here: TOML-style numeric separators (1_000) "
                "are not valid JSON.", rel(f), e.lineno)
    if g.findings:
        g.report_and_exit()

    reg = Registry()
    for d in docs.values():
        if "$id" in d:
            reg = reg.with_resource(d["$id"], Resource.from_contents(d))
    ids = {d.get("$id") for d in docs.values()}

    for f, d in docs.items():
        r = rel(f); g.check()
        try:
            Draft202012Validator.check_schema(d)
        except Exception as e:
            g.fail("JSON-002", f"not a valid JSON Schema 2020-12: {str(e)[:120]}",
                "A malformed schema silently accepts payloads it should reject.",
                "Fix the schema construct named in the error.", r)
            continue

        for m in set(re.findall(r'"\$ref":\s*"(https://lionel\.local[^"#]*)', json.dumps(d))):
            g.check()
            if m not in ids:
                g.fail("JSON-003", f"unresolvable $ref `{m}`",
                    "A dangling $ref means validation silently skips that subtree, so the "
                    "field it was supposed to constrain is effectively unvalidated.",
                    "Fix the $id/$ref, or add the missing schema.", r)

        v = Draft202012Validator(d, registry=reg)
        for i, ex in enumerate(d.get("examples", [])):
            g.check()
            for err in list(v.iter_errors(ex))[:1]:
                g.fail("JSON-004",
                    f"example[{i}] fails its own schema: {'.'.join(map(str, err.path)) or '(root)'} — {err.message[:110]}",
                    "An example is the fastest correct answer to 'what does this look like'. "
                    "One that does not validate is worse than none, because it gets copied.",
                    "Fix the example, or the schema if the example is right.", r)

        if not d.get("examples"):
            g.check()
            g.fail("JSON-005", "no examples",
                "contracts/README.md requires every schema to carry examples; they are the "
                "only part of a schema that is machine-checkable against itself.",
                "Add at least one entry to `examples`.", r)

    # ULID literals: Crockford base32 excludes I, L, O, U and is exactly 26 chars.
    # Five malformed literals slipped through during authoring. Hence a standing check.
    pat = re.compile(p["contracts"]["ulid_pattern"])
    cand = re.compile(r'"(01[0-9A-Z]{20,30})"')
    for f in sorted((ROOT / "contracts").rglob("*.json")):
        for i, line in enumerate(read_text(f).splitlines(), 1):
            for m in cand.finditer(line):
                g.check()
                if not pat.match(m.group(1)):
                    v = m.group(1)
                    why = []
                    if len(v) != 26: why.append(f"length {len(v)}, expected 26")
                    ill = sorted(set(c for c in v if c in "ILOU"))
                    if ill: why.append("contains " + ",".join(ill))
                    g.fail("JSON-006", f"malformed ULID `{v}` ({'; '.join(why)})",
                        "Crockford base32 excludes I, L, O and U to avoid visual ambiguity with "
                        "1 and 0. Five malformed literals slipped through during authoring, "
                        "which is why this is a standing check rather than a one-off fix.",
                        "Use 26 chars from [0-9A-HJKMNP-TV-Z].", rel(f), i)
    g.report_and_exit()

if __name__ == "__main__": main()
