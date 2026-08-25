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


class MCPClient:
    """A minimal stdio MCP client: spawn, initialize, call one tool, close.

    WHY THIS EXISTS INSTEAD OF A PIPELINE
        The live checks were first written as `printf '...' | server`, which looks
        right and is not. The pipe closes the moment printf finishes, and a server
        that treats EOF on stdin as "the client hung up" tears the session down
        before it has written a single byte of response. The GitHub MCP server does
        exactly that:

            session initialized
            server session disconnected
            server session ended with error: server is closing: EOF

        No JSON-RPC ever reached stdout, so the check reported "container started
        but get_me returned no login" — **which it would have reported for a
        perfectly valid credential.** A check that cannot pass is worse than no
        check: it sends the reader to debug an authentication problem that is not
        there, and this one sits on the G1 sign-off path.

        The filesystem check passed through the same pipeline, which was luck
        rather than design: Node answers before its teardown reaches the write.
        Both go through here now.

    It holds stdin open until it has what it asked for, and reads with a timeout
    on a reader thread — Windows cannot `select()` on a pipe, so a blocking
    `readline()` against a wedged server would hang the preflight forever.

    It never logs the environment it was given. The credential goes into the child
    process and nowhere else.
    """

    def __init__(self, argv: list[str], env: dict | None = None, timeout: float = 60.0):
        import os
        import queue
        import shutil
        import subprocess
        import threading

        self.timeout = timeout
        # `npx` on Windows is `npx.cmd`, which CreateProcess will not find from the
        # bare name — Popen without a shell does no PATHEXT resolution. `shell=True`
        # would fix it and is not available: ADR-0011 forbids any path from text to
        # an interpreter, and a preflight that quietly opened one would be arguing
        # against the thing it is checking. `which` does the resolution instead, and
        # execution stays argv-only.
        resolved = shutil.which(argv[0])
        if resolved is None:
            raise FileNotFoundError(argv[0])
        self._proc = subprocess.Popen(
            [resolved, *argv[1:]], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
            env={**os.environ, **(env or {})})
        self._q: "queue.Queue[str | None]" = queue.Queue()

        def pump():
            for line in self._proc.stdout:  # type: ignore[union-attr]
                self._q.put(line)
            self._q.put(None)

        threading.Thread(target=pump, daemon=True).start()
        self._next_id = 0

    def _send(self, message: dict) -> None:
        self._proc.stdin.write(json.dumps(message) + "\n")  # type: ignore[union-attr]
        self._proc.stdin.flush()                            # type: ignore[union-attr]

    def _await(self, want_id: int) -> dict | None:
        """Read until the response to `want_id` arrives, a timeout, or EOF.

        Servers interleave notifications and log lines with responses, so matching
        on the id is the only correct way to read one — taking the first line back
        would pair a request with whatever happened to be printed next.
        """
        import queue
        deadline = __import__("time").monotonic() + self.timeout
        while True:
            remaining = deadline - __import__("time").monotonic()
            if remaining <= 0:
                return None
            try:
                line = self._q.get(timeout=remaining)
            except queue.Empty:
                return None
            if line is None:
                return None
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue
            if doc.get("id") == want_id:
                return doc

    def initialize(self) -> dict | None:
        self._next_id += 1
        rid = self._next_id
        self._send({"jsonrpc": "2.0", "id": rid, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "lionel-preflight", "version": "1"}}})
        reply = self._await(rid)
        if reply is not None:
            self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return reply

    def call(self, name: str, arguments: dict) -> dict | None:
        self._next_id += 1
        rid = self._next_id
        self._send({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                    "params": {"name": name, "arguments": arguments}})
        return self._await(rid)

    def close(self) -> None:
        try:
            self._proc.stdin.close()  # type: ignore[union-attr]
        except (OSError, ValueError):
            pass
        try:
            self._proc.terminate()
            self._proc.wait(timeout=10)
        except Exception:  # pragma: no cover - best effort teardown
            try:
                self._proc.kill()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()
        return False


def _result_text(reply: dict | None) -> str:
    """The text of a tools/call result, error or not."""
    if not reply:
        return ""
    result = reply.get("result") or {}
    parts = [c.get("text", "") for c in result.get("content", []) if isinstance(c, dict)]
    return " ".join(p for p in parts if p)


def cmd_live_filesystem() -> None:
    """v1.0 Phase 1 DoD + ADR-0002 Verification, both halves.

    A server that refuses everything also refuses the escape, and a server that
    allows everything also lists the root. Either half alone proves nothing, so
    both are asserted: a file INSIDE the root must read, and a read OUTSIDE it must
    come back as an error.
    """
    spec = _registry()["filesystem"]
    argv = [spec["command"], *spec.get("args", [])]
    root = Path(spec["args"][-1])
    inside = root / ".python-version"
    outside = "C:/Windows/System32/drivers/etc/hosts"

    try:
        client = MCPClient(argv)
    except FileNotFoundError:
        print(f"skip\t`{spec['command']}` is not on PATH; the filesystem capability "
              f"cannot be launched")
        sys.exit(1)
    with client:
        if client.initialize() is None:
            print("broken\tthe filesystem server never completed an MCP handshake")
            sys.exit(3)
        in_reply = client.call("read_file", {"path": str(inside).replace("\\", "/")})
        out_reply = client.call("read_file", {"path": outside})

    in_ok = bool(in_reply) and not (in_reply.get("result") or {}).get("isError")
    out_denied = bool(out_reply) and bool((out_reply.get("result") or {}).get("isError"))

    if not in_ok:
        print(f"fail\tthe server could not read {inside.name} INSIDE its own root; "
              f"a refusal below would prove nothing")
        sys.exit(1)
    if not out_denied:
        print(f"fail\ta read of {outside} was NOT refused; the root is not a boundary")
        sys.exit(1)
    detail = " ".join(_result_text(out_reply).split())[:80]
    print(f"pass\treads inside the root, refuses outside it — {detail}")


def cmd_live_github() -> None:
    """v1.0 Phase 1 DoD: the pinned container starts and `get_me` returns a login.

    The credential is resolved through ADR-0015's resolver, handed to the child
    process, and never printed. A 401 is reported as a 401 — "no login" would send
    the reader to debug the container when the answer is "issue a new token".
    """
    sys.path.insert(0, str(ROOT / "src"))
    from lionel.secrets import SecretError, SecretResolver

    spec = _registry()["github"]
    secrets = spec.get("secrets") or {}
    env = {}
    for var, uri in secrets.items():
        try:
            env[var] = SecretResolver().resolve(uri).reveal()
        except SecretError as e:
            print(f"skip\t{uri} does not resolve ({type(e).__name__})")
            sys.exit(1)

    argv = [spec["command"], *spec.get("args", [])]
    try:
        client = MCPClient(argv, env=env)
    except FileNotFoundError:
        print(f"skip\t`{spec['command']}` is not on PATH")
        sys.exit(1)
    with client:
        if client.initialize() is None:
            print("broken\tthe container never completed an MCP handshake")
            sys.exit(3)
        reply = client.call("get_me", {})

    text = _result_text(reply)
    if reply and not (reply.get("result") or {}).get("isError"):
        try:
            login = json.loads(text).get("login", "")
        except json.JSONDecodeError:
            login = ""
        if login:
            print(f"pass\tget_me returned login {login}")
            return
        print("fail\tget_me succeeded but the response carries no login field")
        sys.exit(1)

    if "401" in text or "Bad credentials" in text:
        print("fail\t401 Bad credentials — the token is rejected by api.github.com. "
              "Expired, revoked, or not authorised for this account")
        sys.exit(1)
    if "403" in text:
        print("fail\t403 — the token authenticates but lacks the scopes get_me needs")
        sys.exit(1)
    print(f"fail\t{' '.join(text.split())[:120] or 'no response from the container'}")
    sys.exit(1)


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
    "live-filesystem": cmd_live_filesystem,
    "live-github": cmd_live_github,
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
