# Contributing

New exercises are welcome. The bar is that an exercise must teach a
**distinction**, not a command.

## Scaffold

```bash
tse new docker/04-published-port-mismatch
```

That creates the standard layout. Fill it in, then verify:

```bash
tse verify docker/04-published-port-mismatch
```

CI runs the same command. An exercise is only correct if `check.sh` **fails**
against `setup/` and **passes** against `solution/`. An exercise that passes in
its broken state is not broken, and one that fails in its fixed state is not
solvable.

## Rules that are not negotiable

**The ticket never names the technology.** Write what the customer would
actually say. "Orders stopped appearing after lunch" is a ticket. "The
deployment has a bad label selector" is a spoiler. If a learner can tell which
track an exercise belongs to from the ticket alone, rewrite it.

**Check the customer's workflow, not your sabotage.** Assert that the thing the
customer asked for works again. Do not assert that a specific environment
variable holds a specific value, or you have written a puzzle with one accepted
answer instead of an incident with a real resolution.

**Assertions must be honest under timing.** State that is briefly true during
startup ("the container is running") will pass at the wrong moment. Prefer
state that is computed over time, such as a healthcheck result.

**Hints escalate, they do not dump.** Hint 1 reframes the symptom into a
provable question and names no command. Hint 2 points at the layer and the kind
of evidence. Hint 3 gives the commands. `solution.md` gives the reasoning.

**Every solution ends in words.** Root cause, scoped fix, customer update,
escalation note, and a 90-second spoken answer. The writing is graded work, not
decoration.

## Style

US English. No em dashes. Plain language over jargon, and when jargon is
required, define it the first time on the page.
