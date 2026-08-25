"""ADR-0027 layer 1 — the preflight table has the shape it promises.

WHAT THIS CAN AND CANNOT CHECK
    It cannot check the host. `scripts/check_env.sh` answers "is THIS machine ready",
    and the answer differs on every machine — including the CI runners, which have no
    VS Build Tools and would fail a check that asserted otherwise. Running the
    preflight in CI would be asserting something about the wrong computer.

    What is portable is the table's SHAPE, and the agreement between the table, the
    script that executes it, and the helper that reads it. Those three files drift
    apart silently: a row gains a key the script never reads, the script calls a
    helper command that was renamed, a `why` decays to "needed". Each of those is
    invisible until someone runs the preflight on a broken machine and gets a
    confusing answer at the worst possible moment.

WHY THE TABLE IS IN policy.yaml AND NOT IN THE SCRIPT
    Because there would then be two of it. MASTER_PLAN_v1 §1.1 was the first copy and
    it went stale the moment Phase 0 restructured the phases. One registry, executed
    by one script, checked here for shape.
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

SCRIPT = ROOT / "scripts" / "check_env.sh"
HELPER = ROOT / "scripts" / "_preflight_table.py"

# MASTER_PLAN_v1 §1.1, carried forward verbatim by MASTER_PLAN_v2's Phase 1 section.
# Named here so the table cannot quietly lose a row: a preflight that stops checking
# for Docker still passes, and says so, right up until G2 needs Qdrant.
V1_PREFLIGHT_TOOLS = {"git", "node", "python3", "uv", "docker", "cl"}

REQUIRED_AT = re.compile(r"^(now|G(?:10|[0-9]))$")


@unittest.skipIf(yaml is None, "pyyaml not installed (pyproject `ci` extra)")
class TestTableShape(unittest.TestCase):
    def setUp(self):
        doc = yaml.safe_load((ROOT / "ci" / "policy" / "policy.yaml").read_text(
            encoding="utf-8"))
        self.pre = doc["preflight"]

    def test_every_v1_tool_is_still_in_the_table(self):
        self.assertEqual(V1_PREFLIGHT_TOOLS, {t["id"] for t in self.pre["tools"]})

    def test_every_tool_row_is_complete(self):
        for t in self.pre["tools"]:
            with self.subTest(tool=t.get("id")):
                for key in ("id", "minimum", "probe", "extract", "required_at", "why"):
                    self.assertIn(key, t)
                self.assertRegex(str(t["required_at"]), REQUIRED_AT)

    def test_every_extract_regex_compiles_and_finds_a_version(self):
        """A regex that matches nothing turns every row into a silent MISS."""
        for t in self.pre["tools"]:
            with self.subTest(tool=t["id"]):
                rx = re.compile(t["extract"])
                self.assertTrue(rx.search("tool version 12.34.56 (build x)"),
                                f"{t['id']}: extract pattern finds no version in a "
                                f"typical --version line")

    def test_a_probe_names_the_tool_it_probes(self):
        """Guards a copy-paste that would report node's version under docker's name."""
        for t in self.pre["tools"]:
            with self.subTest(tool=t["id"]):
                self.assertEqual(t["probe"].split()[0], t["id"])

    def test_every_why_says_something(self):
        """Same standard the exemption registries hold: a reason, or it is not one."""
        rows = list(self.pre["tools"]) + list(self.pre["python_packages"]) \
            + list(self.pre["live_checks"])
        for r in rows:
            with self.subTest(row=r["id"]):
                self.assertGreaterEqual(
                    len(" ".join(r["why"].split())), 40,
                    f"{r['id']}: `why` is too short to be a reason. A row whose "
                    f"justification is 'needed' teaches the reader nothing at the "
                    f"moment they are staring at a red line.")

    def test_the_gate_dependencies_are_all_required_now(self):
        """Without grpcio-tools the protobuf gate exits 2 — a broken gate, not a pass.

        So no package the gates import may be deferred to a later phase; there is no
        such thing as a pipeline that is 21/22 green and fine.
        """
        for p in self.pre["python_packages"]:
            with self.subTest(package=p["id"]):
                self.assertEqual(p["required_at"], "now")

    def test_probes_do_not_reach_the_network(self):
        """ADR-0007. The default run must work with the cable pulled.

        Anything that dials out belongs under `live_checks`, which is opt-in and
        announces itself.
        """
        for t in self.pre["tools"]:
            with self.subTest(tool=t["id"]):
                for reaching in ("curl", "wget", "npx", "pull", "http"):
                    self.assertNotIn(reaching, t["probe"])


@unittest.skipIf(yaml is None, "pyyaml not installed (pyproject `ci` extra)")
class TestHazardTable(unittest.TestCase):
    """MASTER_PLAN_v1 §2, and the one label that must never be a hiding place.

    Every row says who enforces it. `operator` is the honest word for "nothing can
    check this from a file" — and it is exactly the word a row drifts into when
    writing the check turns out to be work. So `operator` is capped, and a row that
    claims a rule enforces it has to name a rule that exists.
    """

    # The seven rows of MASTER_PLAN_v1 §2. Named here so the table cannot shrink:
    # a hazard silently dropped is a hazard that bites on every phase, unrecorded.
    V1_HAZARDS = {"HAZ-MSYS-PATH", "HAZ-STORE-PYTHON", "HAZ-CRLF-SH",
                  "HAZ-DOCKER-BACKEND", "HAZ-HOST-MOUNT", "HAZ-TTY", "HAZ-BACKSLASH"}

    def setUp(self):
        doc = yaml.safe_load((ROOT / "ci" / "policy" / "policy.yaml").read_text(
            encoding="utf-8"))
        self.pre = doc["preflight"]
        self.hazards = self.pre["hazards"]

    def test_all_seven_rows_are_present(self):
        self.assertEqual(self.V1_HAZARDS, {h["id"] for h in self.hazards})

    def test_every_row_names_its_enforcer(self):
        for h in self.hazards:
            with self.subTest(hazard=h["id"]):
                self.assertIn("hazard", h)
                self.assertIn("rule", h)
                self.assertTrue(h.get("enforced_by"))

    def test_a_named_rule_id_actually_exists(self):
        """The drift: a row claims `SH-WHATEVER` enforces it, and nothing does.

        That reads as covered on every future audit, which is worse than reading as
        uncovered — an `operator` row at least tells the truth about itself.
        """
        known = {p["id"] for p in
                 yaml.safe_load((ROOT / "ci" / "policy" / "policy.yaml").read_text(
                     encoding="utf-8"))["shell"]["forbid_patterns"]}
        known.add("SH-CRLF")
        for gate in (ROOT / "ci" / "gates").glob("gate_*.py"):
            known.update(re.findall(r'g\.fail\(\s*"([A-Z0-9-]+)"', gate.read_text(
                encoding="utf-8")))
        for h in self.hazards:
            enforcer = h["enforced_by"]
            if enforcer in ("operator", "check_env"):
                continue
            with self.subTest(hazard=h["id"]):
                self.assertIn(enforcer, known,
                              f"{h['id']} claims `{enforcer}` enforces it, but no gate "
                              f"emits that rule id")

    def test_operator_rows_are_capped(self):
        """Four of seven were `operator` at 1.7.0; two remain, and both genuinely
        describe what a person types at a terminal. If this number grows, a check
        that could have been written was labelled unwritable instead."""
        operator_rows = [h["id"] for h in self.hazards if h["enforced_by"] == "operator"]
        self.assertLessEqual(
            len(operator_rows), 2,
            f"{operator_rows} are labelled `operator`. Every exemption in this "
            f"repository carries an owner and a route to removal; `operator` is the "
            f"one label with neither, so it is capped instead.")


class TestScriptAndTableAgree(unittest.TestCase):
    """The three files ship together, so they are checked together."""

    def setUp(self):
        self.script = SCRIPT.read_text(encoding="utf-8")

    def test_the_script_exists_and_is_strict(self):
        self.assertTrue(SCRIPT.is_file(), "MASTER_PLAN_v1 §1.2 names this file")
        self.assertRegex(self.script, r"(?m)^set -euo pipefail$")

    def test_the_script_has_lf_endings(self):
        """A CRLF .sh dies with `\\r: command not found`, and the preflight is the
        first thing a new machine runs — the worst possible place for that."""
        self.assertNotIn(b"\r\n", SCRIPT.read_bytes())

    def test_the_script_documents_all_three_exit_codes(self):
        """0 / 1 / 2 is a contract, and 1 and 2 are never collapsed."""
        for code in ("0", "1", "2"):
            self.assertRegex(self.script, rf"(?m)^#\s+{code}\s+\S")

    def test_every_helper_command_the_script_calls_exists(self):
        """The drift this exists to catch: renaming a command in one file only."""
        import _preflight_table as helper
        called = set(re.findall(r"_preflight_table\.py\"?\s+([a-z-]+)", self.script))
        self.assertTrue(called, "the script no longer calls the helper at all")
        for cmd in called:
            with self.subTest(command=cmd):
                self.assertIn(cmd, helper.COMMANDS)

    def test_no_bare_assignment_captures_a_command_that_can_fail(self):
        """`set -e` + `out="$(cmd)"` kills the script when cmd exits non-zero.

        It aborts BEFORE the next line can read `$?`, so every branch downstream that
        is reached by a failure is unreachable. In `live_check` that was skip, fail
        AND broken — the entire three-way diagnosis the preflight documents. A failing
        live check killed the run silently rather than reporting, and the only outcome
        it could ever print was `pass`.

        Twice now the bug has been that a check could not fail. The rule is: capture a
        helper's output inside an `if`, which suspends `set -e` for the assignment, or
        append `|| true` where a non-zero exit is genuinely uninteresting.

        Scoped to the helper calls, deliberately. `ROOT="$(cd ... && pwd)"` is also a
        bare assignment and should stay one — if that fails the script genuinely
        cannot continue, and aborting is the right answer. The rule applies where a
        non-zero exit is a MESSAGE, and `_preflight_table.py` is the thing in this
        script that signals by exit code.
        """
        offenders = []
        for i, line in enumerate(self.script.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or "_preflight_table.py" not in stripped:
                continue
            if not re.match(r'^(?:local\s+)?[A-Za-z_][A-Za-z0-9_]*="\$\(', stripped):
                continue          # already `if !`-guarded, or not an assignment
            if "||" in stripped:
                continue          # an explicit fallback inside the substitution
            offenders.append(f"{i}: {stripped[:70]}")
        self.assertEqual(
            [], offenders,
            "these capture a command's output with a bare assignment under `set -e`; "
            "a non-zero exit aborts the script before the result can be inspected. "
            "Wrap in `if ! VAR=\"$(...)\"; then` or append `|| true`.")

    def test_a_skipped_live_check_is_not_reported_as_a_pass(self):
        """Two live rows ARE v1.0's Phase 1 DoD, so `PASS` must not absorb a skip."""
        self.assertIn("live_skipped", self.script)
        self.assertRegex(
            self.script, r"live check\(s\) did NOT run",
            "the verdict does not distinguish a run that verified the live clauses "
            "from one that could not attempt them")

    def test_the_helper_refuses_an_unknown_command_with_exit_3(self):
        """3 means 'the table or this reader is wrong', which check_env.sh turns into
        its own exit 2. A helper that exited 1 would be reported as a bad machine."""
        r = subprocess.run([sys.executable, str(HELPER), "no-such-command"],
                           capture_output=True)
        self.assertEqual(3, r.returncode)

    @unittest.skipIf(yaml is None, "pyyaml not installed (pyproject `ci` extra)")
    def test_the_helper_emits_no_carriage_returns(self):
        """Python translates newlines to os.linesep on write, and the shell then reads
        a trailing CR as part of the last field — which made `[[ -d ]]` deny a
        directory that plainly existed. Same class as the 1.4.0 checksum contamination.
        """
        r = subprocess.run([sys.executable, str(HELPER), "tools"],
                           capture_output=True)
        self.assertEqual(0, r.returncode)
        self.assertNotIn(b"\r", r.stdout)


FAKE_SERVER = '''
import json, sys
# A server that behaves the way the GitHub MCP server behaves: it tears down on EOF,
# and it interleaves noise with its responses.
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    msg = json.loads(line)
    if msg.get("method") == "initialize":
        sys.stdout.write("a log line that is not JSON\\n")
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg["id"],
                                     "result": {"capabilities": {}}}) + "\\n")
        sys.stdout.flush()
    elif msg.get("method") == "tools/call":
        # An unrelated notification and a response to a DIFFERENT id, first.
        sys.stdout.write(json.dumps({"jsonrpc": "2.0",
                                     "method": "notifications/message"}) + "\\n")
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": 99,
                                     "result": {"content": []}}) + "\\n")
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": {
            "content": [{"type": "text", "text": "the real answer"}]}}) + "\\n")
        sys.stdout.flush()
sys.exit(0)
'''

SILENT_SERVER = '''
import sys
for line in sys.stdin:
    pass
'''


class TestMCPClient(unittest.TestCase):
    """The bug this class was written to fix, tested without a network.

    `printf '...' | server` closes stdin the moment printf finishes. A server that
    reads EOF as "the client hung up" then tears the session down before writing a
    byte of response — so the GitHub check reported "container started but get_me
    returned no login" for **every** input, including a valid credential. A check
    that cannot pass is worse than no check, and this one sits on the G1 sign-off
    path.

    These use a fake server written to behave the same way, so the properties are
    checked offline: ADR-0007's guarantee would not survive a suite that needed the
    network to test the thing that talks to the network.
    """

    def _server(self, source: str):
        import tempfile
        import _preflight_table as helper
        fh = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                         encoding="utf-8", newline="")
        fh.write(source)
        fh.close()
        self.addCleanup(lambda: Path(fh.name).unlink(missing_ok=True))
        return helper.MCPClient([sys.executable, "-u", fh.name], timeout=20)

    def test_initialize_gets_its_response(self):
        with self._server(FAKE_SERVER) as c:
            reply = c.initialize()
        self.assertIsNotNone(reply, "the client closed stdin before the server answered")
        self.assertEqual(1, reply["id"])

    def test_a_response_is_matched_by_id_not_by_arrival_order(self):
        """The fake server answers a different id first, then the real one.

        Taking the first line back would pair a request with whatever happened to be
        printed next — which for a chatty server is a log line or a notification.
        """
        import _preflight_table as helper
        with self._server(FAKE_SERVER) as c:
            c.initialize()
            reply = c.call("anything", {})
        self.assertIsNotNone(reply)
        self.assertEqual(2, reply["id"])
        self.assertEqual("the real answer", helper._result_text(reply))

    def test_a_silent_server_times_out_instead_of_hanging(self):
        """Windows cannot select() on a pipe, so a blocking readline against a wedged
        server would hang the preflight with no output and no way to tell why."""
        with self._server(SILENT_SERVER) as c:
            c.timeout = 2.0
            self.assertIsNone(c.initialize())

    def test_a_missing_command_raises_rather_than_being_reported_as_a_failure(self):
        """`npx` is `npx.cmd` on Windows and Popen finds neither from the bare name.

        It has to surface as "not on PATH", not as "the capability failed its check":
        one is an environment to fix, the other sends the reader after a bug.
        """
        import _preflight_table as helper
        with self.assertRaises(FileNotFoundError):
            helper.MCPClient(["definitely-not-a-real-command-xyzzy"])

    def test_no_shell_is_ever_used(self):
        """ADR-0011: no path from text to an interpreter, including in the preflight.

        A `shell=True` would have been the one-line fix for the npx.cmd problem,
        which is exactly why this is a test rather than a resolution to remember.

        Checked against the parsed tree, not the text. A substring search fails on
        the comment explaining why it was not used — the same shape as
        `SH-BARE-PYTHON` firing on a heading that printed the words "python
        packages". A rule that cannot tell code from prose about code will keep
        finding the documentation.
        """
        import ast
        tree = ast.parse(HELPER.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "shell":
                        self.fail(f"a `shell=` argument at line {node.lineno}; "
                                  f"ADR-0011 forbids any path from text to an interpreter")
                target = ast.unparse(node.func)
                self.assertNotIn("os.system", target)
                self.assertNotIn("popen", target.lower().replace("subprocess.popen", ""))


class TestHostPathDetection(unittest.TestCase):
    """The check that found the stale root, tested on its own."""

    def test_recognises_a_windows_host_path(self):
        import _preflight_table as helper
        self.assertTrue(helper._is_host_path("C:/Users/deniz/Projects/L.I.O.N.E.L"))
        self.assertTrue(helper._is_host_path("D:/models"))

    def test_ignores_things_that_merely_contain_a_colon(self):
        import _preflight_table as helper
        for not_a_path in ("secret://env/GITHUB_PAT", "ghcr.io/github/x@sha256:ab",
                           "stdio", "-y", "C:", ""):
            with self.subTest(value=not_a_path):
                self.assertFalse(helper._is_host_path(not_a_path))

    def test_both_declaring_files_are_scanned(self):
        """The stale root was written twice. A check that read one file would have
        fixed one of them and reported success."""
        import _preflight_table as helper
        sources = {name.split(":")[0] for name, _ in helper._declared_host_paths()}
        self.assertIn("cap", sources, "the capability registry is not being scanned")
        self.assertIn("config/lionel.toml", sources,
                      "config/lionel.toml declares project.root and is not scanned")


if __name__ == "__main__":
    unittest.main()
