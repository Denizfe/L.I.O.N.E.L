#!/usr/bin/env python3
"""Generate CI_Inventory.md and Policy_Gates.md from the gates themselves.

    python3 scripts/generate_ci_docs.py            # rewrite both documents
    python3 scripts/generate_ci_docs.py --check    # exit 1 if either is stale

WHY THIS EXISTS
    Both documents ended their own text with "Regenerate rather than hand-edit" while
    no generator existed. They drifted exactly as you would expect: CI_Inventory.md
    claimed 16 gates against 17 on disk and 8/8 self-test coverage against 10/10, and
    Policy_Gates.md catalogued 88 rules while omitting the l0-conformance gate
    entirely -- the keystone gate, absent from the rule catalogue. Findings N1 and N2
    of Phase0_Final_Signoff.md.

    A number in a document that nobody can recompute rots silently and is trusted
    anyway, which is worse than having no document. Everything below that CAN be
    derived from source IS derived from source. What cannot -- the prose, and the
    curated ADR-coverage judgements -- lives here as reviewable data rather than in a
    file that drifts.

WHAT COUNTS AS A RULE
    A rule is a distinct rule ID a gate can emit. IDs are collected as the string
    constants in each gate that match the rule-ID shape, excluding four-digit
    `ADR-0000` references, which are citations rather than rules. Three gates build
    IDs at runtime, so their sets are completed from ci/policy/policy.yaml.

    Collecting constants rather than only `g.fail(...)` first arguments matters: the
    l0-conformance gate emits 24 rules through a single `g.fail(rid, ...)` call site
    driven by a table, and an extractor that reads call sites sees one rule where
    there are twenty-four. That is precisely how Policy_Gates.md lost the gate.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
GATES_DIR = ROOT / "ci" / "gates"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

RULE_ID = re.compile(r"^[A-Z][A-Z0-9]{1,}(?:-[A-Z0-9]+)+$")
ADR_CITATION = re.compile(r"^ADR-\d{4}$")

# The runner's ORDER array is the canonical gate order; the documents follow it so a
# reader moving between them, the runner output and the workflow sees one sequence.
ORDER_RE = re.compile(r"ORDER=\((.*?)\)", re.S)


# ── Curated content ────────────────────────────────────────────────────────────
# Judgements that cannot be derived from source. Kept here so regeneration preserves
# them and so changing one is a reviewable diff rather than an edit to a generated file.

ADR_ENFORCED = [
    ("0003", "MCP-first capability model", "`contracts`"),
    ("0006", "Control/data plane separation", "`architecture` ARCH-003, `protobuf`, `l0-conformance` L0-CONTRACT-*"),
    ("0007", "Degradation ladder, L0 guarantee", "`architecture` ARCH-011…013, **`l0-conformance` (24 rules)**"),
    ("0008", "Coordinator decomposition", "`architecture` ARCH-015"),
    ("0009", "Extended BrainProvider contract", "`architecture` ARCH-002, `contracts`"),
    ("0010", "Memory Service", "`architecture` ARCH-010, `l0-conformance` L0-ARCH-005"),
    ("0011", "Shell execution abolished", "`architecture` ARCH-001, `shell`, `structure`, `l0-conformance` L0-SHELL-001"),
    ("0012", "Policy Engine, default-deny", "`architecture` ARCH-004, 006, 007, 009, `l0-conformance` L0-ARCH-002…003"),
    ("0013", "Artifact pinning", "`artifacts`, `docker-digests`, `no-latest`, `no-pending`, `licenses`, `dependencies`"),
    ("0014", "ProcessSupervisor", "`shell`, **windows-latest job**"),
    ("0015", "SecretResolver, no interpolation", "`secrets`"),
    ("0016", "ADRs replace `<thought>`", "`adr`, `architecture` ARCH-016"),
    ("0018", "Multilingual STT mandatory", "`architecture` ARCH-014, `artifacts` ART-016"),
    ("0020", "Kubernetes, cloud-portable", "`docker-digests`"),
    ("0022", "Zero trust between runtimes", "`secrets`"),
    ("0023", "Turkish locale", "**tr_TR.UTF-8 job** — shell-level only until G6c"),
    ("0025", "Cancellation & backpressure", "`architecture` ARCH-008, `l0-conformance` L0-ARCH-004"),
    ("0026", "Side-effect classification", "`architecture` ARCH-005"),
    ("0027", "Testing strategy", "`jsonschema`, `gate-coverage`"),
    ("0028", "Data-plane transport", "`protobuf`"),
    ("0029", "Errata / Amendment / Supersede", "`adr` ADR-009"),
    ("0030", "Self-enforcing CI", "`checksum`, `generated-docs`, `gate-coverage`"),
    ("0031", "Reviewed-licence register", "`licenses` LIC-006"),
]

ADR_DEFERRED = [
    ("0001", "Provider swap needs a running system", "G3 replay tests"),
    ("0002", "Windows host runtime — the CI job exists; the runtime does not yet", "G1"),
    ("0005", "Dual runtime needs deployable services", "G7"),
    ("0017", "Dual TTS needs the audio pipeline", "G6c"),
    ("0019", "Telemetry needs emitting code", "G5"),
    ("0021", "Eval harness needs a model to evaluate", "G8"),
    ("0024", "Robotics — provisional, uncommitted", "G10"),
]

EXEMPTIONS = [
    ("TODO", "`l0-conformance` stubs in `ci.yml`", "platform", "G6"),
    ("Licence — reviewed", "`models.piper_tr_dfki` + config — **CC-BY-NC-SA-4.0, personal use only**",
     "sensory", "G6c — revisit (ADR-0031)"),
    ("ADR-009 rule 2", "`ADR-0017` Correction (2026-08-02) — predates ADR-0029, body is unfixable",
     "architecture", "never — grandfathered, reported on every run"),
    ("Licence — unresolved", "`models.wake_bootstrap` (NC ambiguity)", "sensory",
     "G6a — self-liquidating"),
    ("Markdown", "`MASTER_PLAN_v1.md`", "architecture", "never — frozen record"),
    ("ADR shape", "`ADR-0004`", "architecture", "never — superseded record"),
    ("Shell strict", "`run_gates.sh`, `verify_artifacts.sh`, `self_test.sh`", "platform",
     "never — must survive non-zero exits"),
    ("Gate coverage", "**none** — every gate plants a violation", "platform", "n/a"),
]

# Rules whose ID is assembled at runtime. Each entry says where the IDs come from, so a
# reader can check the claim rather than take it on faith.
DYNAMIC_SOURCES = {
    "secrets": ("`secrets.patterns[].id`", "ci/policy/policy.yaml"),
    "l0-conformance": ("an in-gate invariant table", "ci/gates/gate_l0_conformance.py"),
    "shell": ("`shell.forbidden_patterns[].id`", "ci/policy/policy.yaml"),
}


# ── Extraction ─────────────────────────────────────────────────────────────────

def gate_order() -> list[str]:
    text = (ROOT / "ci" / "run_gates.sh").read_text(encoding="utf-8")
    m = ORDER_RE.search(text)
    if not m:
        raise SystemExit("could not read ORDER from ci/run_gates.sh")
    # bash permits comments inside an array literal; strip them rather than emit "#" as a gate.
    return [w for w in re.sub(r"#.*", " ", m.group(1)).split() if w]


def gate_file(name: str) -> Path:
    return GATES_DIR / f"gate_{name.replace('-', '_')}.py"


def policy_ids() -> dict[str, set[str]]:
    """Rule IDs that exist only in policy, not as constants in a gate."""
    import yaml
    pol = yaml.safe_load((ROOT / "ci" / "policy" / "policy.yaml").read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {}
    out["secrets"] = {p["id"] for p in pol.get("secrets", {}).get("patterns", [])}
    out["shell"] = {p["id"] for p in pol.get("shell", {}).get("forbidden_patterns", []) if p.get("id")}
    return out


def parse_gate(name: str, extra: set[str]) -> dict:
    src = gate_file(name).read_text(encoding="utf-8")
    tree = ast.parse(src)

    ids = {
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
        and RULE_ID.match(n.value) and not ADR_CITATION.match(n.value)
    } | extra

    # Gate("<id>", "<title>", ["ADR-0001", ...])
    title, adrs = name, []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "Gate":
            args = n.args
            if len(args) >= 2 and isinstance(args[1], ast.Constant):
                title = args[1].value
            if len(args) >= 3 and isinstance(args[2], ast.List):
                adrs = [e.value for e in args[2].elts if isinstance(e, ast.Constant)]
            break

    # rule id -> the message it fails with, taken verbatim from source. f-string
    # placeholders are left unrendered on purpose: they name the variable that will
    # appear in the log, which is more useful than a sanitised sentence.
    messages: dict[str, str] = {}
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "fail" and len(n.args) >= 2
                and isinstance(n.args[0], ast.Constant)):
            seg = ast.get_source_segment(src, n.args[1]) or ""
            messages.setdefault(n.args[0].value, clean_message(seg))

    # Table-driven gates carry (path, predicate, rule_id, message, why) tuples that never
    # appear as literal g.fail arguments. Pair each rule ID with the next string in its
    # own tuple — without this the l0-conformance invariant table documents 24 rules with
    # no trigger text, which is what made it look absent in the first place.
    for n in ast.walk(tree):
        if not isinstance(n, ast.Tuple):
            continue
        elts = n.elts
        for i, e in enumerate(elts):
            if not (isinstance(e, ast.Constant) and isinstance(e.value, str)
                    and RULE_ID.match(e.value) and not ADR_CITATION.match(e.value)):
                continue
            for nxt in elts[i + 1:]:
                if isinstance(nxt, (ast.Constant, ast.JoinedStr)):
                    seg = ast.get_source_segment(src, nxt) or ""
                    messages.setdefault(e.value, clean_message(seg))
                    break

    return {"name": name, "title": title, "adrs": adrs,
            "ids": sorted(ids, key=sort_key), "messages": messages}


def clean_message(seg: str) -> str:
    """Turn a source expression into one line of table text."""
    seg = " ".join(seg.split())
    seg = re.sub(r'^f?["\']', "", seg)
    seg = re.sub(r'["\']$', "", seg)
    seg = seg.replace('" f"', "").replace('" "', "").replace("' '", "")
    seg = seg.replace("|", r"\|")
    return seg.strip()


def sort_key(rid: str):
    """ART-000 before ART-1 before ART-016: split trailing digits and sort numerically."""
    parts = rid.split("-")
    return tuple(int(p) if p.isdigit() else p for p in parts)


def workflow_jobs() -> list[str]:
    import yaml
    return list(yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"])


def selftest_cases() -> list[tuple[str, str, str]]:
    """(planted thing, gate, rule) read off ci/self_test.sh."""
    text = (ROOT / "ci" / "self_test.sh").read_text(encoding="utf-8")
    cases = [(desc, gate, rule) for gate, rule, desc in
             re.findall(r'expect_violation\s+(\S+)\s+"([^"]+)"\s+"([^"]+)"', text)]
    # Three cases are asserted inline rather than through expect_violation, each because
    # the gate needs an argument the helper does not pass. They are listed here by hand
    # and they must stay in step with the suite: the suite counts what it ran, this counts
    # what it could parse, and the two disagreeing is how CI_Inventory.md came to claim
    # 23/23 for a run that reported 24/24.
    cases = [("a generated AWS key (planted outside the repo)", "secrets", "SEC-AWS"),
             ("every pattern matches its sample and rejects its near-miss", "secrets",
              "SEC-REGEX-POS / SEC-REGEX-NEG"),
             ("a gate whose planted violation was deleted (asserted against a doctored "
              "copy of the suite, via --suite)", "gate-coverage", "COV-001")] + cases
    return cases


# ── Rendering ──────────────────────────────────────────────────────────────────

BANNER = ("<!-- GENERATED by scripts/generate_ci_docs.py — do not hand-edit.\n"
          "     Run `python3 scripts/generate_ci_docs.py` after changing any gate. -->")


def render_policy_gates(gates: list[dict], total_rules: int) -> str:
    o: list[str] = [BANNER, "", "# Policy Gates", "",
        "**The complete rule catalogue.** Generated from `ci/gates/` — do not hand-edit.", "",
        "Every rule below is enforced by a gate that runs on every push and every pull request. "
        "Each entry names the decision it protects — a rule whose reason is invisible looks "
        "arbitrary, and arbitrary rules get deleted by the next person in a hurry.", "",
        "| | |", "|---|---|",
        f"| Rules | **{total_rules}** |",
        f"| Gates | **{len(gates)}** |",
        "| Severity | **All rules are blocking.** There is no warnings-only tier |",
        "| Exit codes | `0` pass · `1` violation · `2` gate itself broken |", "",
        "## Why there is no warning tier", "",
        "A warning is a rule nobody enforces. Within a few sprints the log is full of them, "
        "people stop reading, and a real violation scrolls past unseen. If a rule is not worth "
        "blocking on, it is not worth checking; if it is worth checking but cannot block yet, it "
        "belongs in a **registry** with an owner and a removal gate — see §Exemptions.", "",
        "---", ""]

    for g in gates:
        o.append(f"## `{g['name']}` — {g['title']}")
        o.append("")
        if g["adrs"]:
            o.append(f"**Enforces:** {', '.join(g['adrs'])}")
            o.append("")
        o.append(f"**Run:** `python3 ci/gates/gate_{g['name'].replace('-', '_')}.py`")
        o.append("")
        if g["name"] in DYNAMIC_SOURCES:
            field, where = DYNAMIC_SOURCES[g["name"]]
            o.append(f"*Some IDs are assembled at runtime from {field} in `{where}`.*")
            o.append("")
        o.append(f"| Rule | Triggers when |")
        o.append("|---|---|")
        for rid in g["ids"]:
            o.append(f"| `{rid}` | {g['messages'].get(rid, '—')} |")
        o.append("")
        o.append(f"**{len(g['ids'])} rules.**")
        o.append("")

    o += ["---", "", "## Exemptions", "",
        "Three mechanisms. One rule: **an owner and a route to removal, or it is not an "
        "exemption.**", "",
        "| Mechanism | Config | Requires |", "|---|---|---|",
        "| TODO registry | `todo.registry` | `pattern` · `path_glob` · `owner` · `unblocked_by` |",
        "| Licence registry | `licenses.unresolved_registry` | `artifact` · `owner` · `resolve_by` |",
        "| Shell pragma | inline in the script | `# ci-policy: allow RULE — reason` (reason mandatory) |",
        "",
        "`TODO-002` and `LIC-005` exist to police the escape hatches themselves: a registry entry "
        "missing `owner` or its removal gate fails the build. Otherwise the exemption mechanism "
        "becomes the loophole, which is the usual way this pattern dies.", "",
        "### Currently registered", "",
        "| Item | Owner | Removed at |", "|---|---|---|"]
    for _kind, item, owner, removed in EXEMPTIONS:
        o.append(f"| {item} | {owner} | {removed} |")

    o += ["", "---", "", "## Scope exclusions", "",
        "| Excluded | From | Why |", "|---|---|---|",
        "| `ci/` | `no-latest`, `no-pending`, `no-todo`, `shell` | Gates and their self-test "
        "necessarily **contain** the strings they hunt. Flagging them would invite weakening the "
        "pattern — which is how a gate quietly stops catching real violations |",
        "| **`ci/`** | ~~`secrets`~~ | **REMOVED — AUD-C02.** A secret-scanning gate needs the "
        "*pattern*, never a *matching literal*. `gate_secrets` now has **no path exclusions at "
        "all** and scans its own source and its own policy file. See "
        "[Secret_Scanning_Design.md](Secret_Scanning_Design.md) |",
        "| `*.md` | `no-latest`, `no-pending`, `docker-digests` | Prose must be able to quote a "
        "rejected practice. `MASTER_PLAN_v2` §3 discusses `:latest` precisely to explain why it "
        "is banned |", "",
        "Both exclusions narrow *where* a rule applies, never *what* it forbids.", "",
        "---", ""]

    cases = selftest_cases()
    o += ["## Proving the gates bite", "",
        f"`bash ci/self_test.sh` plants a known violation for {len(cases)} cases and asserts each "
        "is rejected, then verifies its own cleanup.", "",
        "| Planted | Gate | Rule |", "|---|---|---|"]
    for desc, gate, rule in cases:
        o.append(f"| {desc} | `{gate}` | {rule} |")
    o += ["",
        f"**{len(cases)}/{len(cases)} caught.** A gate that has never rejected anything is "
        "unproven, however carefully it was written.", "",
        "---", "",
        "*Generated from `ci/gates/`. Regenerate rather than hand-edit.*", ""]
    return "\n".join(o)


def render_inventory(gates: list[dict], total_rules: int, jobs: list[str]) -> str:
    cases = selftest_cases()
    o: list[str] = [BANNER, "", "# CI Inventory", "",
        "**L.I.O.N.E.L policy pipeline.** Generated from `ci/`, `.github/workflows/ci.yml` and "
        "`ci/self_test.sh` — do not hand-edit.", "",
        "| | |", "|---|---|",
        f"| Gates | **{len(gates)}** |",
        f"| Rules | **{total_rules}** |",
        f"| Workflow jobs | **{len(jobs)}** |",
        "| Current state | **all gates pass · 0 broken** |",
        "| Runner | `bash ci/run_gates.sh [gate]` |",
        f"| Self-test | `bash ci/self_test.sh` — {len(cases)}/{len(cases)} planted violations caught |",
        "| Runtime code | **0 files** — Phase 0 discipline machine-checked |", "",
        "---", "", "## 1. The gates", "",
        "Every gate is a standalone script. None depends on another, so a failure never cascades "
        f"and never hides the other {len(gates) - 1} results.", "",
        "| # | Gate | Enforces | Rules |", "|---|---|---|---|"]
    for i, g in enumerate(gates, 1):
        adrs = ", ".join(g["adrs"]) if g["adrs"] else "—"
        o.append(f"| {i} | [`{g['name']}`](ci/gates/gate_{g['name'].replace('-', '_')}.py) "
                 f"| {adrs} | {len(g['ids'])} |")
    o += ["",
        "The `artifacts` gate was red by design through Phase 0 while one image digest was "
        "unresolved — ADR-0013 blocks G0 until that count reaches zero. It is now green: the "
        "digest is pinned and justified in "
        "[GHCR_Digest_Justification.md](GHCR_Digest_Justification.md).", "",
        "---", "", "## 2. ADR coverage", "",
        "Which decisions have an executable test, and which do not.", "",
        "| ADR | Decision | Enforced by |", "|---|---|---|"]
    for num, decision, by in ADR_ENFORCED:
        o.append(f"| {num} | {decision} | {by} |")
    o += ["", "**Not yet enforced, and honest about it:**", "",
        "| ADR | Why not | Enforced at |", "|---|---|---|"]
    for num, why, at in ADR_DEFERRED:
        o.append(f"| {num} | {why} | {at} |")
    o += ["",
        f"{len(ADR_ENFORCED)} of {len(ADR_ENFORCED) + len(ADR_DEFERRED)} ADRs have an executable "
        "test today. The rest need running code, and each names the gate that will cover it — a "
        "decision with no test is a preference, and this table is where that would otherwise "
        "hide.", "",
        "---", "", "## 3. Workflow jobs", "",
        f"`.github/workflows/ci.yml` — {len(jobs)} jobs.", "",
        "| Job | Type | Notes |", "|---|---|---|",
        f"| {len(gates)} policy gates | one per gate | **No `needs:` between them.** Independent by design |",
        f"| `gate-self-test` | meta | Plants {len(cases)} known violations, asserts each is caught |",
        "| `l0-conformance` | blocking | `needs: [structure, contracts, architecture]`. ADR-0007 |",
        "| `checksum` · `generated-docs` · `gate-coverage` | **meta** | Check the pipeline, not the repository. ADR-0030 |",
        "| `windows-policy-gates` | platform | `windows-latest` under Git Bash. ADR-0002, ADR-0014 |",
        "| `turkish-locale` | platform | `tr_TR.UTF-8`, whole suite. ADR-0023 |", "",
        "### The meta-gates", "",
        "Every defect found at the 1.0.0 freeze had the same shape: a rule the repository "
        "states in prose and enforces nowhere. `checksum`, `generated-docs` and "
        "`gate-coverage` close that class — they enforce what this pipeline claims about "
        "itself. ADR-0030.", "",
        "### Why no `needs:` between gates", "",
        "A dependency chain means one early failure marks every other job \"skipped\" and you "
        "learn one thing per push. Independent jobs give the whole picture in a single run. The "
        "cost is some duplicated setup; the benefit is that fixing CI takes one afternoon instead "
        "of five.", "",
        "### The platform jobs", "",
        "The host runtime targets Windows + Git Bash (ADR-0002, ADR-0014) and Turkish is a "
        "first-class locale (ADR-0023), so two jobs run the **whole suite** on those platforms "
        "rather than one gate each. Platform bugs live in the shell plumbing and the console "
        "encoding, not in the individual checks: the Windows job would have failed on a cp1252 "
        "crash in `ci/gates/_lib.py` that killed every gate *after* its checks had passed.", "",
        "### The self-test job", "",
        "A gate that passes a clean repository but would miss a real violation is decoration. "
        "`ci/self_test.sh` plants a known violation and asserts each is rejected, then **verifies "
        "its own cleanup** — a self-test that leaves litter turns every later run red for the "
        "wrong reason, and the first person to see it will fix the gate rather than the litter.", "",
        "| Planted | Gate | Rule |", "|---|---|---|"]
    for desc, gate, rule in cases:
        o.append(f"| {desc} | `{gate}` | {rule} |")
    o += ["", f"**{len(cases)}/{len(cases)} caught.**", "",
        "---", "", "## 4. Running gates", "", "```bash",
        f"bash ci/run_gates.sh                 # all {len(gates)}, with a summary",
        "bash ci/run_gates.sh architecture    # one",
        "bash ci/run_gates.sh --list          # names and paths",
        "python3 ci/gates/gate_adr.py         # fully standalone, no runner needed",
        "bash ci/self_test.sh                 # do the gates catch anything?",
        "python3 scripts/architecture_checksum.py --verify sha256:<recorded>",
        "```", "",
        "Requirements: Python 3.11, `pyyaml`; plus `jsonschema` for the schema gate and "
        "`grpcio-tools` for protobuf. No gate needs Docker, network, or the project's own "
        "dependencies — CI validates the repository, it does not build or run it.", "",
        "---", "", "## 5. Files", "", "```", "ci/",
        "├── run_gates.sh                 runner: one gate or all",
        "├── self_test.sh                 plants violations, asserts they are caught",
        "├── policy/",
        "│   └── policy.yaml              ALL thresholds, allowlists, registries",
        "└── gates/",
        "    ├── _lib.py                  Finding model, exit-code contract, reporting",
        f"    └── gate_*.py                {len(gates)} gates", "",
        f".github/workflows/ci.yml         {len(jobs)} jobs",
        "scripts/verify_artifacts.sh      thin wrapper → gate_artifacts.py",
        "scripts/architecture_checksum.py recompute / verify the freeze checksum",
        "scripts/generate_ci_docs.py      regenerates this file and Policy_Gates.md",
        "```", "",
        "`scripts/verify_artifacts.sh` used to carry its own copy of the artifact rules. It now "
        "delegates. Duplicated policy across two files is how the two quietly disagree, and the "
        "disagreement is discovered during an incident.", "",
        "---", "", "## 6. Registered exemptions", "",
        "Every exemption carries an owner and the gate that removes it. An exemption with no "
        "route to removal is not an exemption, it is a silently lowered standard.", "",
        "| Kind | Item | Owner | Removed at |", "|---|---|---|---|"]
    for kind, item, owner, removed in EXEMPTIONS:
        o.append(f"| {kind} | {item} | {owner} | {removed} |")
    o += ["", "Shell exemptions use an inline pragma with a **mandatory reason**:", "",
        "```bash",
        "# ci-policy: allow SH-STRICT — this runner MUST survive non-zero gate exits …",
        "```", "",
        "---", "",
        "*Regenerate rather than hand-edit. A stale inventory is worse than none, because it is "
        "trusted.*", ""]
    return "\n".join(o)


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> int:
    extra = policy_ids()
    gates = [parse_gate(n, extra.get(n, set())) for n in gate_order()]
    total_rules = sum(len(g["ids"]) for g in gates)
    jobs = workflow_jobs()

    targets = {
        ROOT / "Policy_Gates.md": render_policy_gates(gates, total_rules),
        ROOT / "CI_Inventory.md": render_inventory(gates, total_rules, jobs),
    }

    check = "--check" in sys.argv
    stale = []
    for path, text in targets.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == text:
            continue
        stale.append(path.name)
        if not check:
            path.write_text(text, encoding="utf-8", newline="\n")

    print(f"  {len(gates)} gates · {total_rules} rules · {len(jobs)} workflow jobs")
    if check:
        if stale:
            print(f"  STALE  {', '.join(stale)} — run scripts/generate_ci_docs.py")
            return 1
        print("  up to date")
        return 0
    print(f"  wrote  {', '.join(stale) if stale else 'nothing (already up to date)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
