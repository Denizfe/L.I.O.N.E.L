#!/usr/bin/env python3
"""Reader for the preflight table.  Support code for `scripts/check_env.sh`.

WHY THIS IS A SEPARATE FILE
    `check_env.sh` is the entrypoint MASTER_PLAN_v1 §1.2 names, and it stays a shell
    script because the host runtime is Git Bash (ADR-0002). But it needs to read YAML
    and JSON, and embedding that as `python3 -c '...'` inside a shell script means two
    quoting regimes fighting over the same backslashes — the exact failure that put
    CRLF into two checksum-set files in the 1.4.0 session. One file each, and neither
    has to quote the other.

    It prints TAB-separated rows and nothing else, so the shell can `read -r` them.
    It resolves no secrets and prints no value that could be one: `pat-resolves`
    answers yes or no through its exit code, and the credential never leaves
    `SecretStr` (ADR-0015).

EXIT CODES
    0  the answer is yes / the rows follow
    1  the answer is no (used by `pat-resolves`)
    3  the table is missing or malformed — `check_env.sh` turns this into its own
       exit 2, "the preflight is broken", which is a different job from "the
       environment is wrong"
"""
import json
import sys
from pathlib import Path

# Two Windows defaults, both of which have already cost this repository a day.
#
# cp1252 console: the `why` strings in policy.yaml are full of em dashes, and
# `ci/gates/_lib.py` carries the same reconfigure for the same reason — every gate
# used to die in its own reporter, AFTER passing its checks.
#
# CRLF on stdout: Python translates the newline character to os.linesep on write,
# so every TSV row
# reached the shell with a trailing CR welded onto its last field. `read -r` keeps
# it, `[[ -d "$path" ]]` then says a directory that plainly exists does not, and
# the preflight reports a defect that is its own. newline="" turns the translation
# off. Same class as the CRLF that contaminated two checksum-set files at 1.4.0.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace", newline="")
    except (AttributeError, ValueError):  # pragma: no cover - very old interpreters
        pass

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "ci" / "policy" / "policy.yaml"
REGISTRY = ROOT / "config" / "capabilities.registry.json"


def _flat(text: str) -> str:
    """One line, collapsed. A `why` that wraps would break the TSV contract."""
    return " ".join(str(text).split())


def _preflight() -> dict:
    import yaml
    doc = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    section = (doc or {}).get("preflight")
    if not isinstance(section, dict):
        sys.exit(3)
    return section


def _registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]


def _is_host_path(value: str) -> bool:
    """A drive-lettered, forward-slashed absolute path — `C:/...`.

    That is the only shape a Windows host path takes in this repository
    (ADR-0002 forbids backslashes: Bash would eat them as escapes), and the only
    shape whose existence can be checked without guessing.
    """
    return len(value) > 3 and value[1] == ":" and value[2] == "/"


def _declared_host_paths():
    """Every absolute host path the configuration declares, wherever it lives.

    Both places are scanned deliberately. The stale `Desktop/L.I.O.N.E.L` root was
    written in TWO files, and a check that read only the capability registry would
    have fixed one of them and reported success.
    """
    for name, spec in _registry().items():
        for arg in spec.get("args") or []:
            if _is_host_path(arg):
                yield f"cap:{name}", arg

    import tomllib
    for toml_path in sorted((ROOT / "config").rglob("*.toml")):
        doc = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        rel = toml_path.relative_to(ROOT).as_posix()
        for section, body in doc.items():
            if not isinstance(body, dict):
                continue
            for key, value in body.items():
                if isinstance(value, str) and _is_host_path(value):
                    yield f"{rel}:{section}.{key}", value


def cmd_tools() -> None:
    rows = _preflight().get("tools")
    if not rows:
        sys.exit(3)
    for t in rows:
        print("\t".join([t["id"], str(t["minimum"]), t["probe"], t["extract"],
                         str(t["required_at"]), _flat(t["why"])]))


def cmd_packages() -> None:
    for p in _preflight().get("python_packages", []):
        print("\t".join([p["id"], p["distribution"], str(p["required_at"]),
                         _flat(p["why"])]))


def cmd_hazards() -> None:
    """The seven-row Git Bash hazard table, each row with who enforces it.

    Printed rather than merely stored. Five of the seven were prose in a superseded
    plan for the whole of Phase 0, and prose in a plan nobody opens during setup is
    the same as no rule at all — MASTER_PLAN_v1 §2 opens by saying these "bite on
    every phase" and that "encoding them once here prevents four separate debugging
    sessions". They were encoded once. Nothing read them.
    """
    for h in _preflight().get("hazards", []):
        print("\t".join([h["id"], h["enforced_by"], _flat(h["rule"])]))


def cmd_docker_backend() -> None:
    """HAZ-DOCKER-BACKEND. Prints one of: wsl2 / other / unreachable.

    `docker --version` answers about the CLI and says nothing about whether a daemon
    is running — the preflight reported a green Docker row on a machine where nothing
    could actually be launched. This asks the daemon.
    """
    import subprocess
    try:
        r = subprocess.run(["docker", "info", "--format", "{{.KernelVersion}}"],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        print("unreachable")
        return
    kernel = (r.stdout or "").strip()
    if r.returncode != 0 or not kernel:
        print("unreachable")
    elif "wsl" in kernel.lower() or "microsoft" in kernel.lower():
        print(f"wsl2\t{kernel}")
    else:
        print(f"other\t{kernel}")


def cmd_live() -> None:
    for c in _preflight().get("live_checks", []):
        why = _flat(c["why"])
        print(f"  skip  {c['id']} — {why[:92]}")


def cmd_roots() -> None:
    for name, path in _declared_host_paths():
        print(f"{name}\t{path}")


def cmd_fs_root() -> None:
    print(_registry()["filesystem"]["args"][-1])


def cmd_gh_image() -> None:
    print(_registry()["github"]["args"][-1])


def cmd_pat_resolves() -> None:
    """Does `secret://env/GITHUB_PAT` resolve? Answered by exit code only.

    Goes through the resolver the runtime uses rather than reading the variable
    directly, so this asks the question the way the running system will ask it —
    and so nothing here ever holds the bare string.
    """
    sys.path.insert(0, str(ROOT / "src"))
    try:
        from lionel.secrets import SecretError, SecretResolver
    except ImportError:
        sys.exit(1)
    uri = _registry()["github"]["secrets"]["GITHUB_PERSONAL_ACCESS_TOKEN"]
    try:
        SecretResolver().resolve(uri)
    except SecretError:
        sys.exit(1)
    sys.exit(0)


COMMANDS = {
    "tools": cmd_tools,
    "packages": cmd_packages,
    "live": cmd_live,
    "hazards": cmd_hazards,
    "docker-backend": cmd_docker_backend,
    "roots": cmd_roots,
    "fs-root": cmd_fs_root,
    "gh-image": cmd_gh_image,
    "pat-resolves": cmd_pat_resolves,
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(f"usage: {Path(__file__).name} {{{'|'.join(COMMANDS)}}}", file=sys.stderr)
        sys.exit(3)
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
