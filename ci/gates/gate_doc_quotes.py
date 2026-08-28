#!/usr/bin/env python3
"""GATE: a document that quotes a file agrees with that file.  ADR-0035.

THE GAP THIS CLOSES
    ADR-0033 made count-shaped claims measurable. Its Costs section named what it did not
    close, and the G1 sign-off audit named it again from the other end: claims about what a
    file CONTAINS are checked by nobody. It cost twice in four days, with all 22 gates green
    both times:

        2026-08-24  Architecture_Freeze.md §9.11 recorded five Git Bash hazard rows as
                    "recorded in check_env.sh". Nothing was there.
        2026-08-25  ADR-0034 and §9.14 quoted the last rule of config/policy/default.toml
                    in a fenced block, both omitting its `match.any = true` line, and both
                    then argued from the absent `match`. The conclusion held. The premise
                    was not in the file.

    gate_checksum cannot help with either. It proves the architecture has not drifted from a
    recorded value; it has no opinion about whether a document DESCRIBING the architecture
    describes it correctly. Those are different claims.

WHY FENCED BLOCKS AND NOT PROSE
    This closes half the gap, deliberately, and ADR-0035 says which half. A prose claim is
    read as a summary; a fenced block is read as the file. Nobody re-opens a file to check a
    block that is right there on the page — that is the entire reason to paste one. So a
    wrong block is believed more readily than a wrong sentence, and by exactly the readers
    who are reading the document instead of the repository.

WHY PRESUMED-QUOTE RATHER THAN ANNOTATED-QUOTE
    The obvious design is opt-in: annotate a block with the file it quotes, check only the
    annotated ones. It checks the quotations someone remembered to annotate, which is the
    same class of failure one level up — the ADR-0034 misquote would have sailed through,
    because the author who quotes a rule wrongly is the author who does not annotate it.

    So a config-language block IS a quotation until it says otherwise. Saying otherwise
    costs an HTML comment carrying a reason, and QUOTE-003 makes that comment fail once it
    stops being true. That is what separates a marker from a suppression comment.

WHAT IT STILL DOES NOT COVER
    Prose. The 2026-08-24 instance above is a sentence, not a block, and this gate walks
    past it. Inline single-backtick quotations too: too short to tell a quotation from a
    name. Frozen historical documents (MASTER_PLAN_v1.md, Phase0_Blockers.md) are out of
    scope permanently — their blocks quote a repository that no longer exists, and asking
    them to agree with the present would be asking them to stop being records.
"""
import fnmatch
import re
from pathlib import Path

from _lib import Gate, ROOT, gate_error, load_policy, read_text, rel, repo_files

FENCE_OPEN = re.compile(r"^\s*```(\w+)\s*$")
FENCE_CLOSE = re.compile(r"^\s*```\s*$")


def dedent(lines: list[str]) -> list[str]:
    """Strip the common leading indent. An excerpt may sit at a different depth than the
    file it comes from — ADR-0031 quotes ci/policy/policy.yaml two levels shallower than
    the file writes it, and that is a real quotation, not a finding."""
    body = [ln for ln in lines if ln.strip()]
    if not body:
        return []
    pad = min(len(ln) - len(ln.lstrip()) for ln in body)
    return [ln[pad:] if ln.strip() else "" for ln in lines]


def corpus() -> dict[str, list[str]]:
    """Every non-markdown repository file, as right-stripped lines.

    Markdown is excluded on purpose: one document quoting another proves nothing about the
    architecture, and it would let two documents agree with each other while both disagree
    with the file."""
    out = {}
    for p in repo_files():
        if p.suffix.lower() in {".md", ".png", ".jpg", ".jpeg", ".gif", ".pyc",
                                ".onnx", ".wav", ".bin"}:
            continue
        text = read_text(p)
        if not text:
            continue
        out[rel(p)] = [ln.rstrip() for ln in text.splitlines()]
    return out


def find_in_corpus(block: list[str], files: dict[str, list[str]]) -> str | None:
    """Where this block appears verbatim and contiguously, or None.

    Contiguous on purpose. An elision syntax is a place to hide a changed line, and a check
    that accepts "the parts I chose to show you" checks nothing worth checking."""
    n = len(block)
    for path, lines in files.items():
        if n > len(lines):
            continue
        for i in range(len(lines) - n + 1):
            if lines[i] .strip() != block[0].strip():
                continue
            if dedent(lines[i:i + n]) == block:
                return f"{path}:{i + 1}"
    return None


def blocks_in(text: str, languages: set[str], marker: str):
    """Yield (line_no, language, body_lines, marker_reason_or_None) per fenced block.

    The marker is an HTML comment on the line before the fence, or the line before that if
    a blank line separates them — markdown renders both, so both must be accepted or the
    rule would depend on invisible whitespace."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = FENCE_OPEN.match(lines[i])
        if not m:
            i += 1
            continue
        lang = m.group(1).lower()
        j = i + 1
        body = []
        while j < len(lines) and not FENCE_CLOSE.match(lines[j]):
            body.append(lines[j].rstrip())
            j += 1
        if lang in languages:
            reason = None
            for back in (1, 2):
                k = i - back
                if k < 0:
                    break
                prev = lines[k].strip()
                if not prev:
                    continue
                if marker in prev:
                    reason = prev.split(marker, 1)[1]
                    reason = reason.rstrip(">").rstrip("-").strip()
                    reason = reason.lstrip("—-:").strip()
                break
            yield i + 1, lang, body, reason
        i = j + 1


def main():
    p = load_policy()
    cfg = p.get("doc_quotes")
    if not cfg:
        gate_error("policy.yaml has no `doc_quotes` section",
                   "ADR-0035 configures this gate there. A gate with no configuration "
                   "checks nothing and would pass.")

    g = Gate("doc-quotes", "Quoted files are quoted correctly", ["ADR-0035", "ADR-0033"])

    languages = {str(x).lower() for x in cfg.get("languages", [])}
    min_lines = int(cfg.get("min_lines", 2))
    marker = str(cfg.get("marker", "lionel:illustration"))
    patterns = list(cfg.get("documents", []) or [])
    if not (languages and patterns):
        gate_error("`doc_quotes` names no languages or no documents",
                   "Both are required; an empty set makes every run vacuously green.")

    docs = sorted({
        q for pat in patterns
        for q in ROOT.glob(pat) if q.is_file()
    })
    if not docs:
        gate_error("`doc_quotes.documents` matched no files",
                   f"patterns: {patterns}. A glob that matches nothing is a gate that "
                   f"checks nothing, and it would pass.")

    files = corpus()
    if not files:
        gate_error("no repository files to compare against",
                   "Nothing to quote from means every block would be a finding.")

    scanned = marked = 0
    for doc in docs:
        r = rel(doc)
        for ln, lang, body, reason in blocks_in(read_text(doc), languages, marker):
            block = dedent([b for b in body if b.strip()])
            if len(block) < min_lines:
                continue
            scanned += 1
            g.check()
            where = find_in_corpus(block, files)

            if reason is None:
                if where:
                    continue
                g.fail("QUOTE-001",
                       f"`{lang}` block matches no repository file: `{block[0][:56]}`",
                       "ADR-0035: a fenced block is read as the file, not as a summary of "
                       "it — nobody re-opens a file to check a block that is already on the "
                       "page. ADR-0034 and Architecture_Freeze.md §9.14 both quoted "
                       "config/policy/default.toml without its `match.any = true` line and "
                       "argued from the absent match; 22 gates were green.",
                       f"Correct the block to match the file, or mark it as not a "
                       f"quotation: put `<!-- {marker} — why this is not from the "
                       f"repository -->` on the line before the fence.", r, ln)
                continue

            marked += 1
            if not reason:
                g.fail("QUOTE-002",
                       f"`{marker}` on the block at line {ln} carries no reason",
                       "Every exemption in this repository carries a reason and someone "
                       "answerable for it. One with neither is not an exemption; it is a "
                       "silently lowered standard.",
                       f"Write the reason after the marker: "
                       f"`<!-- {marker} — why this is not from the repository -->`.", r, ln)
            elif where:
                g.fail("QUOTE-003",
                       f"`{marker}` on a block that DOES match `{where}`",
                       "ADR-0035: a stale escape hatch. The block is a real quotation now, "
                       "so the marker suppresses a check that would pass — and it will keep "
                       "suppressing it when the block stops matching. This is the shape "
                       "COV-003 already polices for gate coverage.",
                       "Delete the marker comment. The block verifies on its own.", r, ln)

    g.note(f"{scanned} config-language block(s) of >= {min_lines} lines "
           f"across {len(docs)} document(s), against {len(files)} repository files")
    g.note(f"{marked} marked as illustration rather than quotation")
    g.note("prose claims and inline `backtick` quotations are OUT of scope — ADR-0035 "
           "closes the half of ADR-0033's gap that can be closed mechanically, and says so")
    g.report_and_exit()


if __name__ == "__main__":
    main()
