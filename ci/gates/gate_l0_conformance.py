#!/usr/bin/env python3
"""GATE: L0 offline conformance.  ADR-0007 — the keystone.

REPLACES THE STUB. The previous job ran two `echo` statements, exited 0, and reported a
green checkmark for asserting nothing. A green vacuous gate is worse than an absent one:
an absent gate is visibly missing, a hollow one is indistinguishable from a passing one.

ADR-0007: "A change that improves L2/L3 while breaking L0 is a REJECTED change, not a
tradeoff." That sentence is worth nothing without a job that goes red. This is the job.

EIGHT INVARIANTS
  I1  offline-only operation          L0 tier declares and configures no network
  I2  no outbound network deps        nothing selectable at L0 requires the network
  I3  no hidden shell execution       ADR-0011, checked across the runtime surface
  I4  no forbidden providers          L0 never selects a requires_network provider
  I5  no mutable image tags           anything L0-reachable is digest-pinned
  I6  artifact lock compliance        every L0-PATH artifact is RESOLVED
  I7  contract compatibility          L0 contracts present, valid, plane-clean
  I8  architecture policy compliance  the ADR invariants the L0 loop depends on

SELF-ENFORCEMENT
  The gate installs a NETWORK EGRESS GUARD on itself before running any check. Every
  socket connect attempt raises and is recorded as a violation. So "no outbound network
  dependencies" is ENFORCED DURING THIS GATE'S OWN EXECUTION, not merely asserted about
  someone else's code. A check that needed the network could not pass silently.

VACUOUS-CHECK HONESTY
  Phase 0 has no runtime code, so some invariants have nothing to examine yet. Each
  result is labelled SUBSTANTIVE or VACUOUS and both counts are reported. A gate that
  reports "8 checks passed" when six examined nothing is the failure mode audit finding
  AUD-M04 identified; this gate refuses to do that.

USAGE
    python3 ci/gates/gate_l0_conformance.py
    python3 ci/gates/gate_l0_conformance.py --root DIR      # negative testing
    python3 ci/gates/gate_l0_conformance.py --prove-egress-guard
"""
from __future__ import annotations

import json
import re
import socket
import sys
from pathlib import Path

from _lib import Gate, load_policy, read_text, ROOT, gate_error, yellow, dim

# ── Network egress guard ─────────────────────────────────────────────────────

_EGRESS: list[str] = []
_real_connect = socket.socket.connect
_real_create = socket.create_connection


class EgressAttempt(RuntimeError):
    pass


def _install_egress_guard() -> None:
    """Any outbound connection from this point raises and is recorded.

    L0 means offline. A gate that verifies offline operation must not itself reach the
    network, and the cheapest way to guarantee that is to make it impossible.
    """
    def blocked_connect(self, address, *a, **k):
        _EGRESS.append(f"socket.connect({address!r})")
        raise EgressAttempt(f"outbound connection blocked: {address!r}")

    def blocked_create(address, *a, **k):
        _EGRESS.append(f"socket.create_connection({address!r})")
        raise EgressAttempt(f"outbound connection blocked: {address!r}")

    socket.socket.connect = blocked_connect          # type: ignore[method-assign]
    socket.create_connection = blocked_create        # type: ignore[assignment]


# ── helpers ──────────────────────────────────────────────────────────────────

def _toml_value(text: str, key: str) -> str | None:
    m = re.search(rf"^\s*{re.escape(key)}\s*=\s*(.+?)\s*(?:#.*)?$", text, re.M)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'").rstrip(",")


def main() -> None:
    argv = sys.argv[1:]
    root = ROOT
    if "--root" in argv:
        root = Path(argv[argv.index("--root") + 1]).resolve()
        if not root.is_dir():
            gate_error(f"--root is not a directory: {root}")

    _install_egress_guard()

    if "--prove-egress-guard" in argv:
        try:
            socket.create_connection(("example.invalid", 80), timeout=1)
            print("  GUARD FAILED — connection was not blocked")
            sys.exit(2)
        except EgressAttempt as e:
            print(f"\n  egress guard active: {e}")
            print(f"  recorded attempts: {_EGRESS}\n")
            sys.exit(0)

    p = load_policy()
    if "l0" not in p:
        gate_error("policy.yaml has no `l0:` section")
    cfg = p["l0"]
    g = Gate("l0-conformance", "L0 offline conformance",
             ["ADR-0007", "ADR-0011", "ADR-0013", "ADR-0006", "ADR-0012"])

    substantive = 0
    vacuous: list[str] = []

    def rel(q: Path) -> str:
        try:
            return str(q.relative_to(root)).replace("\\", "/")
        except ValueError:
            return str(q)

    # ── I1 · offline-only operation ──────────────────────────────────────────
    tier = root / cfg["tier_file"]
    g.check()
    if not tier.is_file():
        g.fail("L0-OFFLINE-001", f"L0 tier config missing: `{cfg['tier_file']}`",
            "ADR-0007: L0 is the offline autonomy guarantee. Without its config there is "
            "nothing to assert offline behaviour against, and the guarantee is a slogan.",
            f"Create `{cfg['tier_file']}`.")
    else:
        substantive += 1
        ttext = read_text(tier)
        for key, want in cfg["required_settings"].items():
            g.check()
            got = _toml_value(ttext, key)
            if got != want:
                g.fail("L0-OFFLINE-002", f"L0 `{key}` is `{got}`, must be `{want}`",
                    "ADR-0007: a tier that permits network access is not the autonomy "
                    "guarantee — it is a configuration that happens to work offline today, "
                    "which is exactly how the guarantee erodes.",
                    f"Set `{key} = {want}` in {cfg['tier_file']}.", rel(tier))

        # every L0 service must be in-process; a URL is a network hop
        placement = cfg["required_service_placement"]
        for m in re.finditer(r"^\s*(memory|brain|stt|tts)\s*=\s*\"([^\"]+)\"", ttext, re.M):
            svc, val = m.group(1), m.group(2)
            g.check()
            if val != placement:
                g.fail("L0-OFFLINE-003", f"L0 service `{svc}` is `{val}`, must be `{placement}`",
                    "ADR-0005: at L0 every cluster service runs in-process. A URL means a "
                    "socket, and a socket means L0 is not offline.",
                    f"Set `{svc} = \"{placement}\"` in the L0 tier config.", rel(tier), m.start())

    # ── I4 · no forbidden providers ──────────────────────────────────────────
    g.check()
    if tier.is_file():
        ttext = read_text(tier)
        prov = _toml_value(ttext, "provider")
        if prov in cfg["forbidden_providers"]:
            g.fail("L0-PROVIDER-001", f"L0 selects network provider `{prov}`",
                "ADR-0007: a requires_network provider at L0 breaks the offline guarantee. "
                "This is precisely the erosion the ladder exists to prevent — nobody decides "
                "to abandon offline operation, it stops being true one config at a time.",
                "Use a local provider (ollama / llamacpp) at L0.", rel(tier))
        else:
            substantive += 1

    # ── I2 · no outbound network dependencies ────────────────────────────────
    reg = root / "config/capabilities.registry.json"
    g.check()
    if not reg.is_file():
        g.fail("L0-NETDEP-001", "capabilities registry missing",
            "Without it, nothing can be verified about which capabilities L0 admits.",
            "Create config/capabilities.registry.json.")
    else:
        substantive += 1
        try:
            caps = json.loads(read_text(reg)).get("capabilities", {})
        except json.JSONDecodeError as e:
            g.fail("L0-NETDEP-002", f"capabilities registry is not valid JSON: {e.msg}",
                "An unparseable registry cannot be checked, and would fail at host startup.",
                "Fix the JSON.", rel(reg), e.lineno)
            caps = {}
        net_caps, undeclared = [], []
        for name, c in caps.items():
            # ADR-0007's exclusion can only be enforced against a DECLARED fact. A
            # capability that says nothing is not "local by default" — it is unverified.
            g.check()
            if "requires_network" not in c:
                undeclared.append(name)
                g.fail("L0-NETDEP-004",
                    f"capability `{name}` does not declare `requires_network`",
                    "ADR-0007 excludes network-dependent capabilities at L0. That exclusion is "
                    "unenforceable against an undeclared field: absence is not a declaration of "
                    "`false`. Today this exclusion exists only in prose, which is exactly what "
                    "the previous stubbed gate concealed.",
                    f"Add `\"requires_network\": true|false` to `{name}` in the registry.",
                    rel(reg))
            if c.get("requires_network"):
                net_caps.append(name)
                g.check()
                if c.get("enabled", True) is not False:
                    g.fail("L0-NETDEP-003",
                        f"capability `{name}` declares requires_network and is not disabled",
                        "ADR-0007 excludes requires_network capabilities at L0. Leaving one "
                        "enabled means the L0 host would try to start it and either fail or "
                        "reach the network — both break the guarantee.",
                        f"Set `\"enabled\": false` on `{name}`, or resolve it into an "
                        "L0-safe form.", rel(reg))
        if net_caps:
            g.note(f"declared network-dependent, excluded from L0: {', '.join(net_caps)}")
        if undeclared:
            g.note(f"{len(undeclared)} capability(ies) with UNDECLARED network status: "
                   f"{', '.join(undeclared)}")

    # ── I3 · no hidden shell execution ───────────────────────────────────────
    pats = [re.compile(x) for x in cfg["shell_execution_patterns"]]
    scanned = 0
    for surface in cfg["runtime_surface"]:
        d = root / surface
        if not d.is_dir():
            continue
        for q in sorted(d.rglob("*")):
            if not q.is_file() or q.suffix not in {".py", ".json", ".toml", ".yaml", ".yml"}:
                continue
            scanned += 1
            for i, line in enumerate(read_text(q).splitlines(), 1):
                if line.lstrip().startswith(("#", "//")):
                    continue
                for rx in pats:
                    if rx.search(line):
                        g.check()
                        g.fail("L0-SHELL-001", f"shell execution in the runtime surface: `{rx.pattern}`",
                            "ADR-0011 abolished arbitrary shell execution. At L0 the agent reads "
                            "local documents with no network to exfiltrate through — but shell "
                            "access turns injected text into code execution on the host, which "
                            "is the whole machine.",
                            "Express the capability as a typed tool over a closed set of values.",
                            rel(q), i)
    g.check()
    if scanned == 0:
        vacuous.append("I3 no-hidden-shell — runtime surface is empty (Phase 0 has no code)")
    else:
        substantive += 1
        g.note(f"shell scan: {scanned} runtime-surface files examined")

    # ── I5 · no mutable image tags in L0-reachable config ────────────────────
    mut = "|".join(re.escape(t) for t in cfg["mutable_tags"])
    img = re.compile(rf"([A-Za-z0-9._\-/]+):({mut})\b")
    checked_cfg = 0
    for relp in cfg["l0_reachable_config"]:
        q = root / relp
        if not q.is_file():
            continue
        checked_cfg += 1
        for i, line in enumerate(read_text(q).splitlines(), 1):
            if line.lstrip().startswith(("#", "//")) or "@sha256:" in line:
                continue
            m = img.search(line)
            if m:
                g.check()
                g.fail("L0-LATEST-001", f"mutable tag `:{m.group(2)}` on `{m.group(1)}`",
                    "ADR-0013: a tag is a movable pointer. At L0 a mutable reference is worse "
                    "than elsewhere — there is no network to re-pull from, so the image you "
                    "have is whatever was cached, and reproducibility is gone.",
                    "Pin by digest: `repo@sha256:…`.", relp, i)
    g.check()
    if checked_cfg:
        substantive += 1
        g.note(f"image-tag scan: {checked_cfg} L0-reachable config files")

    # ── I6 · artifact lock compliance for L0-PATH artifacts ──────────────────
    lock = root / "artifacts.lock.yaml"
    g.check()
    if not lock.is_file():
        g.fail("L0-ARTIFACT-001", "artifacts.lock.yaml missing",
            "ADR-0013: L0 cannot run from artifacts it cannot verify.",
            "Create the lockfile.")
    else:
        substantive += 1
        import yaml
        try:
            lk = yaml.safe_load(read_text(lock)) or {}
        except Exception as e:
            g.fail("L0-ARTIFACT-002", f"lockfile is not valid YAML: {e}",
                "Unparseable lockfile means nothing is verifiable.", "Fix the YAML.", "artifacts.lock.yaml")
            lk = {}

        # An artifact is OFF the L0 path only if it backs a requires_network capability.
        net_refs = set()
        if reg.is_file():
            try:
                for c in json.loads(read_text(reg)).get("capabilities", {}).values():
                    if c.get("requires_network"):
                        net_refs.update(re.findall(r"[a-z0-9.\-]+/[A-Za-z0-9._\-/]+",
                                                   " ".join(c.get("args", []))))
            except Exception:
                pass

        off_path, unresolved_on_path = [], []
        for sec in ("models", "images", "source"):
            for name, a in (lk.get(sec) or {}).items():
                if a.get("status") == "NOT_YET_BUILT":
                    continue
                ref = str(a.get("ref") or "")
                is_net = any(ref and ref in nr for nr in net_refs) or bool(a.get("requires_network"))
                if is_net:
                    off_path.append(f"{sec}.{name}")
                    continue
                if a.get("status") == "RESOLVED":
                    g.check()
                    continue
                unresolved_on_path.append(f"{sec}.{name}")
                g.check()
                # An unresolved artifact whose network status nothing declares is a
                # DIFFERENT defect from one known to be on the offline path. Saying so
                # precisely is the difference between a gate you act on and one you argue with.
                backing = any(ref and ref in " ".join(str(c.get("args", "")))
                              for c in caps.values() for _ in [0]) if ref else False
                if ref and undeclared:
                    g.fail("L0-ARTIFACT-004",
                        f"cannot prove `{sec}.{name}` is off the L0 path, and it is {a.get('status')}",
                        "ADR-0007 excludes requires_network artifacts from L0, but no capability "
                        "in the registry declares that field — so the exclusion is asserted in "
                        "prose and nowhere machine-readable. An unpinned artifact of unknown "
                        "reachability must be treated as reachable.",
                        f"Declare `requires_network` on the capability backing `{ref}`, or "
                        "resolve the pin.", "artifacts.lock.yaml")
                else:
                    g.fail("L0-ARTIFACT-003",
                        f"L0-path artifact `{sec}.{name}` is {a.get('status')}",
                        "ADR-0007 + ADR-0013: L0 runs entirely from local artifacts. An "
                        "unpinned artifact on the offline path means the offline path is not "
                        "reproducible, which is the guarantee itself.",
                        "Resolve the pin, or declare the artifact off the L0 path.",
                        "artifacts.lock.yaml")
        if off_path:
            g.note(f"artifacts off the L0 path (network-backed, excluded by ADR-0007): "
                   f"{', '.join(off_path)}")

    # ── I7 · contract compatibility ──────────────────────────────────────────
    missing = [c for c in cfg["required_contracts"] if not (root / c).is_file()]
    g.check()
    if missing:
        g.fail("L0-CONTRACT-001", f"L0 contracts missing: {missing}",
            "The L0 turn loop depends on these shapes. A missing contract means the offline "
            "path has no defined interface to conform to.",
            "Restore the contract files.")
    else:
        substantive += 1

    for c in cfg["required_contracts"]:
        q = root / c
        if not q.is_file():
            continue
        g.check()
        try:
            json.loads(read_text(q))
        except json.JSONDecodeError as e:
            g.fail("L0-CONTRACT-002", f"`{c}` is not valid JSON: {e.msg}",
                "An unparseable contract validates nothing.", "Fix the syntax.", c, e.lineno)

    # ADR-0006: the control plane never carries media payload
    for dname in cfg["control_plane_dirs"]:
        d = root / dname
        if not d.is_dir():
            continue
        for q in sorted(d.rglob("*.json")):
            txt = read_text(q)
            for key in cfg["media_payload_keys"]:
                if f'"{key}"' in txt:
                    g.check()
                    ln = next((i for i, l in enumerate(txt.splitlines(), 1) if f'"{key}"' in l), None)
                    g.fail("L0-CONTRACT-003",
                        f"media payload key `{key}` in a control-plane contract",
                        "ADR-0006: PCM must never traverse the control plane. At L0 both planes "
                        "run in one process, so the separation is enforced only by contract — "
                        "if it rots here it rots everywhere.",
                        "Move the descriptor to contracts/media/.", rel(q), ln)

    # ── I8 · architecture policy compliance ──────────────────────────────────
    checks = [
        ("contracts/mcp/v1/policy-ruleset.schema.json",
         lambda d: d["properties"]["defaults"]["properties"]["decision"].get("const") == "deny",
         "L0-ARCH-001", "policy default is not pinned to `deny`",
         "ADR-0012: allow-by-default means a forgotten tool registration is an open door. At "
         "L0 there is no network egress, but the local filesystem is the entire machine."),
        ("contracts/mcp/v1/tool-call.schema.json",
         lambda d: "trust" in d.get("required", []),
         "L0-ARCH-002", "ToolCall does not require `trust`",
         "ADR-0012: without a trust context the Policy Engine cannot authorize anything, and "
         "the only safe default would be to deny everything."),
        ("contracts/mcp/v1/tool-result.schema.json",
         lambda d: "trust_of_output" in d.get("required", []),
         "L0-ARCH-003", "ToolResult does not require `trust_of_output`",
         "ADR-0012: a tool result is content of unknown provenance. Without a declared trust "
         "level, reading a local file launders untrusted text into a trusted turn."),
        ("contracts/events/v1/provider-request.schema.json",
         lambda d: "cancellation_token_id" in d.get("required", []),
         "L0-ARCH-004", "ProviderRequest does not require `cancellation_token_id`",
         "ADR-0025: optional cancellation is cancellation some call sites omit, and those are "
         "the ones that hang during barge-in. L0 has the tightest latency budget of any tier."),
        ("contracts/mcp/v1/memory-service.schema.json",
         lambda d: "memory.forget" in d["properties"]["tools"].get("required", []),
         "L0-ARCH-005", "`memory.forget` is not a required tool",
         "ADR-0010: a memory system without a forget path accumulates errors permanently."),
    ]
    for path, pred, rid, msg, why in checks:
        q = root / path
        if not q.is_file():
            continue
        g.check()
        try:
            ok = pred(json.loads(read_text(q)))
        except Exception:
            ok = False
        if not ok:
            g.fail(rid, msg, why, f"Restore the invariant in `{path}`.", path)
        else:
            substantive += 1

    # ADR-0018: .en models are rejected project-wide
    g.check()
    if lock.is_file() and re.search(r"ggml-[a-z0-9.\-]*\.en\.bin", read_text(lock)):
        g.fail("L0-ARCH-006", "an English-only `.en` whisper model is pinned",
            "ADR-0018: `.en` models are English-only by construction. L0 must serve Turkish "
            "offline, and a monolingual model cannot.",
            "Use a multilingual model.", "artifacts.lock.yaml")

    # ── egress verdict ───────────────────────────────────────────────────────
    g.check()
    if _EGRESS:
        g.fail("L0-EGRESS-001", f"{len(_EGRESS)} outbound connection attempt(s) during this gate",
            "ADR-0007: L0 means offline. A conformance gate that itself reaches the network "
            "cannot testify about offline operation. The guard blocked these; their presence "
            "means a check has a network dependency.",
            f"Remove the network dependency. Attempts: {_EGRESS[:3]}")
    else:
        substantive += 1
        g.note("network egress guard: active for the whole run, 0 attempts")

    # ── vacuity report ───────────────────────────────────────────────────────
    for v in vacuous:
        g.note(f"{yellow('VACUOUS')} {v}")
    g.note(f"{substantive} substantive check group(s) · {len(vacuous)} vacuous "
           f"{dim('(vacuous = nothing to examine yet at Phase 0)')}")

    g.report_and_exit()


if __name__ == "__main__":
    main()
