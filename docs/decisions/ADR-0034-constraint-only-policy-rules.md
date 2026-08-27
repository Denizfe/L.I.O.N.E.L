# ADR-0034: A policy rule may constrain without deciding

| | |
|---|---|
| Status | **Accepted** — Efe, 2026-08-27. In force. See the Erratum |
| Date | 2026-08-25 |
| Phase | 1 |
| Related | [ADR-0012](ADR-0012-policy-engine.md), [ADR-0008](ADR-0008-coordinator-decomposition.md), [ADR-0029](ADR-0029-adr-errata-provision.md) |

## Context

`contracts/mcp/v1/policy-ruleset.schema.json` describes rule evaluation in one sentence:

> Evaluated top to bottom. **FIRST MATCH WINS.** Falls through to `defaults.decision`.

And `Match`:

> All present conditions must hold (AND). **An absent condition is a wildcard.**

`config/policy/default.toml` ends with a rule that neither statement accounts for:

```toml
[[rule]]
name = "runaway containment"
match.any = true
max_calls_per_turn = 40
on_exceeded = "halt_turn"
```

A `match`, and no `decision`. The schema does not merely permit this — `Rule` requires only
`name`, and `decision` is optional — it carries a dedicated affordance for exactly this
shape. `match.any` is documented as *"Matches everything. Use only for a terminal
containment rule."* So the contract anticipated a terminal catch-all, and still says nothing
about what a terminal catch-all carrying no `decision` **does**. The file validates and every
gate is green.

Read strictly, it does nothing, in both directions at once:

- `match.any = true` matches **everything**. But it is last, and `reads are broadly
  permitted` matches any read first. For every tool the policy actually allows, evaluation
  stops before reaching it.
- If evaluation *did* reach it — a tool matching no earlier rule — it "wins" while carrying
  no `decision`. The contract has no account of that state. Falling through to
  `defaults.decision` is the only sensible reading, and that path discards
  `max_calls_per_turn` too.

So the shipped ruleset contains a containment limit that, under its own contract, bounds
nothing. `max_calls_per_turn`'s description in the schema is *"Runaway containment. A
tool-calling bug can loop; this bounds the blast radius and the bill."* A reviewer reading
the policy file sees a bound. A reviewer reading the contract sees that the bound is
unreachable. Both are reading the frozen architecture.

**The implementation is already ahead of the contract, and that is the second problem.**
`src/lionel/policy/PolicyEngine._decide()` evaluates constraint-only rules — rules with a
limit and no `decision` — in a pass of their own, before first-match-wins runs. That makes
the 40-call bound real, and it is what `tests/unit/test_policy_engine.py` asserts. It is
also behaviour no contract describes. This ADR exists because that gap must be closed by a
decision rather than by the fact that code shipped: the argument *"the code works, the
contract is merely imprecise"* is exactly the argument `Architecture_Freeze.md` §4 exists
to refuse, and it is most persuasive after the work is done.

This is not hypothetical harm deferred to a later phase. ADR-0008 gives `ToolRouter` a
single policy chokepoint so it cannot be bypassed; a limit that silently does not apply is
a bypass that leaves no trace in the diff. At G4, when tools actually dispatch, a loop
bounded on paper and unbounded in fact costs an API bill at best and an unattended
destructive sequence at worst.

## Decision

**A rule may carry constraints without carrying a decision, and constraint rules are
evaluated in a pass of their own, before the deciding pass.**

1. A **constraint rule** is a rule with at least one of `max_calls_per_turn` or
   `rate_limit_per_minute` and no `decision`. A **deciding rule** carries a `decision`.
   A rule carrying both is deciding, and its constraints apply when it decides.
2. Constraint rules are evaluated **first, all of them, regardless of position**. Each
   applies to every call its `match` selects; an absent `match` selects all calls. A rule
   whose limit is exceeded produces the outcome in `on_exceeded` and evaluation stops.
3. Deciding rules are then evaluated top to bottom, first match wins, falling through to
   `defaults.decision`. **This sentence is unchanged**; what changes is that it now
   describes one of two passes rather than the whole of evaluation.
4. A rule with neither a `decision` nor a constraint is a **load error**, not a rule that
   silently does nothing. The schema must reject it.

Constraints bound; they do not authorise. A constraint rule can never turn a denial into an
allowance — the deciding pass runs afterwards and is unaffected by it. That asymmetry is
what makes an out-of-order pass safe: the only thing a constraint rule can do is stop a
call that would otherwise proceed.

`policy-ruleset.schema.json` goes to **1.1.0**, MINOR for consumers and MINOR for producers:
every ruleset valid under 1.0.0 stays valid unless it contains a rule that was already
inert, which is the one case this ADR declares an error.

## Consequences

**What gets better.** The bound in `config/policy/default.toml` becomes the bound the file
appears to describe. A reviewer reading the policy and a reviewer reading the contract reach
the same conclusion, which they currently do not.

**What this costs.**

- Evaluation is no longer one sentence. "First match wins" is the thing everyone remembers
  about this policy, and it is now true of one pass rather than of the whole. The schema
  must say so where the old sentence is, or the old sentence will keep being quoted.
- Two passes is a shape that invites a third. The decision above is deliberately closed:
  constraints, then decisions. Any further pass needs its own ADR.
- A constraint rule with no `match` applies to everything, which reads as harmless and is
  the most powerful rule in the file. `AuditRecord.rule_name` records it by name when it
  fires, so the effect is at least visible after the fact.

**What is deliberately not decided here.** Whether constraint state is per-session or
per-turn beyond `max_calls_per_turn`'s own scope, and where the counter lives when a session
is restarted mid-conversation (ADR-0008's L2 prerequisite). G4 owns that, and deciding it
now would be deciding it without the thing that needs it.

**Rejected without hesitation:** deleting the containment rule so the contract and the
config agree. They would agree, and the loop would still be unbounded. The rule is not the
defect; its inertness is.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| **Leave it. Fix `default.toml` by giving the rule `decision = "allow"` and moving it to the top** | It would then match everything and allow everything, first match wins — the policy becomes allow-by-default with a limit. That is not a smaller change, it is the opposite of ADR-0012 |
| **Move the containment rule to the top of the file with no other change** | Under strict first-match-wins it would match everything and return no decision. Whatever the engine then does is unspecified behaviour, which is what this ADR is about |
| **Say nothing; the implementation already works** | The implementation is not the contract. `policy-ruleset.schema.json` is `stability: stable` and inside the architecture checksum set precisely so that a second implementation — L2's cluster policy service — cannot quietly disagree with the first. An undocumented pass is a disagreement waiting for a second reader |
| **Express containment outside the policy, as a hard-coded limit in `TurnExecutor`** | ADR-0012's premise is that authorization is *"reviewable as a diff and testable without running the agent"*. A limit in code is neither. It is also the one number an operator most plausibly wants to change per deployment |
| **A separate `[[constraint]]` table instead of a rule without a decision** | Cleaner to read, and it was close. Rejected because constraints and decisions share `match` entirely, and two tables would mean two match implementations that must not drift. One shape, two passes, beats two shapes |

## Verification

**Withheld until this ADR is Accepted.** The schema change and the load error in rule 4 are
not made while this is `Proposed` — `Architecture_Freeze.md` §4 requires an ADR *and* Efe's
approval before a contract's stable surface moves, and shipping the change alongside the
proposal would make the approval ceremonial. This is the same withholding ADR-0029, ADR-0032
and ADR-0033 each practised.

The engine's existing two-pass behaviour stays as it is in the meantime. It is the safer of
the two readings — a bound that applies is strictly better than one that does not — and
reverting it to match a contract that may be about to change would be churn in the direction
of the more dangerous state.

On acceptance:

| | |
|---|---|
| `policy-ruleset.schema.json` → 1.1.0 | the `rule` description states both passes; `Rule` gains a constraint-or-decision requirement so rule 4 is a schema error |
| `PolicyEngine._validate()` | rejects a rule with neither a decision nor a constraint, naming the rule |
| `tests/unit/test_policy_engine.py` | a constraint rule below an allowing rule still bounds the loop; a constraint rule cannot turn a denial into an allowance; a rule with neither shape fails to load |
| `tests/contract/test_config_against_contracts.py` | the shipped `default.toml` validates against 1.1.0 |
| `ci/self_test.sh` | a planted rule with neither a decision nor a constraint is rejected |

Gate **G4**, where dispatch makes the bound load-bearing. The failure this prevents has no
symptom before then, and every symptom after.


## Erratum — 2026-08-27: Accepted; the withholding it describes has been discharged

This ADR was written while `Proposed`, and its Verification section describes that pending
state as ongoing. Efe accepted it on 2026-08-27. The decision is unchanged — what follows
corrects text that has stopped being true, per ADR-0029 rule 2.

The Verification section opened:

> **Withheld until this ADR is Accepted.** The schema change and the load error in rule 4 are
> not made while this is `Proposed` — `Architecture_Freeze.md` §4 requires an ADR *and* Efe's
> approval before a contract's stable surface moves, and shipping the change alongside the
> proposal would make the approval ceremonial. This is the same withholding ADR-0029, ADR-0032
> and ADR-0033 each practised.

and continued:

> The engine's existing two-pass behaviour stays as it is in the meantime. It is the safer of
> the two readings — a bound that applies is strictly better than one that does not — and
> reverting it to match a contract that may be about to change would be churn in the direction
> of the more dangerous state.

Both were true and are now discharged. As of architecture 1.10.0:

- `contracts/mcp/v1/policy-ruleset.schema.json` is **1.1.0**. The `rule` description states
  both passes; `compatibility.notes` records that the *deciding* order is unchanged, which is
  why this is MINOR against a schema whose own note calls an evaluation-order change MAJOR.
- `$defs.Rule` carries an `anyOf` requiring `decision`, `max_calls_per_turn` or
  `rate_limit_per_minute`. Rule 4 is now a schema error rather than a review question.
- `PolicyEngine._validate()` refuses such a rule at load, naming it.
- `tests/unit/test_policy_engine.py` holds the three cases this section named, and one more:
  the *shipped* `config/policy/default.toml` is asserted to bound a runaway loop, so the
  bound is proved on the file the runtime actually loads rather than on a fixture.
- `ci/self_test.sh` plants a decisionless, constraintless rule in the schema's own `examples`
  and asserts `JSON-004`.

**One thing this Erratum does not discharge.** The Context above quoted the shipped rule
without its `match.any = true` line and argued from an absent `match`. That was corrected in
place at architecture 1.9.1, while this ADR was still `Proposed` and its body still editable.
`Architecture_Freeze.md` §9.15 records it. The finding was unaffected; the premise was not in
the file.
