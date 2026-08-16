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

## Before you open a pull request

Run this. It is the gate that matters:

```bash
tools/tests/preflight.sh
```

Every test suite, the leak scan, the link check, shellcheck, the site build with
its type, page, terminal, accessibility and Content-Security-Policy checks, and
then `tse verify` and `tse record --check` for every exercise your branch can
reach. It picks those with the same rule the workflow uses, so it cannot check
less than CI would. `--all` does all 25 rather than the ones you touched, and
`--fast` skips Docker entirely and takes about twenty seconds.

One section is worth knowing about because it will fail for reasons the others
cannot. **A machine that is not this one** re-runs the CLI under `env -i` with a
stripped PATH and `LANG=C`, so nothing you have exported can make it pass. That
is where a locale-dependent decode shows up, and it is also what keeps the
Python floor honest: the stripped PATH finds the system interpreter rather than
whichever one you installed.

Run this before opening a pull request. CI runs the same exercise verification
now that standard runners are free on a public repository, so this is no longer
the only place the expensive half happens. It is still the faster place: your
machine has the images cached and does not spend a minute booting a runner.

It is also how this course gets tested on macOS, and that is not something CI
can take over. There is a `macOS` job in `verify.yml`, and it runs the CLI, the
four test suites, the leak scan and the fast smoke test. It does not run a
single exercise, because hosted macOS runners have no Docker daemon. The job
prints what the runner actually has as its first step, so that stays a measured
claim rather than a remembered one.

That split is worth being plain about: CI covers the CLI on macOS, and running
`preflight.sh` on the machine you work on is the only thing that covers the
course on macOS.

The individual pieces, if you want to run one on its own:

```bash
python3 tools/tests/test_content.py   # structure and the editorial rules below
python3 tools/tests/test_meta.py      # the meta.yaml subset parser
python3 tools/tests/test_scrub.py     # the output scrubber and commands.txt
python3 tools/tests/test_rubric.py    # the communication track's grading
tools/tests/smoke.sh --fast           # the CLI surface
tools/tse leaks                       # nothing from a real machine is committed
tools/tse links                       # every link resolves
```

CI also lints every shell script in the repository, which is the one check with
a tool you have to install. `tse doctor` reports whether you have it.

```bash
shellcheck --severity=info -e SC1091 \
    tools/lib/assert.sh tools/tests/smoke.sh .devcontainer/post-create.sh \
    labs/*/*/check.sh labs/*/*/setup/*.sh labs/*/*/solution/*.sh \
    labs/*/_stack/*.sh
```

Without it locally, run the same thing through Docker and install nothing:

```bash
docker run --rm -v "$PWD:/mnt" -w /mnt koalaman/shellcheck-alpine:stable \
    shellcheck --severity=info -e SC1091 labs/*/*/check.sh
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

## Adding a track

Most exercises belong to a track that already exists. If yours needs a new one,
there are three worked examples to copy from: `mixed` borrows another track's
stack, `communication` has no system at all, and `networking` brought up a new
one. In order:

1. **Add the track to `TRACK_ORDER` in `tools/tse`** and to `TRACK_LABELS` in
   `site/src/lib/labs.ts`. Nothing else on the site needs touching. Pages are
   generated from `labs/`, so the track appears once an exercise exists in it.
2. **Decide whether it needs a stack at all.** `stack: none` is a real option
   and the communication track uses it. If your exercises fit an existing
   stack, set `stack_source` and write no new one, as `mixed` does.
3. **If it does need one**, create `labs/<track>/_stack/` with a `compose.yaml`.
   Copy the resource limits and hardening from an existing stack rather than
   writing them fresh: `read_only`, `cap_drop`, `no-new-privileges`, and the
   memory, CPU and pid caps are there so a lab cannot run away with a laptop.
4. **Publish a port only if the learner should reach it from the host.** Two
   tracks deliberately publish nothing. If the interesting client behavior is
   version dependent, as it is for anything doing TLS, run the client inside a
   container so every machine sees the same output. A host `curl` printed two
   different exit codes for one fault and cost a scrub rule to fix.
5. **Every filename an exercise writes into a shared `_stack` must be in
   `.gitignore`.** `test_content.py` fails the build if one is missing, because
   committing it would freeze one exercise's broken state into the repository.
6. **Add the track to the table in `README.md`,** and say honestly what it does
   and does not yet cover.

Then record as you go rather than in a pass at the end, and expect the first CI
run to find a difference between your machine and the runner. Every track so far
has produced at least one.

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

**If your exercise measures anything, run it several times before you believe
it.** Every service here is capped at half a core, so work that overlaps
contends, and an assertion tuned on a quiet laptop fails on a loaded runner
roughly one push in five. That is worse than a broken exercise, because it
teaches people to rerun CI instead of reading it.

The observability stack sends its sample workload one request at a time for
exactly this reason. Running eight at once produced zero, one, two and four
requests over a one second objective across four runs of the *fixed* state,
from lookups that normally take five milliseconds. Loosening the objective
would have buried that. Removing the contention fixed it, and a hundred serial
requests turned out to prove everything four hundred concurrent ones did.

Prefer numbers that are integers by construction, such as a count out of a
fixed workload, over numbers that are measured, such as an average. When you
do need a measured one, make the gap between pass and fail an order of
magnitude rather than a margin.

**Hints escalate, they do not dump.** What escalates is how much of the work is
done for the reader, not how many commands appear.

| | What it does | What it must not do |
|---|---|---|
| Hint 1 | Reframes the symptom into a provable question | Name a command |
| Hint 2 | Names the layer and shows how to gather the evidence | Interpret it, or give the fix |
| Hint 3 | Shows what the evidence says and what to change | |

Hint 2 may carry commands, and in the harder exercises it should: knowing which
question to ask a system is most of the skill, and withholding `df -i` teaches
nothing that withholding it does not also hide. What hint 2 must never contain
is the change to make. `test_content.py` checks that, and it holds across all
twenty-five exercises with no exceptions.

`solution.md` gives the reasoning.

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
