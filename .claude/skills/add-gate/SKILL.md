---
name: add-gate
description: Add a CI policy gate end to end — ADR, policy config, gate script, ORDER entry, workflow job, planted violation, regenerated docs. Use when adding a new check to the pipeline, or when a gate needs its self-test coverage.
---

# Add a gate

`CI_Architecture.md` §7 lists seven steps and says of one of them:

> **Step 6 is the one that gets skipped and the one that matters.**

It was right. At the 1.0.0 freeze, 8 of 17 gates had never rejected anything. `gate-coverage`
now fails the build if step 6 is skipped — but failing late is worse than not skipping, and
this skill is the whole ritual in one pass.

---

## Step 1 — the ADR comes first

> A gate with no decision behind it is someone's taste.

**A new rule that changes what is permitted requires an ADR and Efe's approval**
(`Architecture_Freeze.md` §4/§5). Enforcing an *existing* decision more completely does not
— §4 item 3 permits gate work and self-test coverage outright.

If you need an ADR: Status / Context / Decision / Consequences / **Alternatives Rejected** /
**Verification**, and the Verification section names the rule IDs this gate will emit. Status
starts `Proposed`; only Efe moves it to `Accepted`. Implementing a blocking rule for an
unapproved decision is the category error ADR-0030 is about.

Adding an ADR means `adr.expected_count` in policy, an entry in `docs/decisions/README.md`
(`ARCH-016` fails otherwise), and a version bump — see `/bump-architecture`.

## Step 2 — config in `ci/policy/policy.yaml`

Thresholds, allowlists and registries live there, never in gate code:

> a policy you can read as a diff is a policy that gets reviewed.

`ci/policy/policy.yaml` **is in the architecture checksum set.** Touching it moves the
checksum. Every exemption needs an `owner` and a route to removal — and a rule that polices
the registry itself (`LIC-005`, `TODO-002`, `COV-002` are the precedents), or the escape
hatch becomes the loophole.

## Step 3 — `ci/gates/gate_<name>.py`

```python
#!/usr/bin/env python3
"""GATE: <one line>.  ADR-XXXX."""
from _lib import Gate, load_policy, ROOT, rel, read_text

def main():
    p = load_policy(); g = Gate("<name>", "<title>", ["ADR-XXXX"])
    cfg = p["<section>"]

    g.check()                      # count every check, including the ones that pass
    if <violated>:
        g.fail("<RULE-ID>",
            "<what is wrong, in plain language>",
            "<WHY the rule exists — cite the ADR. This is the field that gets skipped "
             "and the one a reader needs at 2am>",
            "<how to fix it>",
            "<path>", <line>)
    else:
        g.note("<something worth surfacing that is not a violation>")

    g.report_and_exit()

if __name__ == "__main__": main()
```

Non-negotiable:

- **Exit codes are a contract.** `0` pass · `1` policy violation · `2` the gate itself is
  broken. `_lib.gate_error()` for the third — a missing dependency is a broken gate, not a
  failing repository, and collapsing them teaches people to ignore red.
- **Every Finding carries four things**: what, where, **why (with the ADR)**, and the fix. A
  gate that prints `FAIL: rule R-014` has moved the work of understanding onto whoever reads
  the log, at the least convenient moment.
- **No cross-gate dependencies.** Every gate is standalone so one failure never hides the
  others.
- **Table-driven rules still count as rules.** If one `g.fail(rid, …)` emits many IDs, keep
  the IDs as literals in the table — `scripts/generate_ci_docs.py` collects string constants,
  and reading call sites is exactly how `l0-conformance`'s 24 rules once vanished from the
  catalogue.

## Step 4 — `ORDER` in `ci/run_gates.sh`

Canonical list; both the generator and `gate-coverage` parse it. Meta-gates go last: a
finding about the pipeline read before the findings about the repository invites fixing the
wrong thing.

## Step 5 — a job in `.github/workflows/ci.yml`

One job per gate, **no `needs:`** between policy gates. A dependency chain means one early
failure marks the rest "skipped" and you learn one thing per push.

Install only what the gate needs (`pyyaml`, plus `jsonschema` / `grpcio-tools` if used).
**Do not export `PYTHONIOENCODING`** — the gates must survive a console that cannot encode
their output, and hiding that is how the cp1252 crash lived.

## Step 6 — the planted violation. Do not skip this.

In `ci/self_test.sh`:

```bash
# N. <what invariant this proves>
printf '<the violation>\n' > config/_selftest.yaml
RESTORE+=("rm -f '$ROOT/config/_selftest.yaml'")
expect_violation <gate> "<RULE-ID>" "<what it plants, in plain words>"
rm -f config/_selftest.yaml
```

**If the plant touches the architecture checksum set** — `docs/decisions/ADR-*.md`,
`contracts/**`, `config/**/*.toml`, `config/*.json`, `ci/policy/policy.yaml`,
`artifacts.lock.yaml`, `MASTER_PLAN_v2.md` — use the byte-exact backup helper:

```bash
BAK="$(plant_in <path>)"
<mutate the file>
expect_violation <gate> "<RULE-ID>" "<description>"
unplant <path> "$BAK"
```

A plant left behind there does not merely litter: it moves the architecture checksum, and the
next reader sees an unexplained architecture change. The suite asserts checksum invariance at
the end for exactly this reason.

Add any new planted **file** to the litter check near the bottom.

If the assertion cannot go through `expect_violation` — because the gate needs `--root`,
`--suite` or similar — add `# selftest-covers: <gate> — reason`. `gate-coverage` reads that
pragma. It is explicit on purpose: inferring coverage from "the script mentions this gate"
would let a comment count as a test.

## Step 7 — regenerate

```bash
python3 scripts/generate_ci_docs.py
```

## Verify

```bash
bash ci/run_gates.sh <name>      # passes on a clean repo
bash ci/self_test.sh             # your gate appears, N+1/N+1
bash ci/run_gates.sh             # everything still green, 0 broken
python3 ci/gates/gate_gate_coverage.py   # coverage went up; exemptions still empty
python3 scripts/generate_ci_docs.py --check
```

Then **prove it bites**: break the thing it guards by hand and confirm it goes red with the
rule ID you expect. A gate that has only ever passed is unproven, however carefully written —
two gates in this repository had real bugs that only the self-test surfaced.

If policy or an ADR changed, `gate_checksum` is now red. That is `/bump-architecture`.
