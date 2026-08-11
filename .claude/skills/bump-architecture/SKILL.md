---
name: bump-architecture
description: Recompute the architecture checksum, record it in Architecture_Freeze.md, regenerate the derived documents, verify from a clean clone, and tag a new architecture version. Use after any change to the checksum set.
disable-model-invocation: true
---

# Bump the architecture version

This ritual has been performed four times (1.0.0 → 1.1.0 → 1.1.1 → 1.2.0) and **its step
order is load-bearing**. Getting it wrong produces a tag that does not verify — which is the
one thing the checksum exists to prevent.

**User-invocable only.** It commits, pushes and tags, and `Architecture_Freeze.md` §5 says
*"No autonomous commit or push — ever."*

---

## 0. Decide the version first

`Architecture_Freeze.md` §1:

| | Means |
|---|---|
| **MAJOR** | A superseding ADR changes a decision already in force |
| **MINOR** | A new ADR adds a decision without contradicting an existing one — or a pending one comes into force |
| **PATCH** | An erratum correcting text to state a decision already in force |

If you cannot name which one this is, stop. That question is the change-control review.

## 1. Land everything else first

Every content change goes in **before** the checksum is recorded. `Architecture_Freeze.md` is
**not** in the checksum set, so writing the new value does not move it again — but writing it
early and then editing another ADR means recording a number that was already wrong.

Check what actually moved:

```bash
git status --porcelain
python3 scripts/architecture_checksum.py     # per-group counts + current value
```

A group whose **file count** changed is a change of frozen scope, not a content edit. §4
requires an ADR for that, and `CHECKSUM-003` will say so.

## 2. Audit the hand-written documents

```
Use the doc-claim-auditor agent.
```

Counts live in documents no gate checks: `Architecture_Risk_Register.md`,
`Phase0_Final_Signoff.md`, `Phase1_Entry_Checklist.md`, `CI_Architecture.md` §8, and
`Architecture_Freeze.md` §3 itself. They go stale on exactly this kind of change, and the
bump is the moment they are most visible and least likely to be read.

## 3. Recompute and record — this is where order matters

```bash
python3 scripts/architecture_checksum.py
```

Then in `Architecture_Freeze.md`:

- header: version, tag, and the previous version moved into the "previous versions" row
- **§2**: the new value, the per-group digests, **and the per-group file counts** —
  `gate_checksum` parses those counts for `CHECKSUM-003`
- **§2**: move the old value into the superseded block, so earlier tags stay verifiable
- **§3**: frozen-scope counts — gates, rules, workflow jobs, ADRs
- **§9**: a subsection saying what this version changed **and why**, in prose

`gate_checksum` stays red until §2 is written. That is the gate working; do not work around it.

## 4. Regenerate and verify locally

```bash
python3 scripts/generate_ci_docs.py          # CI_Inventory.md + Policy_Gates.md
bash ci/run_gates.sh                         # expect ALL green, 0 broken
bash ci/self_test.sh                         # expect N/N, checksum unchanged
python3 scripts/architecture_checksum.py --verify
python3 scripts/generate_ci_docs.py --check  # expect "up to date"
```

All four must pass before anything is committed.

## 5. Commit, push, tag — ask first

**Ask the user once, covering the whole chain**, then:

```bash
git add -A && git status --porcelain     # read this list before committing
git commit -m "[LIONEL-CORE] Architecture X.Y.Z: <what changed>"
git push origin main
git tag -a architecture-X.Y.Z -m "<checksum, counts, what changed, how to verify>"
git push origin architecture-X.Y.Z
```

The commit message carries the *reasoning*, not a file list — the diff already has the files.

## 6. Verify the tag from a clean clone

**The only test that speaks for the repository rather than your working tree.** Every
defect found in this project's history was invisible in a working tree and visible in a
clone.

```bash
git clone -q --branch architecture-X.Y.Z <repo-url> /tmp/verify && cd /tmp/verify
pip install pyyaml jsonschema grpcio-tools
bash ci/run_gates.sh && bash ci/self_test.sh
python3 scripts/architecture_checksum.py --verify
```

Then CI:

```bash
gh run watch "$(gh run list --limit 1 --json databaseId -q '.[0].databaseId')" --exit-status
```

All jobs green, including `windows-policy-gates` and `turkish-locale`.

---

## Traps this ritual exists to avoid

- **Recording §2 before the last edit.** The value is wrong and nothing catches it until the
  clean-clone verify — or, historically, not at all.
- **`git add -A` without reading the list.** The 1.0.0 freeze commit deliberately staged
  twelve named paths so the commit matched what the audit had certified.
- **A string replacement that matches nothing.** `Phase1_Entry_Checklist.md` kept saying
  `1.1.0` through the 1.2.0 bump because a `sed` targeted a version string that was never
  there. Re-read what you edited; a silent no-op looks exactly like success.
- **Assuming line endings do not matter.** They are part of the checksum. `.gitattributes`
  must keep `* text=auto eol=lf`.
- **Skipping the clean-clone verify because the gates passed locally.** They did that for
  eight days while a Windows clone computed a different checksum from the same commit.
