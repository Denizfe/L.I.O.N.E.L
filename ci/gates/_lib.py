"""Shared harness for L.I.O.N.E.L CI policy gates.

NOT RUNTIME CODE. Nothing here is imported by src/lionel/. These are repository
validation tools that run in CI and on a developer's machine.

THE EXIT-CODE CONTRACT
    0  PASS          no violations
    1  VIOLATION     the repository breaks a policy — a human must fix the repo
    2  GATE_ERROR    the gate itself could not run — a human must fix the gate

The distinction between 1 and 2 is the point. A gate that cannot run is not a
passing gate, and it is not a failing repository either. Collapsing them teaches
people to ignore red builds because "that one's just broken".

EVERY FINDING EXPLAINS ITSELF
    A gate that prints `FAIL: rule R-014` has moved the work of understanding onto
    whoever reads the log, usually at the least convenient moment. Every Finding
    therefore carries four things: what is wrong, where, WHY THE RULE EXISTS
    (with the ADR), and how to fix it.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

PASS, VIOLATION, GATE_ERROR = 0, 1, 2

# Every gate prints box-drawing characters and interpuncts. On Windows the console
# encoding defaults to cp1252, which cannot encode them, and the gate dies with a
# UnicodeEncodeError inside report_and_exit — after all its checks have passed. That
# reads as "broken gate" (exit 2) on a repository with nothing wrong with it. This is
# a Windows-first project (ADR-0002, ADR-0014), so the runner must not depend on the
# operator having exported PYTHONIOENCODING first.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # already wrapped, or not reconfigurable
        pass

ROOT = Path(__file__).resolve().parents[2]

_NO_COLOR = os.environ.get("NO_COLOR") or not sys.stdout.isatty()
def _c(code: str, s: str) -> str:
    return s if _NO_COLOR else f"\033[{code}m{s}\033[0m"
red    = lambda s: _c("31", s)
green  = lambda s: _c("32", s)
yellow = lambda s: _c("33", s)
dim    = lambda s: _c("2",  s)
bold   = lambda s: _c("1",  s)


@dataclass
class Finding:
    """One policy violation, explained well enough to act on without context."""
    rule: str                 # stable id, e.g. "ARCH-001"
    message: str              # what is wrong, in plain language
    why: str                  # WHY the rule exists — cite the ADR
    fix: str                  # what to do about it
    path: str | None = None
    line: int | None = None

    def render(self) -> str:
        loc = ""
        if self.path:
            loc = f"{self.path}" + (f":{self.line}" if self.line else "")
        out = [f"  {red('✗')} {bold(self.rule)}  {self.message}"]
        if loc:
            out.append(f"      {dim('at')}    {loc}")
        out.append(f"      {dim('why')}   {self.why}")
        out.append(f"      {dim('fix')}   {self.fix}")
        return "\n".join(out)


@dataclass
class Gate:
    """A single policy gate. Independently executable; never depends on another gate."""
    id: str
    title: str
    adr: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    checks_run: int = 0
    notes: list[str] = field(default_factory=list)

    def fail(self, rule, message, why, fix, path=None, line=None):
        self.findings.append(Finding(rule, message, why, fix, path, line))

    def note(self, msg: str):
        """Something worth surfacing that is not a violation."""
        self.notes.append(msg)

    def check(self, n: int = 1):
        self.checks_run += n

    def report_and_exit(self) -> None:
        print()
        print(bold(f"══ {self.id} · {self.title}"))
        if self.adr:
            print(dim(f"   enforces {', '.join(self.adr)}"))
        print()
        for n in self.notes:
            print(f"  {yellow('note')} {n}")
        if self.notes:
            print()
        if self.findings:
            for f in self.findings:
                print(f.render())
                print()
            print(red(f"  FAIL  {len(self.findings)} violation(s) across {self.checks_run} checks"))
            print()
            sys.exit(VIOLATION)
        print(green(f"  PASS  {self.checks_run} checks"))
        print()
        sys.exit(PASS)


def gate_error(msg: str, detail: str = "") -> None:
    """The gate itself is broken. Distinct from a repository violation."""
    print()
    print(red(bold("  GATE ERROR")) + f"  {msg}")
    if detail:
        print(f"  {dim(detail)}")
    print(dim("  This is a broken gate, not a broken repository. Exit 2."))
    print()
    sys.exit(GATE_ERROR)


def load_policy() -> dict:
    import yaml
    p = ROOT / "ci" / "policy" / "policy.yaml"
    if not p.exists():
        gate_error(f"policy file missing: {p}")
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception as e:
        gate_error(f"policy file is not valid YAML: {p}", str(e))


def repo_files(include=None, exclude_dirs=None) -> list[Path]:
    """Every tracked-ish file, minus noise. Deterministic order."""
    exclude_dirs = set(exclude_dirs or []) | {
        ".git", "node_modules", ".venv", "__pycache__", ".mypy_cache",
        ".pytest_cache", ".ruff_cache", "models", "data", "logs", "backups",
        "vendor", ".claude",
    }
    out = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in exclude_dirs for part in p.relative_to(ROOT).parts):
            continue
        if include and p.suffix not in include:
            continue
        out.append(p)
    return sorted(out)


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def load_json(p: Path):
    try:
        return json.loads(read_text(p))
    except Exception as e:
        gate_error(f"invalid JSON: {rel(p)}", str(e))


def load_yaml(p: Path):
    import yaml
    try:
        return yaml.safe_load(read_text(p))
    except Exception as e:
        gate_error(f"invalid YAML: {rel(p)}", str(e))
