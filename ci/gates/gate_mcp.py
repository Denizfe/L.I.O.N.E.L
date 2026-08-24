#!/usr/bin/env python3
"""GATE: developer-tooling MCP servers are pinned, disclosed and credential-free.  ADR-0032.

WHY THIS EXISTS
    An MCP server is code that runs on a developer machine with the repository open, and
    it usually talks to the network. Before ADR-0032 those servers lived only in each
    person's user-level settings: not reproducible, and with nowhere to record what they
    send off the machine. `.mcp.json` is that place, and this gate is what stops it from
    becoming a list nobody reads.

    `.mcp.json` is deliberately NOT in the architecture checksum set. It is workstation
    tooling, not architecture. ADR-0032 is emphatic on the same point from the other
    direction: no gate may depend on an MCP server, and nothing in `config/`, `contracts/`
    or the runtime surface may reference one. `l0-conformance` is what proves that half.

RULES
    MCP-000  the manifest is not valid JSON
    MCP-001  a package-backed command does not pin an exact version
    MCP-002  an entry does not declare what leaves the machine
    MCP-003  an entry carries a literal credential

    MCP-000 is not named in ADR-0032's Verification section, and it is mechanical
    necessity rather than a new decision: a malformed manifest is a file the repository
    owns and a human must fix, so reporting it through `gate_error` — exit 2, "the gate is
    broken" — would break the exit-code contract. See ADR-0032's Erratum of 2026-08-24.

    ADR-0032's standing criterion — one entry; a second is a decision — is reported as a
    NOTE and never as a violation. A gate that blocked the second entry would settle by
    implementation the question the ADR deliberately left to a reviewer.

ABSENCE IS NOT THIS GATE'S BUSINESS
    `.mcp.json` is in `repository.required_paths`, so a deleted manifest fails `structure`
    with a finding that says so. If this gate also owned existence, deleting the file
    would produce two findings about one problem — and if it owned it *instead*, deleting
    the file would leave this gate with nothing to check and a green light to show for it.
"""
import json
import re

from _lib import Gate, ROOT, load_policy, read_text

# name@1.2.3 · @scope/name@1.2.3. A range (^1.2.3, ~1.2, >=1.0) or a dist-tag (latest,
# next, beta) resolves differently tomorrow, which is the whole objection.
_NPM_PIN = re.compile(r"^(@[a-z0-9][\w.-]*/)?[a-z0-9][\w.-]*@\d+\.\d+\.\d+[\w.+-]*$", re.I)
# pkg==1.2.3. `pkg`, `pkg>=1.2` and `pkg~=1.2` are not pins.
_PY_PIN = re.compile(r"^[A-Za-z0-9][\w.-]*(\[[\w,.-]+\])?==\d+[\w.+!-]*$")


def _spec_args(args: list[str]) -> list[str]:
    """The positional arguments — flags, and the values they consume, are not packages."""
    return [a for a in args if not a.startswith("-")]


def check_pin(g, cfg, name, entry, manifest):
    command = str(entry.get("command", "") or "").strip()
    base = command.replace("\\", "/").rsplit("/", 1)[-1]
    base = re.sub(r"\.(cmd|exe|bat|ps1)$", "", base, flags=re.I)

    npm = [c.lower() for c in cfg.get("npm_style_commands", [])]
    py = [c.lower() for c in cfg.get("python_style_commands", [])]
    if base.lower() not in npm + py:
        return  # a local binary or an absolute path — nothing is resolved from a registry

    g.check()
    args = [str(a) for a in entry.get("args", []) or []]
    specs = _spec_args(args)
    pin = _NPM_PIN if base.lower() in npm else _PY_PIN
    shape = "`name@1.2.3` (npm)" if base.lower() in npm else "`pkg==1.2.3` (Python)"

    if any(pin.match(s) for s in specs):
        return

    shown = " ".join([command] + args) or command
    g.fail("MCP-001", f"MCP server `{name}` resolves its package at launch instead of "
           f"pinning it: `{shown}`",
        "ADR-0032 rule 2, applying ADR-0013: `npx -y <pkg>` takes whatever is newest at "
        "the moment someone opens their editor, so every machine can run a different "
        "version and the window for a supply-chain compromise is 'whenever anyone next "
        "started their editor'. This is code running with the repository open.",
        f"Pin an exact version — {shape}. A range or a dist-tag such as `latest` is not "
        f"a pin.", manifest)


def check_egress(g, cfg, name, entry, manifest):
    if not cfg.get("require_egress_note", True):
        return
    g.check()
    note = ((entry.get("x-lionel") or {}).get("egress") or "").strip()
    if note:
        return
    g.fail("MCP-002", f"MCP server `{name}` does not declare what leaves the machine",
        "ADR-0032 rule 3. 'Library names and version strings' and 'the contents of files "
        "you ask it about' are different answers and must not be collapsed. This project's "
        "central claim is an offline autonomy guarantee; a tool in the workflow that sends "
        "something undisclosed is exactly the erosion MASTER_PLAN_v2 §W1 describes.",
        f"Add an `x-lionel.egress` string to the `{name}` entry saying what it sends and "
        f"to whom — or `\"none — runs entirely locally\"` if nothing leaves.", manifest)


def check_secrets(g, cfg, name, entry, manifest):
    key_re = re.compile(cfg.get("credential_key_regex", "(?!)"))
    allowed = [re.compile(p) for p in cfg.get("credential_value_allowed", []) or []]

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, path + [str(k)])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + [str(i)])
        elif isinstance(node, str):
            here = ".".join(path)
            # `x-lionel` is prose ABOUT the entry — the context7 entry's own `secrets`
            # note has to be able to say the words "Authorization: Bearer" in order to
            # explain why there is no key. Matching on it would punish the disclosure.
            if "x-lionel" in path:
                return
            if not key_re.search(here):
                return
            g.check()
            if any(a.search(node) for a in allowed):
                return
            g.fail("MCP-003", f"MCP server `{name}` carries a literal credential at `{here}`",
                "ADR-0032 rule 4 and ADR-0015: a credential in a checked-in file is a "
                "committed credential. `gate_secrets` scans this file with no path "
                "exclusions, so the only question is whether you find it or the gate does.",
                "Reference the environment instead — `\"${LIONEL_SOME_TOKEN}\"` — or drop "
                "the key: ADR-0032 declined context7's, because it buys rate limit rather "
                "than capability.", manifest)

    walk(entry, [])

    # A key can also ride in on the command line — `--api-key=sk-…`, `--token sk-…`. The
    # path-based walk above cannot see it, because the JSON key is just `args.3`.
    inline = re.compile(r"(?i)\b[\w-]*(api[-_]?key|token|secret|password|credential|bearer)"
                        r"[\w-]*\s*[=:]\s*(\S+)")
    for i, a in enumerate(entry.get("args", []) or []):
        if not isinstance(a, str):
            continue
        m = inline.search(a)
        if not m:
            continue
        g.check()
        if any(al.search(m.group(2)) for al in allowed):
            continue
        g.fail("MCP-003", f"MCP server `{name}` passes a credential on the command line: "
               f"`args[{i}]`",
            "ADR-0032 rule 4 and ADR-0015. An argument is no less checked in than a value, "
            "and it is additionally visible in every process listing on the machine.",
            "Move it to the environment and reference it — or, as ADR-0032 did for "
            "context7, decide the server does not need one.", manifest)


def main():
    p = load_policy()
    g = Gate("mcp", "Dev-tooling MCP servers are pinned and disclosed",
             ["ADR-0032", "ADR-0013", "ADR-0015"])
    cfg = p.get("mcp", {}) or {}
    manifest = cfg.get("manifest", ".mcp.json")
    f = ROOT / manifest

    g.check()
    if not f.is_file():
        # `structure` owns existence (repository.required_paths). Saying nothing here
        # would be a green gate with nothing behind it, so say it as a note.
        g.note(f"{manifest} does not exist — no MCP servers are declared. `structure` "
               f"owns that finding (repository.required_paths); this gate checks contents.")
        g.report_and_exit()

    try:
        doc = json.loads(read_text(f))
    except json.JSONDecodeError as e:
        g.fail("MCP-000", f"{manifest} is not valid JSON: {e.msg}",
            "A manifest that cannot be parsed declares nothing, and every rule below it "
            "silently stops applying — the gate goes green because it found no entries "
            "rather than because the entries were clean.",
            "Fix the JSON. `python3 -c \"import json;json.load(open('.mcp.json'))\"` "
            "reports the position.", manifest, e.lineno)
        g.report_and_exit()

    servers = (doc or {}).get("mcpServers", {}) or {}
    g.check()
    if not isinstance(servers, dict):
        g.fail("MCP-000", f"`mcpServers` in {manifest} is not an object",
            "The MCP client reads `mcpServers` as a name → definition map. Any other shape "
            "means the file does not declare what it appears to declare.",
            "Write `\"mcpServers\": { \"<name>\": { … } }`.", manifest)
        g.report_and_exit()

    for name in sorted(servers):
        entry = servers[name]
        if not isinstance(entry, dict):
            g.check()
            g.fail("MCP-000", f"MCP server `{name}` is not an object",
                "An entry that is not a definition cannot be pinned, cannot declare its "
                "egress, and cannot be reviewed.",
                f"Give `{name}` a `command` / `args` object.", manifest)
            continue
        check_pin(g, cfg, name, entry, manifest)
        check_egress(g, cfg, name, entry, manifest)
        check_secrets(g, cfg, name, entry, manifest)

    n = len(servers)
    standing = cfg.get("standing_entry_count")
    if servers:
        g.note(f"{n} MCP server(s) declared: {', '.join(sorted(servers))}")
    if standing is not None and n > standing:
        g.note(f"ADR-0032's standing criterion is {standing} entry — a second is a decision, "
               f"not a routine addition. {n} are declared. This is a note by design: "
               f"whether the addition was reviewed is a judgement, and a gate that answered "
               f"it would be deciding rather than checking.")

    g.report_and_exit()


if __name__ == "__main__":
    main()
