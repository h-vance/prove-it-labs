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

Then run the rest of the suite, which is fast:

```bash
python3 tools/tests/test_content.py   # structure and the editorial rules below
python3 tools/tests/test_meta.py      # the meta.yaml subset parser
tools/tests/smoke.sh --fast           # the CLI surface
```

One test in `test_meta.py` compares the subset parser against real PyYAML, and
it **skips silently** when PyYAML is not installed. Since the CLI deliberately
has no dependencies, that is the normal state on a fresh machine, and it once
hid a real divergence until CI caught it. To run it locally:

```bash
python3 -m venv /tmp/yamlvenv && /tmp/yamlvenv/bin/pip install -q pyyaml
/tmp/yamlvenv/bin/python tools/tests/test_meta.py
```

18 tests and no skips means the parity check actually ran.

`test_content.py` enforces most of the rules on this page, so a violation is a
failing build rather than a review comment.

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

**Every solution ends in words.** Root cause, scoped fix, customer update, and
an escalation note. The writing is graded work, not decoration.

**Every exercise ends in questions.** Three of them, in `questions.json`, with
four options each and exactly one correct. Every option carries its own
explanation, the right one included, because "correct" on its own teaches
nothing. `test_content.py` enforces the shape, rejects "of the above" options,
requires question text to be unique across the whole course, and fails the
build if the answer drifts toward one position. Write them from the
distinctions the exercise actually made rather than from the topic in general.

## Style

US English. No em dashes. Plain language over jargon, and when jargon is
required, define it the first time on the page.
