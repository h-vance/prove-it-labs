# Prove It

[![verify](https://github.com/h-vance/technical-support-engineering/actions/workflows/verify.yml/badge.svg)](https://github.com/h-vance/technical-support-engineering/actions/workflows/verify.yml)

A hands-on Technical Support Engineering course. You get a customer ticket, a
genuinely broken system, and no hint about which layer failed. You investigate.

Most infrastructure courses tell you the topic before the exercise, which is the
one thing a real ticket never does. Every ticket here is a symptom in the
customer's own words. Working out what to look at first is the skill.

## Start

Open the repository in a Codespace, wait for the container to build, then:

```bash
tse start docker/01
```

That provisions a broken system and prints the ticket. Investigate it with
ordinary tools. When you think you have fixed it:

```bash
tse check
```

The grader never just says pass or fail. It shows the assertion, the command it
ran, and the raw output it evaluated:

```
FAIL  Customer workflow returns their data
      $ curl -s --max-time 3 http://127.0.0.1:8100/customers
      (no output)
      Expected: {"status": "ok", "customer_count": 10} from /customers
```

Running locally instead of in a Codespace needs Docker and Python 3.11 or
newer. There is nothing to install: `tse doctor` will tell you what is missing.

## The commands

| Command | What it does |
|---|---|
| `tse list` | Every exercise, with time estimates and your progress |
| `tse start <id>` | Provision an exercise and print its ticket |
| `tse check` | Grade the active exercise, showing the evidence used |
| `tse hint` | Reveal the next hint. They escalate rather than dump |
| `tse answer` | Root cause, customer update, and escalation wording |
| `tse apply` | Recreate the services after you edit the configuration |
| `tse reset` | Return to the state described in the ticket |
| `tse progress` | See or export your progress |
| `tse doctor` | Check this machine can run the labs |
| `tse new` | Scaffold a new exercise |

## How the exercises work

Everything is built around one question, borrowed from how infrastructure
support actually happens:

> What can I prove for the customer right now?

Not "what technology am I studying today." Each exercise proves exactly one
operational fact, and the technology sits underneath it. You are not asked to
memorize commands. You are asked to say what a command proved, and just as
importantly, what it did not.

Every exercise has the same shape, so there is never a surprise about where to
look:

```
ticket.md     the customer symptom, and nothing else
setup/        the broken state
check.sh      the assertions, and the evidence behind them
hints/        three escalating nudges
solution.md   root cause, the fix, and the words you would send
```

## Design notes

This course was built for people who bounce off setup friction and walls of
prose, which includes a lot of very good engineers.

- **Uniform structure.** Every exercise is laid out identically, so orienting
  yourself costs nothing.
- **Stated cost.** Every exercise declares how long it takes before you start.
- **Core and stretch are separated,** and stretch material can be hidden rather
  than skimmed past.
- **A minimum viable day exists.** One ticket, one command, one proof sentence,
  one spoken answer. That counts as a day of progress.
- **The writing is graded.** Support is half communication, so customer updates
  and escalation notes are assessed work, not an afterthought.

## Status

Under construction. The Docker track is being built first, followed by
Kubernetes, APIs, and SQL, then Linux foundations, networking, observability,
and communication.

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Code is MIT. Course content, meaning lessons, tickets, solutions, and
reference material, is CC BY 4.0. See [LICENSES/](LICENSES/).
