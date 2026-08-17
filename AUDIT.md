# Audit

An end-to-end review of this repository against current practice, covering
correctness, security, accessibility, portability, content, operability and
cost. Twenty-nine commits over two days, finishing 16 August 2026.

Everything below is either fixed and gated, accepted with a reason and a
number, or listed as not covered. There is no fourth category.

This is a record of one review, not a living document. The counts in it were
true when it was written and the next exercise added will move some of them. The
gates it describes are the part that stays current, and they are in
`tools/tests/` and `site/scripts/` rather than here. The one thing checked
mechanically is that every cross-reference below still resolves, because a
document nobody can navigate is not a deliverable.

## Method

**A gate that has never been seen to fail is not a gate.**

That is the whole method, and it is the reason this document is long. Every
check here was made to fail on purpose before it was believed: the defect it
claims to catch was written into a real file, the check was run, its message
was recorded, and the defect was reverted. Where a check did not fail, that is
recorded too, because those were the most useful findings in the audit.

The rule was applied to the auditor as well. Four times a fix was reported as
working and was then shown wrong by its own test. Those are written up in full
rather than quietly corrected, because a review that only records the things it
got right is not evidence of anything.

**Who the auditor was.** This review was carried out by Harrison Vance working
with Claude (Anthropic). That is worth stating because this document refers to
"the auditor" throughout and because the same standard applies either way: none
of the findings below rest on anybody's judgment. Each one names the defect that
was planted, the check that caught it, and the message it printed. Where the
review reached a wrong conclusion, the test is what corrected it, which is the
argument for building the gates in the first place.

## Contents

- [Blockers](#blockers), two, both closed
- [Checks that could not fail](#checks-that-could-not-fail), nine of them
- [Correctness](#correctness)
- [Security](#security)
- [Accessibility](#accessibility)
- [Portability](#portability)
- [Content and documentation](#content-and-documentation)
- [Cost](#cost)
- [Where the auditor was wrong](#where-the-auditor-was-wrong)
- [Accepted](#accepted)
- [What the flip bought](#what-the-flip-bought)
- [Not covered](#not-covered)
- [The gates as they stand](#the-gates-as-they-stand)

---

## Blockers

Two findings would have been live problems the moment this repository went
public. Both are closed.

### B1. A contributed exercise file could undo the stack's hardening

**What was wrong.** Exercises materialize files into a shared `_stack`
directory: `compose.override.yaml`, a query, a request script. The override is
merged into the stack's compose file, and nothing limited what it could set. An
exercise could give itself `privileged: true`, mount the host filesystem, or
join the host network, and the stacks' `read_only`, `cap_drop` and
`no-new-privileges` settings would be silently overridden by the merge.

**How it was proven.** Written as a hostile override and applied. It worked.

**The gate.** `check_compose_override` in `tools/tse` refuses anything outside
four keys, counted across all twenty overrides in the repository:
`environment`, `user`, `group_add`, `ports`. It is a deliberately strict scan
rather than a YAML parse, and it refuses what it cannot read confidently: tabs,
odd indentation, flow style, unknown tags. The equivalent exists for Kubernetes
manifests, refusing any kind outside the three the labs create and any field
that reaches the node.

**Planted.** Every hostile override in `test_content.py` is a planted defect
kept as a test. One of them found a real hole during development: `services:
{app: {privileged: true}}` on a single line, whose first word is the expected
key, was waved through by an earlier version that only looked at line starts.

**Proven again after the flip, this time where it actually runs.** Everything
above was established on one machine, by one person, on a repository nobody
else could open a pull request against. That is a weaker claim than it sounds:
the thing this guard defends against is a stranger's file being executed by CI
before a human reads it, and that path did not exist yet.

It exists now, and removing the `workflow_dispatch` gate is what switched it on.
So the guard was tested as a real pull request, [#1](https://github.com/h-vance/prove-it-labs/pull/1),
carrying an override asking for `privileged`, `SYS_ADMIN`, an unconfined seccomp
profile, the host PID namespace, and a read-write bind mount of `/` into the
container. CI refused it in thirteen seconds:

```
tse: labs/docker/01-service-unavailable-after-deploy/setup/compose.override.yaml:5:
     an override may not set 'privileged'.
     Allowed: environment, group_add, ports, user.
     The stack declares how its containers are confined and an
     exercise does not get to change that.
```

**The ordering held too, which is the part that was only ever a claim.** The
matrix job declares `needs: [discover, tests]` specifically so the cheap scan
refuses a bad file before anything is provisioned. With `tests` red, the nine
stack jobs and the learner loop skipped rather than ran. A hostile pull request
costs one job and thirteen seconds, not a full matrix, and no container is ever
started from the contributed file.

The pull request was closed and its branch deleted. It is left open to reading
rather than squashed out of the history, because a guard nobody has watched fail
is the thing this document exists to distrust.

### B2. The leak gate missed 12 of 17 credential formats

**What was wrong.** The scan that exists to stop a real credential reaching a
public repository was matching five of the seventeen formats it was written
for.

**How it was proven.** A sample of each format was planted and the scan was run.

**The gate.** Twenty-four patterns everywhere and twenty-six more inside
recordings, over 394 tracked files, with three named exemptions. Four tests
hold it honest: every planted sample must be caught, every rule must have a
planted sample, no rule may fire on what it must tolerate, and every exemption
must still exist.

**A second hole in the same gate, found later.** See [S1](#s1-a-credential-in-a-wide-encoding-read-as-clean).

---

## Checks that could not fail

The largest single category. Eight checks were passing without checking
anything, and a ninth was caught before it ever ran here.

### F1. `--not-contains` passed when the command errored

**What was wrong.** The assertion library's negative matcher asked whether a
string was absent from a command's output. If the command failed, its output
was an error message, the expected string was not in it, and the assertion
passed.

**How it was proven.** Live, on `sql/03`. The postgres service was stopped. The
command returned `service "postgres" is not running`. There is no `Seq Scan` in
that, so the grader printed **"1 of 1 checks passed"** against a completely
broken system.

**The gate.** `--not-contains` now requires exit 0. A grader that genuinely
expects a failing command opts in with `--even-if-it-fails`. The failure message
says so explicitly: *"The command itself failed, exit N. What it did not print
proves nothing."*

**Planted.** Two smoke assertions, both of which fail against the old library.

### F2. Two graders passed on evidence they never saw

Same shape, different mechanism. Both fixed in `e122da0`.

### F3. The accessibility gate had never opened the content

**What was wrong.** Hints and the solution were Preact islands that rendered
nothing until clicked. The gate scanned the page as served, so the richest
markup on it, tables and blockquotes and fenced code, went unscanned on every
exercise in both themes for as long as the gate had existed.

**How it was proven.** The gate was made to open them. The heading outline was
broken on all twenty-five exercise pages and had been the whole time.

**The gate.** The a11y run opens every hint in order and the solution, then
scans again. Checks went from 210 to 324.

**A correction worth recording.** A reviewer proposed adding axe's
`heading-order` rule to catch the heading bug. That was tested and is wrong:
axe only flags a level *increasing* by more than one, and this bug was an
injected `h1` landing under an `h2`, which is a decrease. Planting the exact
defect against the extended axe run produced no violation at all. The outline
check is written out longhand for that reason.

### F4. `finish()` reported success when nothing had run

A grader whose checks all failed to execute reported a pass. It now exits 1 on
zero checks.

### F5. The 404 page had never been checked by anything

**What was wrong.** `findPages` in the a11y harness matched directories
containing an `index.html`. Astro emits the not-found page as a bare
`404.html`, which matched neither branch, so thirty of the thirty-one built
pages were checked and nobody had ever looked at the thirty-first.

**How it was found.** By accident, and only because of the method. A planted
defect was put into the 404 page to prove the CSP check fired, and it did not
fire. The plant was correct; the page was invisible.

**The gate.** `findPages` returns every `.html`. 31 pages, 324 checks.

### F6. `tse doctor` failing did not stop the Codespace saying it was ready

`.devcontainer/post-create.sh` ran `tools/tse doctor || true`. A container that
came up unable to run a single exercise still printed "Prove It is ready." The
banner is now conditional and a failure is reported loudly. The build still does
not abort, which was the actual intent of `|| true`.

### F7. The style rules read a fraction of what gets published

See [C1](#c1-the-style-rules-covered-labs-and-two-files-at-the-root).

### F8. A new file is exempt from the editorial rules until it is committed

`style_sources()` builds its list from `tse.tracked_files()`, on the stated
grounds that tracked files are exactly what gets published. That is the right
scope and it has a timing hole nobody had noticed.

A file that has just been written is not tracked yet, so every editorial rule
skips it. The tests pass. The author, reasonably, reads that as permission to
commit. Committing is what puts the file in scope, and the rules that would
have caught it do not run again until somebody thinks to re-run them.

Found by walking into it. `site/scripts/demo-svg.mjs` was written, checked
green at 145 tests, and committed. The next run failed `test_us_spelling` on
that file, naming a line and a British spelling in a comment that had been
sitting there the whole time.

The message is described rather than quoted, and for the third time today that
is not squeamishness. Pasting it in put the misspelled word into this document,
and `AUDIT.md` is held to the spelling rule like everything else, so the finding
about a gate failed on the gate it was about. The same collision produced the
same answer in [C10](#c10-nothing-checks-that-this-document-is-still-true) and
[C11](#c11-a-setting-a-reader-could-change-that-could-change-nothing). A
document cannot both forbid a string and contain it, and the right response is
usually to stop quoting rather than to stop checking.

**Not changed, deliberately.** Widening the scan to untracked files would put
scratch files, editor leftovers and anything a contributor happens to have in
their working directory under the editorial rules, which is a fast way to make
the gate something people learn to ignore.

The real mitigation is the one that already worked: `preflight.sh` is the thing
you run before pushing, it runs after you have committed, and it caught this
before anything left the machine. What is worth knowing is that a green test
run on a file you have not committed yet is not evidence about that file, and
this document is the place to write that down.

### F9. A grader assertion that could not fail, caught before it shipped

The only entry in this section that never ran in this repository, kept because
the rule that found it is the one this section exists to state.

`networking/03` was written with three assertions. The third read back what the
customer's address resolves to and required the gateway's own value, meaning to
catch two wrong fixes: pointing the record at something that merely answers,
and deleting the record so the name stops resolving at all.

It looked like a real check. Applying this document's own standard to it, that
a gate never seen to fail is not a gate, meant constructing a state it would
reject and the first two did not. There is none. Both wrong fixes stop the
upload working, so the first assertion already refuses them, and across every
state reachable through the four keys an exercise may set the third never once
failed alone.

Worse, the fix it was written to catch is the one it lets through. A record
holding the gateway's literal address rather than its name passes all three,
because today it resolves to exactly the same place. It goes wrong on the next
rebuild, which is not a thing any check running now can observe.

So the assertion was removed rather than shipped, the reasoning is written into
`check.sh` where the next person to have the idea will find it, and the literal
address trap is taught in the solution and deliberately left ungraded. Two
assertions that can both fail are worth more than three where one is decoration.

---

## Correctness

### A1. The networking stack could mint two different lab CAs

**What was wrong.** A `certs` build stage generates fresh RSA keys every time it
runs, and `gateway` and `client` were parallel branches off it. One cold build
shares the stage. A build where one branch is cached and the other is not runs
`certs` again and mints a second CA, so the client ends up trusting an authority
that never signed the gateway's certificates. Every exercise in the track then
fails on an unknown issuer, which is not what the track teaches, and
`issue-certificates.sh` deletes `ca.key` at the end so nothing can re-sign.

**The fix.** The graph is a line: `certs` → `gateway` → `client`. The gateway
keeps `ca.pem`, a public certificate with no key, and the client copies it from
there. Docker's cache follows edges, so the two cannot disagree in any cache
state. No private key moves and the teaching property is untouched.

**The first fix was not enough, and the test said so.** Chaining alone does not
fix independently built compose service images. Two single-service builds with a
cache prune between them still split. This was reported as working before that
case was tested. What actually holds is that `tse` uses `up -d --build`, one
build graph, verified twice including after a full cache wipe, plus a backstop:

**The gate.** A stack may ship `_stack/self-check.sh`, run after its services
come up. The networking one extracts `ca.pem` from the client image and `v3.pem`
from the gateway image and runs `openssl verify`, using only public
certificates. It fails with both subjects, both fingerprints and the rebuild
command. This runs on every learner's machine at every start, which is wider
coverage than the contributor-only gate originally planned.

### A2. A regression the auditor introduced, and the test caught

**What happened.** Bounding assertion commands with `timeout ... bash -c` moved
them into a fresh shell. `bash -c` inherits only exported variables, not plain
shell variables and not functions.

`sql/03` builds its query in a plain variable. It became empty, the SQL was a
syntax error, the command failed, and `--not-contains` passed: **the exact
fail-open that same change had been written to prevent**. `observability/02`
calls a shell function, which no longer existed. Its `check.sh` documents the
contract in a comment: *"`assert` evaluates its command in this shell, so a
function is callable."*

**The fix.** `_tse_run_bounded` runs the command in a subshell with a watchdog,
which preserves `eval` semantics. The watchdog's output is redirected away from
the function's own stdout, because a background job holding that pipe open makes
every assertion wait out the full timeout.

**Planted.** Two smoke assertions that fail against the broken version: a plain
variable reaching the command, and a function being callable. Plus a pipefail
test and a real timeout test.

### A3. Three recordings captured a state that was still moving

`docker/02`, `docker/03` and `kubernetes/03` recorded container state during
startup rather than after it settled. Fixed with `# until:` markers.

**The fix exposed a second bug.** Waiting for the settled state slid a
`--tail 15` log window past the line the exercise is about. Anchoring at the
head instead was proven byte-identical across six samples over twenty seconds.

---

## Security

### S1. A credential in a wide encoding read as clean

**What was wrong, in three layers, each found after fixing the one above it.**

1. A file with a UTF-16 byte order mark raised on decode and was skipped
   silently. The scanned-file count did not move, so nothing said so.
2. Unmarked UTF-16 is *valid UTF-8*. `ghp_` becomes `g\x00h\x00p\x00_\x00`,
   which decodes without raising and matches no pattern.
3. Unmarked UTF-32 scored 1.0 as UTF-16, because the interleaved NUL bytes were
   being counted as ASCII characters.

**The gate.** `decode_for_scanning` reads byte order marks, then scores the wide
encodings with NUL penalized, then falls back to UTF-8. A file it cannot read at
all is a **failure**, named, rather than a skip. Eight encodings are tested.

### S2. The only image holding data was the only one not confined

**What was wrong.** `CONTRIBUTING.md` tells a contributor to copy `read_only`,
`cap_drop`, `no-new-privileges` and the resource caps from an existing stack.
Nothing checked that they had. Postgres had none of the three, in both stacks
that use it, while every Python service beside it was sealed.

**Why it had been left, and why that reason was wrong.** The official postgres
entrypoint starts as root and drops to postgres with `gosu`, which needs SETUID
and SETGID and is blocked outright by `no-new-privileges`. Starting *as* the
postgres user skips that branch entirely, so there is nothing to drop and all
three settings hold.

**Proven from outside the container rather than assumed.** `docker inspect`
reports `CapDrop=[ALL]`, `ReadonlyRootfs=true`,
`SecurityOpt=[no-new-privileges:true]`, `User=postgres`. The seed runs, queries
work, and `sql/03`'s `CREATE INDEX` still succeeds. All six exercises on the two
stacks verify, including the two running against a volume that predates the
change.

`sql/` keeps its promise that a rebuild reseeds, now on a tmpfs rather than the
container's writable layer, which makes the guarantee stronger because the data
never reaches a disk. Measured rather than assumed: the full 300,000-row seed is
122M of the 512M cap, and the container sits at 166M in total.

**The gate.** `service_containment` reads what each service ends up with,
resolving merge keys so the observability stack's shared anchor counts for all
three of its services. A service that genuinely cannot take a setting declares
`x-containment` with the reason. None needed it.

**Planted twice, and the second one is the point.** Removing `cap_drop` failed.
Changing it to `NET_RAW`, which a key-presence check would wave through, also
failed.

### S3. No Content-Security-Policy

**What was wrong.** Nothing constrained what a page could load or run.

**The fix.** `default-src 'none'` and then only what the site uses, written into
every page as a meta tag by `site/scripts/csp.mjs`. GitHub Pages serves no
custom headers, which costs three directives browsers ignore in meta form:
`frame-ancestors`, `report-uri` and `sandbox`. They are left out rather than
written and quietly dropped, because a policy that looks stricter than it is, is
worse than an honest one.

Script and style hashes are computed from what was built rather than written
down, per page rather than pooled, so a Starlight upgrade cannot start failing
on a stale hash and one page cannot vouch for another's script. The one
concession is style attributes: the syntax highlighter writes 2,357 of them and
an attribute cannot be hashed. Unlike a script, it also cannot call anything.

**What this buys, precisely.** The pages are static and already checked, so this
is not what stops bad content entering the build. That is [S4](#s4-markdown-was-rendered-to-html-with-no-sanitizer).
This is what protects a reader when something reaches the page *after* the
build: a compromised host, a tampering proxy, an extension.

**The gate.** Checked inside `a11y.mjs`, which already opens every hint, the
solution, the quiz and the terminal on all thirty-one pages in both themes.
Search and the quiz are exactly where a policy usually breaks. A policy read out
of the HTML is not proved; one a browser enforced with nothing to say about it
is.

**Planted three times.** A corrupted hash was refused. An injected
`<script>window.__pwned=1</script>`, added to a built page after the build,
which is the thing this exists to stop, was refused. A stripped meta tag was
reported as the page carrying zero policies. The third plant is what found
[F5](#f5-the-404-page-had-never-been-checked-by-anything).

### S4. Markdown was rendered to HTML with no sanitizer

**What was wrong.** `md()` in `site/src/lib/labs.ts` renders with `marked` and
no sanitizer, and the page inserts the result with `set:html`. Every ticket,
hint, solution and reference document goes through that path, so a tag written
into one of them is a tag on the published site. 134 files were clean by habit
rather than by rule.

**Why not a sanitizer.** It would mean adding a dependency to a project whose
lack of them is a stated design property, and it would strip markup silently
rather than telling the author. Refusing raw HTML at the source closes the same
hole a step earlier and gives a contributor an error they can act on.

**The gate.** No raw HTML in anything rendered this way. Deliberately broad
enough to catch `<placeholder>` written in prose, because markdown treats that
as an unknown tag and renders nothing where the word should be. Code is exempt,
which is the part worth testing, and both directions are asserted.

**Planted.** `<script>alert(1)</script>` in a ticket, named with both tags.

### S5. Identities appeared in history but not in the diff scan

Fixed in `d8ef50e`: the leak scan reads the history, not only the working tree.

### S6. The one binary this repository installs was never checked

Found in the pre-flip pass. Two places fetched the `kind` binary over the
network and handed it straight to `sudo install`:
`.devcontainer/post-create.sh` and the Kubernetes job in
`.github/workflows/verify.yml`. Whatever that URL served on the day ran as root,
on CI runners and in every learner's Codespace.

The inconsistency is as much the finding as the risk. Every GitHub action in
both workflows is pinned to a commit SHA, with the version in a trailing
comment, precisely so that a tag moving underneath cannot change what runs. The
one thing being downloaded as an executable had no such pin.

**The fix.** The published sha256 for each architecture, committed to git and
verified before the install. Pinned rather than fetched on the grounds that a
checksum downloaded next to the thing it checks only proves the two arrived
together. Living in git is what makes it a control: changing the binary this
installs now takes a commit. Both digests were confirmed against the binaries
that URL actually serves, not merely confirmed to be well formed.

**The gate.** In every tracked shell script and workflow, a download that names
a target file must be verified before any line installs or marks that file
executable. A download nothing ever runs is left alone, because several
exercises curl into `/dev/null` on purpose and the rule is about what gets
executed, not about what gets fetched. A second check refuses a truncated
digest, which still reads as a pin and checks almost nothing.

**Planted, three times.**

```
.github/workflows/verify.yml:243 installs /tmp/kind, downloaded at line 242,
with nothing having verified it. Pin the published sha256 and check it first.

.devcontainer/post-create.sh:25 installs /tmp/kind, downloaded at line 23,
with nothing having verified it. Pin the published sha256 and check it first.

.devcontainer/post-create.sh:17 pins a 33 character digest, and a sha256 is 64
```

The first version of this gate was wrong in the other direction: it required a
checksum for every download anywhere, and failed twelve times on exercises that
curl to `/dev/null` to demonstrate a connection failure. A gate that fires on
correct code gets switched off, so the rule was narrowed to what it actually
means.

### S7. The link checker's own exemption could not expire

`tools/tse links` skips links that point at this repository, because a private
repository answers 404 to everybody and reporting all of them as broken would
be wrong. The exemption was correct. Its expiry was a comment:

> THE DAY THIS REPOSITORY GOES PUBLIC: these stop returning 404 and this
> function stops being needed. Deleting it then is the check getting stronger.

That is a gate that depends on somebody remembering, which is the same class of
problem as the rest of this document. Six links were exempt, and one of them
matters more than the others: `SECURITY.md` sends people reporting a
vulnerability to the advisory form, and that form only exists once private
vulnerability reporting is switched on. So "the security policy does not send
reporters to a 404" was a claim nothing could check, and would have stayed
unchecked until somebody read a comment.

**The fix.** The exemption expires on its own. `own_urls()` asks whether the
repository answers a stranger, and returns nothing as soon as it does, at which
point every self-link is checked like any other. A probe that cannot reach
GitHub keeps the exemption, matching how this command already treats an
unreachable host: a bad minute on the network is a warning, never a failure.
Offline runs never request an external address at all, so they skip the
question entirely.

**Proven in both directions**, since the branch that matters only ever runs
after the flip. Probed live: this repository answers 404 and the exemption is
kept, a public repository answers 200. With the probe forced to 200, `own_urls`
returns `()`, and the advisory link's classification moves from `self`, which is
skipped, to `external`, which is requested and fails the build on a 404.

---

## Accessibility

WCAG 2.2 AA, both themes, every page.

### X1. No page had ever been viewed narrow

**What was wrong.** Nothing had looked at this site at 320 CSS pixels, which is
1.4.10 Reflow. The site carries a monospace terminal and wide preformatted SQL
tables, so it was a real risk rather than a formality.

**The result.** All 31 pages pass with **zero CSS changes**. A wide block
scrolls inside its own container, which `md()` already supported by putting
`tabindex="0"` on `<pre>`.

**The gate.** A pass at 320×720 asserting the document does not scroll
sideways, naming the widest offending element when it does, then a full axe scan
at that width.

**Planted.** A `min-width` wider than 320 on the terminal failed the assertion
and named the element.

### X2. Without JavaScript the page lost the hints and the solution entirely

**What was wrong.** The content was already in every page, escaped inside an
island's props attribute. Every visitor paid for those bytes and nobody with
scripting off could read a word of them. The worst of both.

**The fix.** Native `<details>` elements, rendered server-side. The browser
handles opening and closing with no script at all and gives correct disclosure
semantics for free. The remaining script only persists which disclosures are
open and keeps the hint escalation, so losing it costs a preference rather than
the content.

**It got smaller.** The heaviest page dropped to 84,962 bytes from 86,618, and
the JavaScript to 141,907 across 19 files from 144,123 across 21. The
Content-Security-Policy added later puts the page back to 86,078, which is a
fair trade and is still 14% under budget.

**The gate.** A pass with `javaScriptEnabled: false` that opens every disclosure
and asserts the prose is visible rather than merely present.

**axe is deliberately not run in that pass**, and this is worth stating because
it looks like an omission. axe injects itself into the page and cannot execute
without scripting. Attempting it produces `frame.evaluate: Resulting promise was
garbage collected`.

**The first plant proved nothing, and that is why there was a second.** Hiding a
hint with `display:none` also broke the JavaScript-enabled `waitForSelector`, so
the script died before it ever reached the no-JS pass. The real old failure mode
was replanted, an attribute filled in by script, and was caught on all 25 pages
while every scripted scan stayed clean.

**Accepted consequence.** Without JavaScript a learner can open hint 3 first.
`SolutionReveal`'s own comment already said the click existed to prevent
accidental reading rather than to gatekeep, and every hint is a plain file in a
public repository.

---

## Portability

### P1. `tse record` crashed under a different locale

`text=True` decoded subprocess output as US-ASCII under `LANG=C` with
`PYTHONUTF8=0` and raised on the ellipsis that appears in every recorded
`docker ps`. Fixed with explicit `encoding="utf-8"` on all eleven
`subprocess.run` calls. Nothing found it until CI ran under a different locale
from the author's, which is the class of bug that produced [P3](#p3-nothing-had-ever-run-this-on-a-machine-that-is-not-the-authors).

### P2. The course built on two different operating systems

Three stacks were on `python:3.12-alpine` and two on `python:3.12-alpine3.24`.
Both resolve to Alpine 3.24.1 today, which is exactly why nothing noticed. They
stop being the same image the day Alpine 3.25 ships, and then three stacks move
operating system and two do not, on a course where two tracks teach things that
depend on what the operating system does.

Because the two tags are identical right now, standardizing is provably a no-op:
`linux/01`, `api/01` and `docker/01` all verify against freshly built images.

The Codespace pre-pull listed only the floating tag, so networking and
observability waited on a download the pre-pull exists to avoid. The list is now
checked against the Dockerfiles in both directions.

**Planted.** One change, three failures: more than one Python base, a tag that
does not name its Alpine release, and a base the Codespace does not pre-pull.

### P3. Nothing had ever run this on a machine that is not the author's

**What was wrong.** Every check ran in the shell it was started from, with the
author's PATH, locale and exports. A check that passes because of something
already set there proves nothing about a stranger's laptop.

**The gate.** A `preflight.sh` section running `doctor`, `list`, `leaks` and
`links --offline` under `env -i` with a stripped PATH and `LANG=C` set on
purpose, because that is the environment that produced [P1](#p1-tse-record-crashed-under-a-different-locale).

**Planted.** The exact old defect, an ASCII decode of output carrying an
ellipsis, failed with the `UnicodeDecodeError`.

### P4. The stated Python requirement was wrong

**What was wrong.** The README said Python 3.11 or newer. Nothing had checked,
and it was wrong in the direction that costs a reader something: every suite and
all forty-two smoke assertions pass on **3.9.6**, which is the interpreter macOS
already ships with the Xcode command line tools.

That is not a detail. It means somebody on a Mac can clone this and start
without installing a Python at all, and an unverified requirement was sending
them away to do it for no reason.

**How it was found.** By [P3](#p3-nothing-had-ever-run-this-on-a-machine-that-is-not-the-authors),
which resolves `python3` to 3.9.6 rather than the 3.14 everything else had been
tested on.

**The gate.** `MINIMUM_PYTHON` in `tools/tse`, enforced with a message that says
what it found, and tested against what the README claims so the two cannot
drift.

### P5. The Codespace was not reproducible

Two features were pinned to `"latest"`, so two Codespaces built a month apart
were two different machines with no record of what changed. Both now name their
versions.

### P6. The CLI crashed on a machine with no Docker installed

Found by the macOS job, on its first run, which is the argument for having
added it.

Three functions promised to be safe without Docker and none of them were.
`image_in_node` is called from `tse cluster status` and its docstring says it
must not blow up. `node_platform` says it returns None when it cannot tell.
`cluster_exists` returns a bool. All three checked a return code, and
`subprocess.run` raises `FileNotFoundError` when the binary does not exist, so
there was never a return code to check.

**Why nothing had caught it.** The distinction is between a stopped daemon and
an absent binary, and only the first had ever been tested. Every machine this
code had run on had Docker installed: the author's, the Codespace, and the
Linux runners. `cmd_doctor` gets it right, and guards with `shutil.which`, which
is why the cold-start check in `preflight.sh` passed and proved nothing about
this. The one environment that would have exposed it was the one that was
priced out.

**The fix.** `run_tool` reports a missing binary as exit 127, which is what a
shell reports for the same thing, so every caller that already tested the
return code needed no change to benefit.

**Fixing the crash exposed the next problem, which is worse.** With the
traceback gone, `tse cluster status` answered a machine with no Docker with:

```
Cluster proveit does not exist. Create it with `tse cluster up`.
```

True, useless, and pointing at a command that could not work either. That is
precisely the failure this course is built to teach, an accurate signal
answering a narrower question than the one being asked, shipped in the tool
that teaches it. It now names the missing tool and points at `tse doctor`.

**Planted.** `run_tool` was changed back to let `FileNotFoundError` through:

```
ERROR: test_the_docker_helpers_survive_a_machine_with_no_docker
FileNotFoundError: [Errno 2] No such file
```

**What the macOS runner reports about itself**, printed by the job's first step
so the claim stays measured rather than remembered:

```
python3: Python 3.14.6, at /opt/homebrew/bin/python3
docker: absent, which is why this job skips the exercises
```

That is why the macOS job runs the CLI, the suites and the scans, and not one
exercise. `preflight.sh` on a real Mac is not a stopgap for that. It is the only
thing that can cover it.

---

## Content and documentation

### C1. The style rules covered `labs/` and two files at the root

The em dash rule read `labs/*/*/*.md` and the hints. The US spelling rule added
`meta.yaml`, `questions.json`, `reference/` and two files at the root. Neither
looked at the site, `SECURITY.md`, `CODE_OF_CONDUCT.md` or the workflows.

Two British spellings had been outside it the whole time, both in comments,
which is exactly why nothing found them.

Both rules now read every tracked file, through the leak scan's decoder rather
than a second one. Two files are exempt and both say why, and a test asserts
each exemption is still *needed*, so one that stops being needed becomes a
failure rather than an unchecked file. `aria-labelledby` is stripped first,
because it is an attribute name from the HTML specification and there is no US
spelling of it to prefer.

Failures name the line. `assertNotIn` prints its haystack, so an em dash in
`SECURITY.md` used to report by printing all of `SECURITY.md`.

### C2. Two dead links, one a live 404 on the published site

Nothing had ever confirmed a link goes anywhere. The start page and the
how-it-works page both pointed at this repository under its old name.

`tse links` classifies rather than treating all addresses alike: `127.0.0.1` and
`localhost` are addresses a learner types, not links, and are skipped and
counted so the skip is visible; relative paths must resolve on disk; fragments
must name a heading that exists; anything interpolated at runtime is not an
address.

**Only 404 and 410 fail.** A timeout or a 503 is somebody else's bad minute, and
a gate that goes red for that teaches people to ignore it.

The exemption for this repository's own URLs is derived from `git remote` and
the configured site rather than written down, which is the whole point: the old
name is not exempt, so the dead links could be found at all.

### C3. The link checker's slugger was wrong in both directions

**Found by this document.** `AUDIT.md` cross-references itself twenty-three
times. Two of those links were reported broken, and they were not.

`tse links` was turning punctuation into a hyphen. Both GitHub and Starlight use
github-slugger, which **deletes** it. So a heading ending in "the author's"
produces `the-authors` everywhere it is actually rendered, and the checker was
looking for `the-author-s`.

That is a two-way error, which is why it matters more than the one broken
anchor: a working link reads as broken, and a broken one reads as fine. The
checker had shipped the day before with this in it.

**The gate.** Three slug cases tested directly, including an apostrophe, inline
code in a heading, and typographic quotes. Plus a test that `AUDIT.md` resolves
its own anchors, because a document nobody can navigate is not a deliverable.

### C4. The README's table was a claim nobody checked

It happens to be correct, and it would have stayed correct-*looking* through the
next exercise added. Now checked three ways, including the spelled-out sentence
underneath, and against `TRACK_LABELS` in the site rather than a copy.

That last part found the real thing: the README called a track "Linux and CLI
foundations" and every page on the site called it "Linux and CLI".

### C5. The hint escalation rule described something the exercises do not do

See [Where the auditor was wrong](#w4-the-hints-had-not-drifted-the-measurement-had).

### C6. Both buttons on the front page served a 404

Found by clicking one. For as long as the site existed, its two hero actions
pointed at `/start` and `/how-it-works`, which resolve to `h-vance.github.io/start`
rather than `h-vance.github.io/prove-it-labs/start`. The only working action on
the page was `Repository`, which is an absolute URL and so could not be wrong
in this particular way.

**The cause is a difference worth knowing.** Starlight prefixes the base path
onto sidebar entries in `astro.config.ts` and does not prefix a hero action's
`link`, which goes into an `href` as written. Both spellings look correct.

**Confirmed against the live site rather than reasoned about**: `/start`
returned 404, `/prove-it-labs/start` returned 200.

### C7. The check that would have caught it was never handed the string

This is the more interesting half. `check_local_link` already refused a
site-absolute link that does not start with the site's base path, and it was
written after this exact bug bit once before, when the repository rename left
`how-it-works.mdx` pointing at the old name. The rule existed. The input never
reached it.

`extract_links` matches three shapes: a markdown link, an `href` attribute, and
a bare URL in prose. A hero action is none of those. It is a YAML value in a
page's frontmatter, so every link written that way had been invisible to the
checker since the day it was built.

**The gate.** Frontmatter is now read as well, for `.md` and `.mdx` only.
Deliberately not for `astro.config.ts`, which carries `link:` keys of its own
for the sidebar, and Starlight *does* prefix those: reading them here would
report a working link as broken, which is the fastest way to get a check
switched off.

**Planted with the defect that actually shipped**, and it fires offline, so
`preflight.sh` and CI would both have caught it:

```
site/src/content/docs/index.mdx:18: /start
      a site link that does not start with the site's base path '/prove-it-labs'
site/src/content/docs/index.mdx:21: /how-it-works
      a site link that does not start with the site's base path '/prove-it-labs'
```

### C8. The self-link exemption was a prefix where it needed to be exact

`classify_link` skipped anything starting with one of this repository's own
addresses. For the repository URL that is right, and necessary: while private,
the README badge and every other path beneath it answered 404 together.

Applied to the Astro `site` value it is wrong, and expensively so.
`https://h-vance.github.io` is a prefix of every page the site publishes, so
adding a README link to the live site created an entry that was exempt from
checking on the day it was written. The single address most worth checking was
the one being skipped.

**The fix** separates the two rather than sharing one mechanism between them:
repository addresses match as prefixes and expire when the repository goes
public, and configured addresses match exactly and never expire, because
Astro's `site` is half an address rather than a link that could resolve.

**Measured.** Link coverage went from 42 to 56.

### C9. Three required tools were named nowhere a reader would look

`tse doctor` probes for `kubectl`, `kind` and `jq`. None of the three appeared
in `README.md` or `CONTRIBUTING.md`. Someone following the README would have
installed Docker and Python, started the Kubernetes track, and hit a wall the
documentation had never mentioned.

**Not fixed by writing a requirements table.** That would be a second copy of
the list, and this repository has been caught by second copies three times: a
README claiming Python 3.11 when the floor was 3.9, an exercise count nobody
checked, and a dozen sentences calling the repository private after it went
public. `tse doctor` is the list, now grouped by what needs what so a gap costs
a reader one track rather than leaving them guessing, and a test fails the
build if it learns to require something the prose does not name.

**Planted**, by teaching `doctor` a tool the docs do not mention:

```
tse doctor requires rg and neither README.md nor CONTRIBUTING.md names it.
A reader cannot install what nothing tells them about.
```

### C10. Nothing checks that this document is still true

Every other tracked file is held to the present tense by a rule that refuses
any claim this repository is private. `AUDIT.md` is exempt, because describing
the private period accurately is the whole point of it.

That exemption is correct and it has a cost, which showed up within hours. The
section now titled *What the flip bought* spent an afternoon as *Deferred to
the public flip*, listing as pending seven things that had already shipped, and
stating that both workflows were disabled when four were running.

**The gate is narrow on purpose.** Two exact strings, held in
`test_content.py` rather than repeated here, each a phrase that was true when
written and became false at a known moment. A broader rule over a document
whose subject is the past would fire on correct sentences, and a gate that
fires on correct work gets switched off.

They are not quoted in this paragraph, and that is not squeamishness: a
document cannot both forbid a phrase and contain it. Writing them out here made
the gate fail on the section describing the gate, which is how this sentence
came to exist. The same problem already had the same answer one level up, where
`test_content.py` is exempt from the style rules because it holds the pattern
table those rules are written from.

It does not make this document self-checking. It catches the one way it has
actually been observed to rot.

### C11. A setting a reader could change, that could change nothing

`README.md` and the home page both said stretch material could be hidden
rather than skimmed past, and *How this works* carried the control that did
the hiding. It was a real component, correctly written, with its state applied
before first paint so nothing would flash in and out.

Every one of the twenty six exercises is `tier: core`. There has never been a
single piece of stretch material in this repository. Somebody who found the
switch and used it watched the page not change, and had no way to tell whether
they had misunderstood the feature or the site was broken.

Measured, not remembered: `grep -rh "^tier:" labs/*/*/meta.yaml | sort | uniq
-c` returns 25 core and no stretch.

This is the same shape as the two hero buttons in C6. A promise written down,
nothing behind it, and nothing looking. It is worth naming that shape because
three separate instances of it have now been found in a repository whose whole
argument is that its claims are checked, and all three survived a full audit
that was looking for exactly this.

**What changed.** The claim and the control are gone. `TierToggle.tsx` and its
CSS rule are kept, unimported and therefore costing nothing in the build, with
the three steps to restore them written at the top of the component. The inline
script came out of `astro.config.ts`, where it was reading a setting nothing
writes on all thirty one pages.

**The gates**, two of them, because the claim has two forms. Prose that says
stretch material can be hidden, and a page that renders the control. Either
requires at least one exercise to declare `tier: stretch`, which makes the rule
self-correcting: the day the content exists, the claim is allowed back.

Planted against, by putting each back:

```
README.md:160 says stretch material can be hidden, but no exercise declares
`tier: stretch`, so the control has nothing to hide. Either write the stretch
material or drop the claim.

site/src/content/docs/how-it-works.mdx renders <TierToggle />, but no exercise
declares `tier: stretch`. Someone toggling it would watch the page not change.
```

**And it fired on this section.** Writing the finding up put the forbidden
phrase into `AUDIT.md`, so the rule refused the document explaining the rule.
That is the third time a gate here has collided with the file describing it,
after C10 and after `test_content.py` being exempt from the style rules that
read its own pattern table.

`AUDIT.md` is now exempt, and unlike C10 the exemption is the right answer
rather than the second-best one. This rule exists to stop a reader being
offered a setting that cannot do anything, and nobody is offered a feature by
an audit explaining why it was removed. Every surface that does the offering,
the README and every page under `site/`, is still read.

### C12. The difficulty words and the range they cover were never joined

Every exercise declares a difficulty, and `test_content.py` asserts it falls in
1 to 5. The only list of words covering that range was an anonymous array
literal inside the exercise page template, six strings long, with nothing
connecting it to the assertion.

Nothing was broken. Only 1, 2 and 3 are used, so `Hard` and `Brutal` were
simply unreachable. The defect is the join, not the values: indexing past the
end of a JavaScript array returns `undefined` rather than raising, so widening
the permitted range to 6 would have rendered an empty difficulty on every page
that used it, silently, with every gate green.

This one was found by looking for the shape of C11 elsewhere rather than by a
report, and it is the milder version of it: not a promise with nothing behind
it, but a promise with nothing holding it in place.

**What changed.** The words moved to `DIFFICULTY_LABELS` in `site/src/lib/labs.ts`
behind a function that throws at build time rather than rendering a blank, and
the permitted range became a named constant both sides can be checked against.

**The gate** runs in both directions, because a list can drift either way.
Planted against by removing a word, and then by adding one:

```
Difficulty 5 is permitted by VALID_DIFFICULTIES but has no label in
site/src/lib/labs.ts, so an exercise using it would render a blank.

site/src/lib/labs.ts labels difficulties above 5, which VALID_DIFFICULTIES does
not permit, so no exercise can ever show ['Punishing'].
```

### C13. Every page wrote a record, and nothing ever read one back

Six families of `localStorage` key are written by this site: the quiz answers,
how far into the hints somebody went, whether they opened the solution, the
notes they wrote in the scratchpad, and the commands they replayed. Twenty five
exercises each writing their own.

Nothing had ever read any of them back. Every component wrote its key and
forgot about it, so somebody returning after a week had a complete record of
their own work sitting in their own browser that no page would ever show them.

`tse progress` compounded it. It has printed *"Export for the site with `tse
progress --json`"* since it was written, and `grep -rn progress site/src`
returned nothing but the word appearing in three unrelated sentences. The site
had never read that export. The line was an intention that reads as a fact.

**What changed.** A page at `/proof`, built on the state that was already
there rather than on anything new. It reports what happened on the site, and
refuses to call any of it proof.

That refusal is the design. Nothing typed into a page fixes a system, so no
amount of reading, answering or replaying can turn an exercise's proof question
into a statement. Only `tse check` knows, because only `tse check` ran the
assertions against real containers. Pasting its output is the one thing that
changes a question into a claim, which is what finally makes the CLI's export
line true.

**The reward is the content, not a token.** Every exercise already carries a
proof question, and a passed exercise restates it: *"Can I prove the
application started at all?"* becomes *"You can prove the application started at
all."* No points, no streaks, no badges, no levels. A page that awarded a token
for opening a hint would contradict every other page in this repository, and the
restatement costs no metadata that did not already exist.

**One thing deliberately not shipped.** The quiz stores which option was
picked, which is only a score if you also hold the answer key. Scoring on the
proof page would have meant putting the correct index for all seventy five
questions into the HTML of a page anybody can read the source of. `Quiz.tsx`
stores its own score instead: derivable from what already sat beside it, so no
new fact about a learner, and the one form the other page can read without
being handed the answers.

**The gate drives it rather than scanning it.** `a11y.mjs` now pastes something
invalid, asserts the refusal wrote nothing, pastes a real record, scans the
proven state, and clears it. It earned that on its first run, before any defect
was planted, by catching the new page skipping from `h1` straight to `h3`.

Planted against by stopping the input reaching the check, which is the failure
mode C7 was:

```
axe: the proof record never showed a refused import, so that state went
unchecked.
```

### C14. The home page described the course instead of running it

The landing page opened with a tagline and four cards. One explained that the
tickets are symptom-only. One explained that the grader shows its evidence. One
explained that the terminal replays real output.

Every word was true and none of it was evidence, on a site whose entire
argument is that a claim and a demonstration are different things. The first
thing a reader met was the course talking about itself.

**What changed.** The two things being described now happen on the page. A
reader meets `docker/01`'s actual ticket and its actual terminal, loaded from
`labs/` through the same loader the exercise pages use, so the front page
cannot drift from the exercise and CI re-verifies its recorded output against a
freshly provisioned stack on every push.

**Two layout defects found while measuring rather than guessing.** Starlight's
splash hero is built around an image this page does not have. Its grid is
`7fr 4fr`, so the tagline was squeezed into two thirds of the width while the
remaining third sat empty, and its block padding reaches `10rem` to balance a
picture. At a 1100px viewport that was 365 pixels of nothing between the
buttons and the first real content.

**And one real defect in a gate, exposed by the change.** The terminal's
command list is a toggle, and whether it is open is remembered per exercise
rather than per page. `a11y.mjs` clicked it unconditionally. With `docker/01`'s
terminal now on two pages, whichever the gate reached second in a theme's
context clicked the list shut and then waited thirty seconds for content it had
just hidden. It failed loudly and correctly stopped the build, so this is a
maintenance bug rather than a check that could not fail, but it is the first
time two pages in this site have shared a storage key and nothing had
anticipated it.

### C15. Nothing measured a stylesheet or a font

`check-pages.mjs` held a budget for the heaviest built page and a budget for
total JavaScript, and between them they gave the comfortable impression that
page weight was watched.

CSS was not measured at all, and neither was anything else a browser downloads.
There were no fonts to miss, which is exactly why nobody noticed: the gap was
invisible until something walked into it.

A webfont is the easiest kilobyte on a site to spend. Adding a second family,
or shipping every axis of a variable one, or leaving an old face behind after
swapping it out, would have added hundreds of kilobytes to what a first-time
reader downloads with all three existing gates green.

**What changed, and in this order.** The budget first, then the font. Measured
at the moment it landed: 157,486 bytes of CSS and no fonts, going to 203,198
with one typeface at 45,712. Two thirds of that CSS is Pagefind's own search
interface, vendored by the search integration and not ours to trim.

**The typeface.** IBM Plex Sans, SIL Open Font License, from a pinned
dependency rather than committed here, so there is one copy, the lockfile
records its provenance, and Dependabot watches it like everything else. The
site's own policy is `default-src 'none'` with `font-src 'self'`, so a font
from anywhere else would be refused by the browser rather than merely
discouraged.

Three choices, each measured against what it bought:

| Choice | Cost avoided |
|---|---|
| Weight axis only, not width | 19,776 bytes |
| Upright only, no italic file | 50,184 bytes |
| Latin subset only | the rest |

Dropping italic is the one worth stating plainly, because it is a visible
compromise rather than a free win. The entire built site contains four `<em>`
elements across three of its thirty two pages. Those four now get a synthetic
oblique, which is worse than a real one, and buying a 50KB file heavier than
the typeface itself to fix four words would have been the worst trade on the
page.

**The accent** was chosen around what the palette already meant rather than by
preference. Green is a correct answer, red is a wrong one, and the orange rule
down the side of a ticket is the customer's problem. All three were here first
and all three carry meaning, so an accent sharing a hue with any of them is a
link that looks like a judgement. The values were then adjusted until the
contrast gate stopped reporting violations, rather than until they looked about
right.

**Two gates**, planted against:

```
orphan.woff2 ships but no stylesheet refers to it, so nothing will load it.

Stylesheets and fonts are 319,587 bytes across 9 files, over the 260,000
budget. 3 of them are fonts.
```

The second plant is the realistic one. It is what happens when somebody adds
the italic file and a width axis without thinking about it, which is a change
of two lines.

### C16. Every service could take back what it had dropped

The containment gate reads six keys off every service in every stack and
insists on the strong form of three of them: `read_only: true`, `cap_drop`
containing `ALL`, and `no-new-privileges:true`. It had never looked at
`cap_add`.

A service could therefore drop every capability, add back exactly the one it
wanted, and report as fully sealed, because the gate only ever asked what was
given up and never what was taken back. `cap_drop: ALL` beside a `cap_add` is
not the posture the other five keys advertise.

Nothing in the course did this. The hole was found while adding the networking
resolver, which binds port 53 and is the first service here with a reason to
want `NET_BIND_SERVICE`. It turned out not to need it: Docker sets
`net.ipv4.ip_unprivileged_port_start=0` inside containers, so the resolver
binds 53 as an unprivileged user with everything dropped, which was confirmed
on a live daemon before the design leaned on it and is explained in
`resolver.py` where a daemon configured otherwise will land.

Closing a hole at the moment something first has a reason to use it, rather
than after it has been used, is the whole reason to write the gate now.

**Not a ban.** A service that genuinely needs a capability declares
`x-containment` with the reason, which is the escape every other rule in this
group already offers. The gate refuses the silent form, not the argued one.

**The gate, planted against:**

```
labs/networking/_stack/compose.yaml: resolver drops all capabilities and adds
'NET_BIND_SERVICE' straight back, which is not the posture the keys beside it
advertise. Say why in x-containment, or do without it.
```

---

## Cost

CI was measured rather than estimated, from a real run.

| | |
|---|---|
| Jobs | 29 |
| Real work | 74.1 min |
| Billed | 90 min |
| Lost to per-job rounding | 16 min (18%) |
| Step-level work inside the 25 matrix jobs | 37.5 min |
| Job-level time for the same | 68.4 min |
| **Per-job overhead** | **~31 min** |

The Docker matrix was 73 of 81 billable minutes: a private repository's entire
2,000-minute monthly allowance in 27 pushes. A nightly schedule on top of that
would have been ~2,400 minutes a month against the same allowance. It was
removed.

**Three changes, in order of size.**

1. **Path-aware selection.** `tse affected` verifies only the exercises a change
   can reach.
2. **One job per stack, not per exercise.** Eight jobs instead of twenty-six,
   grouped by the stack an exercise actually runs against rather than its track,
   because `mixed/01` borrows the docker stack and `mixed/02` borrows api.
   Grouping by track would have built both an extra time. Roughly 76 billable
   minutes to 30.
3. **The expensive half moved off CI entirely.** `tools/tests/preflight.sh` runs
   it on the machine that pushes, for nothing, picking exercises with the same
   rule the workflow uses so it cannot check less than CI would.

**The honest trade on grouping.** A stack that will not come up fails its whole
group, and a group runs in sequence so its wall time is the sum rather than the
max. State is not shared: `tse verify` still force-recreates containers per
exercise, so what a group reuses is the image cache and nothing else.

**The loop deliberately does not use `set -e`.** Every exercise in a group runs
even after one fails, so a single run reports all of them. Verified locally with
a planted bad exercise: it continued, counted, and exited 1.

**A method note.** The matrix summary was first written as Python inside a shell
string inside YAML, and the quoting was wrong twice, with no way to test a fix
that did not cost a push. It moved into `tse affected --for-github`, which is
covered by tests.

---

## Where the auditor was wrong

Four times. All four were caught by the method rather than by review.

### W1. The networking CA fix was reported as working before the hard case was tested

Chaining the build stages does not fix independently built compose service
images. Pruning the cache between two single-service builds still splits them.
See [A1](#a1-the-networking-stack-could-mint-two-different-lab-cas).

### W2. A fix for a fail-open guard introduced the same fail-open

`timeout ... bash -c` broke three commits of CI and made `sql/03` pass in a
broken state. See [A2](#a2-a-regression-the-auditor-introduced-and-the-test-caught).

### W3. `preflight.sh` caught its own author twice on its first run

An `A && B || C` construct, which is precisely the class the raised shellcheck
severity had been added to find, and a `run` call inside a subshell that
discarded the pass/fail counters, so a failing site check printed FAIL and then
said "Safe to push."

### W4. The hints had not drifted; the measurement had

**What was claimed.** Counting code fences said six exercises had put commands
into hint 2, all in the newest tracks, and that they should be rewritten.

**What was true.** Reading them showed the opposite. Hint 2 gives the commands
that *gather evidence*; hint 3 shows what the evidence says and what to change.
That is a real escalation and a better one than the rule described. The right
measurement is where the *fix* appears: `tse apply` and `tse check` are what
somebody runs after changing something, and across all twenty-six exercises
they are in hint 3 sixteen times and in hint 2 **never**.

Acting on the first measurement would have stripped good teaching content out of
the six hardest exercises. `CONTRIBUTING.md` now says what the exercises
actually do, and that is what is gated.

---

## Accepted

Decisions taken deliberately, with the number that drove them.

**macOS in CI.** Hosted macOS runners bill at **10x** the Linux rate. A macOS
matrix would be roughly **730 billable minutes per push** against a
2,000-minute allowance and would not survive a week. `preflight.sh` runs the
full matrix on the machine the labs are developed on, which is macOS, for
nothing. That is real coverage on a real platform, and it is worth more than a
job nobody could afford to keep.

**Digest-pinning base images.** Rejected. It defeats Dependabot's ability to see
the image and buys reproducibility this course does not need, since these run
for ten minutes on a laptop and a stale base is a security problem rather than a
stability feature. The tag now names the Alpine release, which is the part that
was actually causing drift.

**Building the devcontainer in CI.** It needs Docker-in-Docker on a runner and
is expensive. The parts that can be checked without building it are checked.

**`unsafe-inline` for style attributes in the CSP.** The syntax highlighter
writes 2,357 of them and an attribute cannot be hashed. Unlike a script, it
cannot call anything.

**A learner without JavaScript can open hint 3 first.** Consistent with the
design's stated intent. Every hint is a plain file in a public repository.

**Python 3.9 as the floor.** It is past end of life. Supporting it costs nothing
because the code already works there, it means a Mac needs no install at all,
and the cold-start check keeps it true rather than letting it rot.

---

## What the flip bought

This section used to be a list of things waiting on the repository going
public. It went public on 2026-08-16, every row of that list landed the same
day, and what follows is what actually happened rather than what was expected.

**The arithmetic that forced it.** Verifying the whole course is about eighty
minutes of runner time. A private repository gets two thousand a month, which
is roughly twenty two pushes, and the allowance was reached during this audit.
The last CI run before the flip did not fail a test: it never started, and said
so, `The job was not started because recent account payments have failed or
your spending limit needs to be increased`. On a public repository standard
runners are free and unmetered. The first full course run afterwards reported
**zero billable milliseconds across twelve jobs**.

| | What it turned out to be |
|---|---|
| CodeQL | Runs on `actions`, `javascript-typescript` and `python`. Found four, three of them the course working as designed and dismissed with reasons, one a genuinely unused import |
| `dependency-review-action` | Runs on every pull request |
| macOS | Added, and it failed on its first run for a real reason. See P6 |
| Exercises on pull requests | The bigger find. See below |
| Branch protection | Seven required checks, chosen so that a legitimately skipped job cannot block a merge |
| Secret scanning and push protection | On. Fired once, on the synthetic Slack token in `test_content.py` that exists to prove the leak scan catches that format. Resolved as used in tests |
| Private vulnerability reporting | On, which is what makes `SECURITY.md`'s advisory link resolve rather than 404 |
| Pages | Publishing. The gate on `github.event.repository.private == false` started working with nothing to remember |

**CodeQL does read `tools/tse`.** This document previously recorded that as
unknowable from here: three thousand lines of Python in a file with no `.py`
extension, and no way to tell whether the extractor finds it on the shebang
alone. It is knowable, and the run answers it. Thirteen tracked `.py` files
exist and CodeQL reported scanning fourteen Python files. The extra one is the
CLI. No rename was needed, which was the alternative on the table.

**The `workflow_dispatch` gate was the expensive mistake.** The exercise matrix
and learner loop had been restricted to runs started by hand, because together
they were 76 of the workflow's 90 billable minutes. That restriction outlived
its reason and quietly became worse than what it saved: an ordinary push and a
contributor's first pull request both went green **without provisioning a
single container**. A push went from three jobs to twelve when it was removed.
A green badge that has verified nothing is worse than no badge.

**The two exercises that failed before the flip now pass.** `sql/03` and
`observability/02` failed on three consecutive runs, deterministically, on
Linux while passing on macOS. Both pass in CI now. The honest version is that
this was never diagnosed: the run logs had expired by the time anyone looked,
and the stack under one of them changed in between, since `sql/03` reads an
`EXPLAIN` plan and this audit moved that database onto a tmpfs `PGDATA`. A
plausible cause is not a proven one. What can be said is that they pass, and
that the nightly schedule now exists to catch it if that stops being true.

---

## Not covered

The most useful section for anyone reading this as a work sample.

- **The devcontainer is never built.** Its contents are checked; that it comes
  up is not.
- **No performance budget beyond page weight.** Nothing measures render time,
  interaction latency or Core Web Vitals.
- **No test of the site under a screen reader.** axe is a static analysis of the
  accessibility tree, not a test that the page is usable by ear.
- **The Kubernetes track is verified against `kind` only.** Nothing checks it on
  a real cluster or another distribution.
- **The networking track teaches no routing.** DNS is now taught by
  `networking/03`. Routing is named in the track and is not.
- **Only the README's counts are gated.** `ReadmeCounts` reads the track table
  against the real exercises, which is why that table cannot go stale. Nothing
  reads the counts written into prose elsewhere. Adding one exercise falsified
  five sentences across `CONTRIBUTING.md` and this file, all found by grep
  rather than by a gate. A rule general enough to catch them would also have to
  tell a live claim from a historical one, and this document is full of the
  second kind.
- **`tse links` checks external URLs but not their content.** A link that
  resolves to a parked domain passes.
- **No mutation testing.** The gates are proven by planted defects chosen by the
  auditor, which is better than nothing and is not exhaustive.
- **The scrubber's rule set is empirical.** It covers what has been seen. A new
  kind of machine-specific output would need a new rule, and nothing predicts
  those.
- **The screenshots in the README are not read by the leak scan.** A PNG is not
  text, so the four in `docs/screenshots/` are named in `LEAK_BINARY` and
  skipped. What stands in for reading them is that a script regenerates all
  four from `site/dist`, so every pixel originates in a file the scan does
  read. A screenshot taken by hand would not have that property.
- **Nothing checks that this document is still true.** Every other tracked file
  is held to the present tense by a rule that refuses any claim this repository
  is private. `AUDIT.md` is exempt from it, because recording the private
  period is its job, and that exemption is why this section spent an afternoon
  describing a repository that had already changed. See C10.
- **The monospace face is still whatever the reader's machine supplies.** The
  sans is now shipped and identical everywhere; the terminal is not, and the
  terminal is the product. Recorded output that lines up on one machine can
  wrap on another, and the screenshots in the README are a picture of one
  laptop's idea of monospace. A second face would cost about 30KB against
  56,000 bytes of remaining budget, so this is a decision that has not been
  made rather than one that could not be.
- **The proof record believes whatever is pasted into it.** Anyone can type
  `{"completed": [...]}` and watch every question turn into a claim. There is
  no signature and there will not be one: the record is for the person doing
  the work, it is stored only in their own browser, and a course that made its
  learners prove things to it rather than to themselves would have the wrong
  relationship with them. Worth stating plainly, because a reader could
  otherwise mistake it for an attestation.
- **The evidence layers are free text.** Seventy one distinct phrases across
  twenty six exercises, sixty five of them used exactly once, so they cannot
  support the thing they look like they should support: a map of which layers
  somebody has actually gathered evidence at. Turning them into a controlled
  vocabulary is content work on all twenty six exercises, and it is the
  obvious next thing the proof record wants.
- **26 exercises against a target of 100.** Depth inside existing tracks rather
  than new ground, and not an audit finding.

---

## The gates as they stand

Everything below runs from `tools/tests/preflight.sh`, on any machine, needing
nothing installed beyond Docker and Python.

| Gate | Scale |
|---|---|
| `test_content.py` | 146 tests |
| `test_scrub.py` | 53 tests |
| `test_rubric.py` | 20 tests |
| `test_meta.py` | 18 tests, incl. parity against real PyYAML |
| `smoke.sh` | 42 assertions |
| `tse leaks` | 398 files, 24 patterns everywhere and 26 in recordings |
| `tse links` | 56 links, including frontmatter and every README badge |
| Cold start | 4 commands under `env -i` with `LANG=C` |
| shellcheck | every shell script, `--severity=info` |
| Site types | `astro check`, `noUncheckedIndexedAccess` on |
| `check:pages` | three budgets: page weight, JavaScript, and stylesheets and fonts |
| `check:terminal` | 150 assertions across 9 normalization cases |
| `a11y.mjs` | 330 axe checks, 32 pages, 2 themes, plus 320px reflow and no-JS |
| CSP | enforced by a browser on 32 pages in both themes |
| `tse verify` | 26 exercises must fail broken and pass fixed |
| `tse record --check` | every transcript still matches a real run |

It ends on `Safe to push.` or `Not safe to push.`

**Added on the day this went public**, each planted against before it was
trusted, and each closing a finding above:

| Gate | Refuses |
|---|---|
| Downloaded binaries | A file fetched over the network and installed without its checksum verified first (S6) |
| Present tense | Any tracked file except this one claiming the repository is private (C1) |
| This document | The two exact phrases the flip made false (C10) |
| Python floor on the badge | A shield stating a version the CLI does not enforce |
| Badge and workflow parity | A badge for a workflow that does not exist, and a workflow no badge shows |
| Requirements | A tool `tse doctor` requires that the docs do not name (C9) |
| Frontmatter links | A site-absolute link in a page's frontmatter missing the base path (C7) |
| Docker absence | The CLI raising rather than reporting on a machine with no `docker` binary (P6) |

**Added by the makeover**, on the same terms:

| Gate | Refuses |
|---|---|
| Stretch, in prose | Any file that offers to hide stretch material when no exercise declares it, this document excepted (C11) |
| Stretch, on a page | A page rendering the control while the content it hides does not exist (C11) |
| Difficulty coverage | A permitted difficulty with no word, and a word no difficulty can reach (C12) |
| Proof questions | A proof question the page cannot restate as a claim, because it does not open "Can I" |
| The proof record | A run that never made the page refuse an import, accept one, and clear it (C13) |
| Styles and fonts | More than 260,000 bytes of them, measured across the whole build (C15) |
| Orphan fonts | A font that ships when no stylesheet refers to it (C15) |

**Added by the DNS exercise**, on the same terms:

| Gate | Refuses |
|---|---|
| Capabilities taken back | A service that drops all capabilities and adds one back without saying why (C16) |
| Connect timing | A recording that compares a duration only the machine's speed decides (networking/03) |

CI adds what a laptop cannot: every exercise on every pull request, CodeQL on
three languages, dependency review, the CLI on macOS, and a nightly run of the
whole course to catch a base image moving under a lab with nobody committing
anything.
