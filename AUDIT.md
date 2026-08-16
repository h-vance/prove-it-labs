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
- [Checks that could not fail](#checks-that-could-not-fail), seven of them
- [Correctness](#correctness)
- [Security](#security)
- [Accessibility](#accessibility)
- [Portability](#portability)
- [Content and documentation](#content-and-documentation)
- [Cost](#cost)
- [Where the auditor was wrong](#where-the-auditor-was-wrong)
- [Accepted](#accepted)
- [Deferred to the public flip](#deferred-to-the-public-flip)
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

The largest single category. Seven checks were passing without checking
anything.

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
2. **One job per stack, not per exercise.** Eight jobs instead of twenty-five,
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
somebody runs after changing something, and across all twenty-five exercises
they are in hint 3 fifteen times and in hint 2 **never**.

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

## Deferred to the public flip

Each of these becomes free or possible the moment the repository is public.
None are blocked on anything else.

**Written, not yet run.** `.github/workflows/security.yml` now holds CodeQL for
`actions`, `javascript-typescript` and `python`, and `dependency-review-action`
on pull requests. Both are free on a public repository and billed on a private
one, so the file exists and has never executed. Writing a scanner and running it
are different claims and this document should not confuse them. One thing to
read on the first run: `tools/tse` is three thousand lines of Python in a file
with no `.py` extension, and whether the extractor finds it on the shebang alone
is not knowable from here. If the reported line count for Python is near zero,
the largest file in the repository is not being scanned.

| | Why it waits |
|---|---|
| Running CodeQL and dependency review | Written and committed. Needs the flip, plus the dependency graph switched on |
| macOS matrix | Standard runners are free and unmetered on public repositories |
| Docker layer caching (`type=gha`) | Cannot be measured without a run, and an unmeasured gate is what this audit exists to find |
| Re-enabling both workflows | The allowance is spent until it resets |
| Branch protection on `main` | Returns HTTP 403 on a private repository on the free plan. `CODEOWNERS` does nothing until it exists |
| Fork pull request approval | Not configurable while private. Matters because removing the `workflow_dispatch` gate lets a stranger's exercise files run in Docker on a runner |
| Secret scanning, push protection, private vulnerability reporting | The whole `security_and_analysis` block is unavailable, and reads as null today |

Both workflows are currently disabled. The GitHub Pages publish step is already
gated on `github.event.repository.private == false`, so it skips cleanly now and
starts working at the flip with nothing to remember. The link checker's
self-exemption expires the same way, on its own, and is described in S7.

**The one thing that cannot be checked before the flip.** The last five `verify`
runs failed and their logs have expired, so the first version of this paragraph
recorded the cause as unknowable and moved on. That was giving up too early.
The run logs expire; the check run annotations do not, and they name both the
failing step and the reason.

Read that way, the five runs are two different stories.

| Run | What actually failed |
|---|---|
| 20:03 | Nothing ran. `The job was not started because recent account payments have failed or your spending limit needs to be increased` |
| 19:49 | `sql/03` and `observability/02`, both on "fails broken and passes fixed" |
| 19:17 | The same two, plus `docker/02` on "recorded output still matches the system" |
| 19:01 | The same two again |
| 18:44 | `networking/01` on "recorded output still matches the system" |

So the red badge is not one failure, it is a billing wall in front of a real
one. Two exercises failed on three consecutive runs, which is not flake.

**Neither of them is timing dependent**, which was the first guess and was
wrong. `sql/03` deliberately asserts on the query plan rather than on elapsed
time, and says so in a comment: a wall clock threshold there would be flaky and
misleading. `observability/02` asserts that one reference appears in each
service's log. Both are deterministic, so both failed for a real reason on
Linux while passing on the machine they were written on.

What that reason is stays open. Both now pass here, in a full
`preflight.sh --all`, and the stack under one of them changed after these runs:
`sql/03` reads an `EXPLAIN` plan, and the audit moved that database onto a
tmpfs `PGDATA` running as `postgres`, which changes the I/O costs a planner
makes its choices from. That could have fixed it or moved it. Guessing which is
exactly what this document is against.

The honest statement is therefore narrower than "probably fixed": two exercises
have a known, reproducible, unexplained difference between Linux CI and macOS,
last seen before a change that could plausibly affect one of them. The first
`verify` run after the flip is the experiment, and going in expecting green
would be the wrong posture.

---

## Not covered

The most useful section for anyone reading this as a work sample.

- **The devcontainer is never built.** Its contents are checked; that it comes
  up is not.
- **No dependency vulnerability scanning.** Dependabot opens version bumps; it
  is not an advisory gate. Deferred to the flip.
- **No performance budget beyond page weight.** Nothing measures render time,
  interaction latency or Core Web Vitals.
- **No test of the site under a screen reader.** axe is a static analysis of the
  accessibility tree, not a test that the page is usable by ear.
- **The Kubernetes track is verified against `kind` only.** Nothing checks it on
  a real cluster or another distribution.
- **The networking track is two exercises and both are TLS.** DNS and routing
  are named in the track and not yet taught.
- **`tse links` checks external URLs but not their content.** A link that
  resolves to a parked domain passes.
- **No mutation testing.** The gates are proven by planted defects chosen by the
  auditor, which is better than nothing and is not exhaustive.
- **The scrubber's rule set is empirical.** It covers what has been seen. A new
  kind of machine-specific output would need a new rule, and nothing predicts
  those.
- **25 exercises against a target of 100.** Depth inside existing tracks rather
  than new ground, and not an audit finding.

---

## The gates as they stand

Everything below runs from `tools/tests/preflight.sh`, on any machine, needing
nothing installed beyond Docker and Python.

| Gate | Scale |
|---|---|
| `test_content.py` | 125 tests |
| `test_scrub.py` | 53 tests |
| `test_rubric.py` | 20 tests |
| `test_meta.py` | 18 tests, incl. parity against real PyYAML |
| `smoke.sh` | 42 assertions |
| `tse leaks` | 394 files, 24 patterns everywhere and 26 in recordings |
| `tse links` | every link in the tree |
| Cold start | 4 commands under `env -i` with `LANG=C` |
| shellcheck | every shell script, `--severity=info` |
| Site types | `astro check`, `noUncheckedIndexedAccess` on |
| `check:pages` | page weight and JavaScript budgets |
| `check:terminal` | 150 assertions across 9 normalization cases |
| `a11y.mjs` | 324 axe checks, 31 pages, 2 themes, plus 320px reflow and no-JS |
| CSP | enforced by a browser on 31 pages in both themes |
| `tse verify` | 25 exercises must fail broken and pass fixed |
| `tse record --check` | every transcript still matches a real run |

It ends on `Safe to push.` or `Not safe to push.`
