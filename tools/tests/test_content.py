#!/usr/bin/env python3
"""Structural and editorial tests for every exercise.

CONTRIBUTING states rules about how an exercise must be written. Rules that are
only written down decay, so the ones that can be checked are checked here.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import re
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_loader = importlib.machinery.SourceFileLoader("tse", str(ROOT / "tools" / "tse"))
_spec = importlib.util.spec_from_loader("tse", _loader)
tse = importlib.util.module_from_spec(_spec)
sys.modules["tse"] = tse
_loader.exec_module(tse)

EXERCISES = tse.load_exercises()

REQUIRED_META = ("id", "track", "title", "proof_question", "stack", "tier",
                 "difficulty", "minutes", "interview_relevance", "teaches")
VALID_TIERS = {"core", "stretch"}
VALID_STACKS = {"compose", "kind", "none"}

REQUIRED_SOLUTION_SECTIONS = (
    "## What the evidence proved",
    "## Root cause",
    "## Customer update",
)

QUESTIONS_PER_EXERCISE = 3
OPTIONS_PER_QUESTION = 4

# "All of the above" tests whether the reader noticed a pattern in the list,
# which is a different skill from the one this course is about.
LAZY_OPTIONS = re.compile(r"\b(all|none|both) of (the )?(above|these|them)\b", re.IGNORECASE)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _contains_run(haystack: list[str], needle: list[str]) -> bool:
    size = len(needle)
    return any(haystack[i:i + size] == needle for i in range(len(haystack) - size + 1))


def giveaway_overlap(question: str, option: str, *, window: int = 5) -> str | None:
    """The longest run of words an option copies verbatim from its question.

    A correct option that echoes the question's own phrasing can be picked by
    matching strings, without understanding anything. Returns the offending
    run, or None when nothing of at least `window` words is shared.
    """
    asked = _words(question)
    answered = _words(option)
    longest: list[str] = []

    for start in range(len(answered)):
        for end in range(start + window, len(answered) + 1):
            run = answered[start:end]
            if not _contains_run(asked, run):
                break
            if len(run) > len(longest):
                longest = run

    return " ".join(longest) if longest else None

# Terms that name the failing layer or hand over the diagnosis. A ticket
# containing one of these has told the learner what to look at, which is the
# single thing this course refuses to do.
SPOILER_TERMS = re.compile(
    r"\b("
    r"docker|dockerfile|container|compose|image tag|"
    r"kubernetes|kubectl|pod|replicaset|namespace|selector|"
    r"postgres|postgresql|psql|sql query|"
    r"environment variable|env var|"
    # Stems take \w* because "throttl" alone would not match "throttling":
    # the trailing \b on the group requires the word to end there.
    r"rate.?limit\w*|throttl\w*|scopes?|revok\w*|deprecat\w*|"
    r"dns|hostname|localhost|"
    # SQL, networking, Linux, and observability vocabulary. Deliberately not
    # banned: "report", "slow", "disk", "space", and "log", because those are
    # what a customer genuinely says and a lint that fights good writing gets
    # switched off.
    #
    # "certificate" is banned, and this comment used to claim the opposite. On
    # a track where the whole question is which of several trust failures it
    # is, a customer who says the word has handed over the layer. A customer
    # describing the browser asking whether to continue has not, and that is
    # also closer to how somebody without the vocabulary actually reports it.
    r"certificates?|tls|ssl|x509|cipher|handshake|"
    r"index|indexes|indices|joins?|seq scan|query plan|"
    r"inode|file descriptor|chmod|chown|umask|"
    r"metrics?|percentile|p9[59]|histogram|cardinality|"
    r"40[0-9]|41[0-9]|42[0-9]|50[0-9]"
    r")\b",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# Style, over the whole published surface
# --------------------------------------------------------------------------- #

# US spelling throughout. Caught "join behaviour" sitting in an evidence layer,
# which renders as a chip on the exercise page, so it was learner visible
# rather than an internal note. Only the endings that actually differ are
# listed: a general -our or -ise rule would fire on "our", "rise" and half the
# prose in the repository.
BRITISH = re.compile(
    r"\b(?:colour|behaviour|favour|honour|labour|neighbour|rumour"
    r"|normalis|recognis|organis|initialis|customis|optimis|specialis|apologis|analyse"
    r"|centre|metre|litre|defence|offence|licence|pretence"
    r"|catalogue|dialogue|analogue"
    r"|labelled|cancelled|travelling|modelling|signalling)\w*",
    re.IGNORECASE,
)

# Names fixed by a specification somebody else wrote. `aria-labelledby` is the
# attribute, and there is no US spelling of it to prefer.
SPELLED_BY_SPECIFICATION = re.compile(r"\baria-labelledby\b")

# Two files, each with a reason that is not "it was already there".
STYLE_EXEMPT = {
    "site/package-lock.json":
        "generated by npm, and it names packages written by other people",
    "tools/tests/test_content.py":
        "holds the pattern table these two rules are written from",
}


def style_sources() -> list[tuple[str, str]]:
    """Every tracked text file, because that is exactly what gets published.

    Read through the leak scan's decoder rather than a second one, so a file
    written in UTF-16 is checked here too instead of being skipped quietly.
    """
    out: list[tuple[str, str]] = []
    for name in tse.tracked_files():
        if name in STYLE_EXEMPT:
            continue
        text = tse.decode_for_scanning((ROOT / name).read_bytes())
        if text is not None:
            out.append((name, text))
    return out


STYLE_SOURCES = style_sources()


class Structure(unittest.TestCase):
    def test_exercises_exist(self):
        self.assertGreater(len(EXERCISES), 0)

    def test_required_files_present(self):
        for exercise in EXERCISES:
            with self.subTest(exercise.id):
                for name in ("meta.yaml", "ticket.md", "check.sh", "solution.md"):
                    self.assertTrue((exercise.path / name).is_file(),
                                    f"{exercise.id} is missing {name}")
                self.assertTrue((exercise.path / "hints").is_dir(),
                                f"{exercise.id} has no hints/")

    def test_setup_and_solution_states_exist(self):
        """Including "none" exercises: a written answer has a bad draft and a good one."""
        for exercise in EXERCISES:
            with self.subTest(exercise.id):
                for variant in ("setup", "solution"):
                    directory = exercise.path / variant
                    self.assertTrue(directory.is_dir(), f"{exercise.id}: no {variant}/")
                    self.assertTrue(any(directory.iterdir()),
                                    f"{exercise.id}: {variant}/ is empty")

    def test_setup_and_solution_provide_the_same_filenames(self):
        """Otherwise switching states leaves a stale file behind."""
        for exercise in EXERCISES:
            with self.subTest(exercise.id):
                setup = {p.name for p in (exercise.path / "setup").iterdir() if p.is_file()}
                solution = {p.name for p in (exercise.path / "solution").iterdir() if p.is_file()}
                self.assertEqual(setup, solution,
                                 f"{exercise.id}: setup/ and solution/ differ in filenames")

    def test_hints_are_numbered_from_one(self):
        for exercise in EXERCISES:
            hints = sorted((exercise.path / "hints").glob("*.md"))
            with self.subTest(exercise.id):
                self.assertGreaterEqual(len(hints), 1, f"{exercise.id} has no hints")
                names = [h.stem for h in hints]
                self.assertEqual(names, [str(n) for n in range(1, len(hints) + 1)],
                                 f"{exercise.id}: hints must be 1.md, 2.md, ...")

    def test_check_is_executable_and_uses_the_library(self):
        for exercise in EXERCISES:
            check = exercise.path / "check.sh"
            body = check.read_text()
            with self.subTest(exercise.id):
                self.assertTrue(check.stat().st_mode & 0o111,
                                f"{exercise.id}: check.sh is not executable")
                self.assertIn("assert.sh", body, f"{exercise.id}: check.sh must source assert.sh")
                self.assertRegex(body, re.compile(r"^finish\s*$", re.MULTILINE),
                                 f"{exercise.id}: check.sh must call finish")


class Metadata(unittest.TestCase):
    def test_required_fields_present_and_valid(self):
        for exercise in EXERCISES:
            meta = exercise.meta
            with self.subTest(exercise.id):
                for field in REQUIRED_META:
                    self.assertIn(field, meta, f"{exercise.id}: meta is missing {field}")
                    self.assertIsNotNone(meta[field], f"{exercise.id}: {field} is empty")
                self.assertIn(meta["tier"], VALID_TIERS)
                self.assertIn(meta["stack"], VALID_STACKS)
                self.assertIn(meta["difficulty"], range(1, 6))
                self.assertGreater(meta["minutes"], 0)

    def test_id_matches_directory(self):
        for exercise in EXERCISES:
            with self.subTest(exercise.id):
                self.assertEqual(exercise.meta["id"], exercise.id)
                self.assertEqual(exercise.meta["track"], exercise.path.parent.name)

    def test_stack_source_points_at_a_real_stack(self):
        """A borrowed stack that does not exist fails at provision time, not here."""
        for exercise in EXERCISES:
            if exercise.stack == "none":
                continue
            with self.subTest(exercise.id):
                self.assertTrue(
                    exercise.stack_dir().is_dir(),
                    f"{exercise.id}: stack source {exercise.stack_source!r} has no _stack",
                )

    def test_prerequisites_resolve(self):
        known = {e.id for e in EXERCISES}
        for exercise in EXERCISES:
            for prerequisite in exercise.meta.get("prerequisites") or []:
                with self.subTest(exercise.id):
                    self.assertIn(prerequisite, known,
                                  f"{exercise.id}: unknown prerequisite {prerequisite}")

    def test_no_placeholders_left(self):
        # questions.json is scaffolded with placeholders too, and it is not a
        # .md file, so it has to be named here or a whole template question set
        # could ship unwritten.
        for exercise in EXERCISES:
            paths = list(exercise.path.rglob("*.md")) + [exercise.path / "questions.json"]
            for path in paths:
                if not path.is_file():
                    continue
                with self.subTest(f"{exercise.id}:{path.name}"):
                    self.assertNotIn("TODO", path.read_text(),
                                     f"{path} still contains a template placeholder")


class Editorial(unittest.TestCase):
    def test_ticket_does_not_name_the_failing_layer(self):
        """The customer-facing half of a ticket must not give away the layer."""
        for exercise in EXERCISES:
            ticket = (exercise.path / "ticket.md").read_text()
            # Working notes are operator scaffolding, not the customer's words.
            customer_facing = ticket.split("**Working notes**")[0]
            found = SPOILER_TERMS.findall(customer_facing)
            with self.subTest(exercise.id):
                self.assertEqual(found, [], f"{exercise.id}: ticket leaks {sorted(set(found))}")

    def test_solution_has_every_required_section(self):
        for exercise in EXERCISES:
            body = (exercise.path / "solution.md").read_text()
            with self.subTest(exercise.id):
                for section in REQUIRED_SOLUTION_SECTIONS:
                    self.assertIn(section, body, f"{exercise.id}: solution.md needs {section}")

    def test_no_solution_still_ends_in_a_spoken_answer(self):
        """The spoken section was replaced by questions.json, not kept alongside.

        Required-section tests can only notice something missing, never
        something lingering, so removing it from REQUIRED_SOLUTION_SECTIONS
        left nothing watching. A revert quietly restored all fifteen once
        already and every test still passed.
        """
        for exercise in EXERCISES:
            body = (exercise.path / "solution.md").read_text()
            with self.subTest(exercise.id):
                self.assertNotIn(
                    "## Say it out loud", body,
                    f"{exercise.id}: solution.md still ends in a spoken answer",
                )

    def test_first_hint_names_no_command(self):
        """Hint 1 reframes the problem. It must not hand over a command."""
        for exercise in EXERCISES:
            first = exercise.path / "hints" / "1.md"
            with self.subTest(exercise.id):
                self.assertNotIn("```", first.read_text(),
                                 f"{exercise.id}: hint 1 contains a code block")

    # What escalates is how much of the work is done for the reader, not how
    # many commands appear. An audit first measured this by counting code
    # fences and concluded six exercises had drifted. Reading them showed the
    # opposite: hint 2 gives the commands that gather evidence and hint 3
    # interprets it and gives the fix, which is a real escalation and a better
    # one. The measurement was wrong, not the hints.
    #
    # `tse apply` and `tse check` are what a reader runs after changing
    # something, so they mark the point where a hint stops asking and starts
    # answering. Across all twenty-five exercises they appear in hint 3
    # fifteen times and in hint 2 never.
    APPLYING_THE_FIX = re.compile(r"\btse (?:apply|check)\b")

    def test_the_second_hint_does_not_hand_over_the_fix(self):
        """Hint 2 shows how to look. Hint 3 is where the answer lives."""
        for exercise in EXERCISES:
            second = exercise.path / "hints" / "2.md"
            if not second.is_file():
                continue
            with self.subTest(exercise.id):
                self.assertIsNone(
                    self.APPLYING_THE_FIX.search(second.read_text()),
                    f"{exercise.id}: hint 2 tells the reader to apply a change. "
                    f"Gathering evidence belongs in hint 2, the fix in hint 3.",
                )

    def test_a_later_hint_is_where_the_fix_actually_is(self):
        """Otherwise the rule above passes on a course with no answers in it."""
        answered = [
            exercise.id for exercise in EXERCISES
            if self.APPLYING_THE_FIX.search(
                (exercise.path / "hints" / "3.md").read_text())
        ]
        self.assertGreater(len(answered), len(EXERCISES) // 2,
                           "hint 3 has stopped telling anybody what to do")

    def test_no_em_dashes(self):
        for name, text in STYLE_SOURCES:
            # Report the line, not the file. assertNotIn prints the haystack,
            # and on a file the size of SECURITY.md that buries the finding in
            # the thing it was found in.
            hits = [i for i, line in enumerate(text.splitlines(), 1) if "—" in line]
            with self.subTest(name):
                self.assertEqual(
                    hits, [],
                    f"{name} contains an em dash on line(s) "
                    f"{', '.join(str(i) for i in hits)}",
                )

    def test_us_spelling(self):
        """Every word a reader sees, not only the one somebody happened to notice."""
        for name, text in STYLE_SOURCES:
            hits = []
            for i, line in enumerate(text.splitlines(), 1):
                found = BRITISH.search(SPELLED_BY_SPECIFICATION.sub("", line))
                if found:
                    hits.append(f"line {i}: {found.group(0)!r}")
            with self.subTest(name):
                self.assertEqual(hits, [], f"{name} uses British spelling, {'; '.join(hits)}")

    def test_the_style_sweep_reaches_past_the_exercises(self):
        """The scope is the point of this pair, so the scope is asserted.

        Both rules used to read labs/ and a couple of files at the root, which
        is the surface somebody thought of rather than the surface a reader
        sees. Two British spellings sat in site/ comments the whole time
        because nothing looked there.
        """
        covered = {name for name, _ in STYLE_SOURCES}
        for name in ("SECURITY.md", "CODE_OF_CONDUCT.md",
                     "site/src/content/docs/index.mdx",
                     "site/src/styles/custom.css",
                     "site/scripts/a11y.mjs",
                     ".github/workflows/verify.yml"):
            with self.subTest(name):
                self.assertIn(name, covered, f"{name} is not being checked")

    def test_every_style_exemption_still_exists_and_still_needs_it(self):
        """An exemption that stopped being needed is an unchecked file."""
        for name, reason in STYLE_EXEMPT.items():
            with self.subTest(name):
                self.assertTrue((ROOT / name).is_file(), f"{name} is exempt and gone")
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertTrue(
                    "—" in text or BRITISH.search(SPELLED_BY_SPECIFICATION.sub("", text)),
                    f"{name} no longer needs its exemption ({reason}); delete it",
                )

    def test_a_specification_spelling_is_not_mistaken_for_prose(self):
        """`aria-labelledby` is an attribute name and cannot be spelled the US way."""
        stripped = SPELLED_BY_SPECIFICATION.sub("", '<p aria-labelledby="x">')
        self.assertIsNone(BRITISH.search(stripped))
        self.assertIsNotNone(BRITISH.search("the labelled diagram"))

    # Present tense only. Saying a private repository *gets* 2,000 minutes is a
    # fact about GitHub and stays true. Saying *this* repository is private is
    # not, and several files said exactly that for a while after the flip.
    STILL_PRIVATE = re.compile(
        r"\b(?:this|the)\s+repositor(?:y|ies)\s+is\s+private\b"
        r"|\bwhile\s+(?:it|this|the\s+repository)\s+is\s+private\b"
        r"|\bthe\s+day\s+this\s+(?:goes|repository\s+goes)\s+public\b"
        r"|\bTHE\s+DAY\s+THIS\s+REPOSITORY\s+GOES\s+PUBLIC\b",
        re.IGNORECASE)

    # AUDIT.md is the record of how this repository got here, so it describes
    # the private period at length and correctly. It is the one file where the
    # past tense is the whole point.
    TENSE_EXEMPT = {"AUDIT.md"}

    def test_nothing_still_claims_this_repository_is_private(self):
        """It is public. A file that says otherwise is wrong, not merely stale."""
        for name, text in STYLE_SOURCES:
            if name in self.TENSE_EXEMPT:
                continue
            for index, line in enumerate(text.splitlines(), 1):
                if self.STILL_PRIVATE.search(line):
                    self.fail(
                        f"{name}:{index} describes this repository as private, "
                        f"or as not yet public. It went public on 2026-08-16. "
                        f"Say what was true then in the past tense."
                    )


STACKS = sorted(ROOT.glob("labs/*/_stack/compose.yaml"))


class Containment(unittest.TestCase):
    """Every service in every stack is confined, and says how.

    CONTRIBUTING told a contributor to copy `read_only`, `cap_drop`,
    `no-new-privileges` and the resource caps from an existing stack, and
    nothing checked that they had. The answer, when something finally looked,
    was that the only image in the course holding data was the one running with
    full capabilities, in both stacks that use it, while every Python service
    beside it was sealed.

    A service that genuinely cannot take a setting declares `x-containment`
    with the reason. Silence is not an option, which is the whole point:
    postgres turned out to take all of it once it starts as the postgres user
    instead of dropping to it, so no exception was needed after all.
    """

    def containment(self):
        for path in STACKS:
            name = str(path.relative_to(ROOT))
            for service, keys in tse.service_containment(path.read_text(), name).items():
                yield name, service, keys

    def test_every_service_is_confined(self):
        for name, service, keys in self.containment():
            with self.subTest(f"{name}:{service}"):
                if tse.CONTAINMENT_EXCEPTION in keys:
                    self.assertTrue(
                        len(keys[tse.CONTAINMENT_EXCEPTION]) > 20,
                        f"{name}: {service} claims an exception without a reason",
                    )
                    continue
                missing = [k for k in tse.CONTAINMENT_KEYS if k not in keys]
                self.assertEqual(
                    missing, [],
                    f"{name}: {service} declares no {', '.join(missing)}. Copy the "
                    f"posture from a service beside it, or add {tse.CONTAINMENT_EXCEPTION} "
                    f"with the reason it cannot.",
                )

    def test_the_confinement_is_the_strong_form(self):
        """Present is not enough. `cap_drop: [NET_RAW]` would pass a key check."""
        for name, service, keys in self.containment():
            if tse.CONTAINMENT_EXCEPTION in keys:
                continue
            with self.subTest(f"{name}:{service}"):
                self.assertEqual(keys.get("read_only"), "true",
                                 f"{name}: {service} is not read_only")
                self.assertIn("ALL", keys.get("cap_drop", ""),
                              f"{name}: {service} does not drop ALL capabilities")
                self.assertIn("no-new-privileges:true", keys.get("security_opt", ""),
                              f"{name}: {service} can still gain privileges")

    def test_every_stack_was_actually_read(self):
        """A scan that quietly found no services would pass everything above."""
        self.assertGreaterEqual(len(STACKS), 6, "stacks have gone missing")
        for path in STACKS:
            name = str(path.relative_to(ROOT))
            with self.subTest(name):
                self.assertGreater(
                    len(tse.service_containment(path.read_text(), name)), 0,
                    f"{name}: no services were read out of it",
                )

    def test_a_shared_posture_is_resolved_rather_than_missed(self):
        """observability defines its posture once and merges it into three services."""
        got = tse.service_containment(
            "x-service: &service\n"
            "  read_only: true\n"
            "  cap_drop:\n"
            "    - ALL\n"
            "\n"
            "services:\n"
            "  api:\n"
            "    <<: *service\n"
            "    command: [\"python\", \"/app/api.py\"]\n",
            "probe",
        )
        self.assertEqual(got["api"]["read_only"], "true")
        self.assertEqual(got["api"]["cap_drop"], "ALL")

    def test_a_service_that_sets_nothing_is_seen_as_setting_nothing(self):
        got = tse.service_containment(
            "services:\n  postgres:\n    image: postgres:16-alpine\n", "probe")
        self.assertEqual(list(got), ["postgres"])
        self.assertNotIn("read_only", got["postgres"])


class BaseImages(unittest.TestCase):
    """One base per language, and the Codespace pre-pulls all of them.

    Three stacks were on `python:3.12-alpine` and two on
    `python:3.12-alpine3.24`. Both resolve to Alpine 3.24.1 today, which is
    exactly why nothing noticed: they stop being the same image the day Alpine
    3.25 ships, and then three stacks move operating system and two do not.

    The Codespace pre-pull listed only the floating tag, so networking and
    observability still waited on a download the pre-pull exists to avoid.
    """

    def bases(self) -> dict[str, list[str]]:
        """Every image a stack builds FROM or runs directly, by file."""
        found: dict[str, list[str]] = {}
        for path in sorted(ROOT.glob("labs/*/_stack/Dockerfile")):
            found[str(path.relative_to(ROOT))] = re.findall(
                r"(?m)^FROM\s+(\S+)", path.read_text())
        for path in STACKS:
            found[str(path.relative_to(ROOT))] = re.findall(
                r"(?m)^\s+image:\s*(\S+)", path.read_text())
        return found

    def test_every_stack_builds_on_the_same_python(self):
        used = {image for images in self.bases().values() for image in images
                if image.startswith("python:")}
        self.assertEqual(
            len(used), 1,
            f"the course builds on more than one Python base: {sorted(used)}",
        )

    def test_every_base_names_its_operating_system(self):
        """A floating tag moves under the course without anything saying so."""
        for name, images in self.bases().items():
            for image in images:
                if not image.startswith("python:"):
                    continue
                with self.subTest(f"{name}:{image}"):
                    self.assertRegex(
                        image, r"alpine\d+\.\d+$",
                        f"{name}: {image} does not pin the Alpine release",
                    )

    def test_the_codespace_pre_pulls_every_base(self):
        script = (ROOT / ".devcontainer" / "post-create.sh").read_text()
        pulled = set(re.findall(r"docker pull -q (\S+)", script))
        needed = {image for images in self.bases().values() for image in images}
        missing = sorted(needed - pulled)
        self.assertEqual(
            missing, [],
            f"post-create.sh does not pre-pull {missing}, so a Codespace stops "
            f"to download on first use",
        )

    def test_nothing_is_pre_pulled_that_no_stack_uses(self):
        script = (ROOT / ".devcontainer" / "post-create.sh").read_text()
        pulled = set(re.findall(r"docker pull -q (\S+)", script))
        needed = {image for images in self.bases().values() for image in images}
        self.assertEqual(sorted(pulled - needed), [],
                         "post-create.sh pulls an image no stack builds on")


NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "twenty-five": 25, "fifty": 50, "one hundred": 100,
}


class ReadmeCounts(unittest.TestCase):
    """The README's table is a claim about the repository, so it is checked.

    Nothing kept it honest. It happens to be right, and it would have stayed
    right-looking through the next exercise added, because a table nobody reads
    against reality is just a paragraph.

    Catching the README and the site calling one track two different names was
    the first thing this found: the table said "Linux and CLI foundations" and
    every page on the site said "Linux and CLI".
    """

    def rows(self) -> list[tuple[str, int]]:
        text = (ROOT / "README.md").read_text()
        block = re.search(r"(?ms)^\| Track \| Exercises \|.*?(?=\n\n)", text)
        self.assertIsNotNone(block, "the README has no track table any more")
        out = []
        for line in block.group(0).splitlines()[2:]:
            cells = [c.strip() for c in line.strip("|").split("|")]
            out.append((cells[0], int(cells[1])))
        return out

    def site_labels(self) -> dict[str, str]:
        """TRACK_LABELS out of the site, so the two cannot drift apart."""
        text = (ROOT / "site" / "src" / "lib" / "labs.ts").read_text()
        block = re.search(r"TRACK_LABELS[^{]*\{(.*?)\}", text, re.S)
        self.assertIsNotNone(block, "TRACK_LABELS has moved or been renamed")
        return dict(re.findall(r'(\w+):\s*"([^"]+)"', block.group(1)))

    def test_every_track_has_a_row_with_the_right_count(self):
        labels = self.site_labels()
        real = {}
        for exercise in EXERCISES:
            real[labels.get(exercise.track, exercise.track)] = \
                real.get(labels.get(exercise.track, exercise.track), 0) + 1
        self.assertEqual(dict(self.rows()), real)

    def test_the_table_names_tracks_the_way_the_site_does(self):
        """A reader moving between the README and the site sees one name."""
        self.assertEqual(
            sorted(label for label, _ in self.rows()),
            sorted(self.site_labels().values()),
        )

    def test_the_sentence_under_the_table_counts_the_same_things(self):
        text = (ROOT / "README.md").read_text()
        said = re.search(r"(?i)(\w+[\w-]*) exercises across all (\w+) tracks", text)
        self.assertIsNotNone(said, "the sentence under the table has been reworded")
        self.assertEqual(NUMBER_WORDS.get(said.group(1).lower()), len(EXERCISES),
                         f"the README says {said.group(1)} exercises")
        self.assertEqual(NUMBER_WORDS.get(said.group(2).lower()), len(self.rows()),
                         f"the README says {said.group(2)} tracks")

    def test_the_table_was_actually_found(self):
        """Every assertion above passes trivially against an empty table."""
        self.assertGreaterEqual(len(self.rows()), 9)


# Anything shaped like an HTML tag. Deliberately broad, including the
# `<placeholder>` a contributor might write in prose, because markdown treats
# that as an unknown tag and renders nothing where the word should be. Telling
# somebody that up front is better than the word silently vanishing.
HTML_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>")


def prose_only(text: str) -> str:
    """The parts of a markdown file that are not code."""
    text = re.sub(r"(?ms)^```.*?^```", "", text)
    return re.sub(r"`[^`\n]*`", "", text)


class RenderedMarkdown(unittest.TestCase):
    """Nothing contributed reaches the page as live HTML.

    `md()` in site/src/lib/labs.ts renders with marked and no sanitizer, and
    the page inserts the result with `set:html`. Every ticket, hint, solution
    and reference document goes through that path, so a tag written into one is
    a tag on the published site.

    Adding a sanitizer would mean adding a dependency to a project whose lack
    of them is a stated design property, and it would strip the markup quietly
    rather than telling the author. Refusing raw HTML at the source closes the
    same hole one step earlier and gives a contributor an error they can act on.
    """

    def sources(self):
        return sorted(ROOT.glob("labs/*/*/**/*.md")) + sorted(ROOT.glob("reference/*.md"))

    def test_no_contributed_markdown_carries_raw_html(self):
        for path in self.sources():
            found = HTML_TAG.findall(prose_only(path.read_text()))
            with self.subTest(str(path.relative_to(ROOT))):
                self.assertEqual(
                    found, [],
                    f"{path.relative_to(ROOT)} contains raw HTML: {found}. "
                    f"It is rendered with set:html and reaches the page as markup.",
                )

    def test_there_is_something_to_check(self):
        self.assertGreater(len(self.sources()), 100)

    def test_the_detector_tells_markup_from_code(self):
        """A tag inside a fence is an example, not markup."""
        self.assertEqual(HTML_TAG.findall(prose_only("```\n<script>x</script>\n```\n")), [])
        self.assertEqual(HTML_TAG.findall(prose_only("use `<div>` here")), [])
        self.assertIn("<script>", HTML_TAG.findall(prose_only("a <script>alert(1)</script> b")))
        self.assertIn("<img src=x onerror=alert(1)>",
                      HTML_TAG.findall(prose_only("<img src=x onerror=alert(1)>")))


class MachineLocalFiles(unittest.TestCase):
    """Nothing personal to one machine can be committed by accident.

    `.claude/settings.local.json` was ignored only by the author's *global*
    gitignore, which is not a property of this repository. Anybody else cloning
    it would have seen their own local settings as untracked and one `git add
    -A` away from published.
    """

    LOCAL_ONLY = (
        ".claude/settings.local.json",
        ".vscode/settings.json",
        ".idea/",
        ".tse-state.json",
    )

    def test_this_repository_ignores_them_itself(self):
        # By line rather than assertIn, which prints the whole .gitignore to
        # tell you one line is missing from it.
        lines = {line.strip() for line in (ROOT / ".gitignore").read_text().splitlines()}
        missing = [name for name in self.LOCAL_ONLY if name not in lines]
        self.assertEqual(
            missing, [],
            f".gitignore does not list {missing}, so they are only ignored if "
            f"whoever cloned this happens to have them in a global gitignore",
        )

    def test_none_of_them_are_tracked(self):
        tracked = set(tse.tracked_files())
        for name in self.LOCAL_ONLY:
            with self.subTest(name):
                self.assertFalse(
                    any(path == name or path.startswith(name) for path in tracked),
                    f"{name} is committed",
                )


class PythonFloor(unittest.TestCase):
    """The oldest Python this runs on is stated in one place and checked.

    The README said 3.11 or newer and nothing had ever checked. It was wrong in
    the direction that costs a reader something: every suite and all forty-two
    smoke assertions pass on 3.9.6, which is the interpreter macOS already has,
    so the requirement was sending people to install a Python they did not need.
    """

    def test_the_readme_agrees_with_the_cli(self):
        said = re.search(r"Python (\d+)\.(\d+) or newer", (ROOT / "README.md").read_text())
        self.assertIsNotNone(said, "the README no longer states a Python version")
        self.assertEqual((int(said.group(1)), int(said.group(2))), tse.MINIMUM_PYTHON)

    def test_the_floor_is_enforced_rather_than_documented(self):
        source = (ROOT / "tools" / "tse").read_text()
        self.assertIn("if sys.version_info < MINIMUM_PYTHON:", source)

    def test_preflight_runs_the_cli_on_a_stripped_environment(self):
        """The floor only stays true because something keeps proving it."""
        script = (ROOT / "tools" / "tests" / "preflight.sh").read_text()
        self.assertIn("env -i", script)
        self.assertIn("LANG=C", script)


class Devcontainer(unittest.TestCase):
    """The Codespace definition, which nothing builds and nothing else checks.

    Building it in CI needs Docker in Docker on a runner and is recorded in
    AUDIT.md as accepted rather than done. These are the parts that can be
    checked without building anything, and both were wrong: two features were
    pinned to "latest", so two Codespaces a month apart are two different
    machines, and `tse doctor || true` meant an environment that could not run
    a single exercise still printed "Prove It is ready."
    """

    def definition(self) -> dict:
        text = (ROOT / ".devcontainer" / "devcontainer.json").read_text()
        # devcontainer.json permits comments. None are in this one, and if one
        # is added this will say so rather than guessing.
        self.assertNotIn("//", text, "devcontainer.json now has comments to strip")
        return json.loads(text)

    def test_no_feature_floats(self):
        for feature, options in self.definition()["features"].items():
            for key, value in options.items():
                if not isinstance(value, str):
                    continue
                with self.subTest(f"{feature}:{key}"):
                    self.assertNotEqual(
                        value, "latest",
                        f"{feature} pins {key} to latest, so two Codespaces "
                        f"built a month apart are two different machines",
                    )

    def test_the_post_create_script_reports_a_failed_check(self):
        """A container that cannot run an exercise must not say it is ready."""
        script = (ROOT / ".devcontainer" / "post-create.sh").read_text()
        # By line, so the failure names the line rather than reprinting the
        # script it was found in.
        swallowed = [i for i, line in enumerate(script.splitlines(), 1)
                     if "tse doctor" in line and "|| true" in line]
        self.assertEqual(
            swallowed, [],
            f"post-create.sh line {swallowed} swallows the environment check",
        )
        self.assertIn("if tools/tse doctor;", script)

    def test_the_banner_is_conditional(self):
        # Anchored on the heredoc rather than on the banner's words, which also
        # appear in the comment explaining why this check exists. That is what
        # the first version of this test matched, and it failed for it.
        script = (ROOT / ".devcontainer" / "post-create.sh").read_text()
        self.assertIn("<<'BANNER'", script)
        guard = script.find('if [ "$ready" -eq 1 ]')
        self.assertNotEqual(guard, -1, "the ready banner prints unconditionally")
        self.assertLess(guard, script.index("<<'BANNER'"),
                        "the guard comes after the banner it is meant to guard")


class DownloadedBinaries(unittest.TestCase):
    """Anything fetched from the network and then run must be checksummed first.

    Every GitHub action in this repository is pinned to a commit SHA. The kind
    binary was not. Two places curled it and handed it straight to `sudo
    install`, so whatever that URL served on the day ran as root, both on CI
    runners and in every learner's Codespace. The fix is a checksum committed
    to git, which is what makes it a control: a checksum fetched next to the
    thing it checks only proves the two arrived together.
    """

    # A download that names the file it lands in. A download piped into
    # something else is a different shape and is deliberately not matched here.
    DOWNLOAD = re.compile(
        r"\b(?:curl|wget)\b[^\n]*?\s(?:-[A-Za-z]*o|--output|--output-document)[= ]\s*(\S+)")
    CHECKED = re.compile(r"\bsha256sum\s+-c\b|\bshasum\s+-a\s*256\s+-c\b")
    # Handing the file to something that will run it, now or later.
    RUNS_IT = re.compile(r"\b(?:install|chmod\s+\+x|exec)\b")

    def scripts(self) -> list[tuple[str, str]]:
        out = []
        for name in tse.tracked_files():
            if not name.endswith((".sh", ".bash", ".yml", ".yaml")):
                continue
            text = tse.decode_for_scanning((ROOT / name).read_bytes())
            if text is not None:
                out.append((name, text))
        return out

    def test_a_downloaded_file_is_verified_before_it_is_installed(self):
        """Walk forward from each download. A checksum must come before the install."""
        for name, text in self.scripts():
            lines = text.splitlines()
            for index, line in enumerate(lines):
                match = self.DOWNLOAD.search(line)
                if not match:
                    continue
                target = match.group(1).strip("\"'")
                # Downloading is not the problem. Running what was downloaded
                # without having checked it is, so a fetch that nothing ever
                # installs or marks executable is left alone. Several exercises
                # curl into /dev/null on purpose.
                with self.subTest(f"{name}:{index + 1}"):
                    for offset, later in enumerate(lines[index + 1:], index + 2):
                        if self.CHECKED.search(later) and target in later:
                            break
                        if self.RUNS_IT.search(later) and target in later:
                            self.fail(
                                f"{name}:{offset} installs {target}, downloaded at "
                                f"line {index + 1}, with nothing having verified it. "
                                f"Pin the published sha256 and check it first."
                            )

    PINNED_DIGEST = re.compile(r"\b(?:KIND_SHA256=|echo\s+\")([0-9a-fA-F]+)\s")

    def test_every_pinned_digest_is_a_full_sha256(self):
        """A truncated digest still reads as a pin and checks almost nothing."""
        for name, text in self.scripts():
            for index, line in enumerate(text.splitlines(), 1):
                if "sha256" not in line.lower() and "SHA256" not in line:
                    continue
                match = self.PINNED_DIGEST.search(line)
                if not match:
                    continue
                with self.subTest(f"{name}:{index}"):
                    self.assertEqual(
                        len(match.group(1)), 64,
                        f"{name}:{index} pins a {len(match.group(1))} character "
                        f"digest, and a sha256 is 64",
                    )


class ClusterHelpers(unittest.TestCase):
    """Guards on the Kubernetes preload path.

    The platform string used to be inferred from `uname -m`, which meant one
    branch of a mapping table only ever ran on hardware the author did not
    have. It is now asked of Docker directly, and these assert the answer is
    well formed rather than assuming it.
    """

    def test_node_platform_is_well_formed_or_absent(self):
        platform = tse.node_platform()
        if platform is None:
            self.skipTest("Docker is not available on this machine")
        self.assertRegex(platform, r"^linux/[a-z0-9]+$")

    def test_node_platform_matches_the_running_daemon(self):
        # Through `run_tool` rather than `subprocess.run`, for the reason
        # `run_tool` exists: this test asked for Docker directly and crashed
        # with FileNotFoundError on a runner that has no `docker` binary, which
        # is not the same as a machine where the daemon is stopped. It reported
        # an error where it meant to report a skip.
        probe = tse.run_tool(["docker", "version", "--format", "{{.Server.Arch}}"])
        if probe.returncode != 0 or not probe.stdout.strip():
            self.skipTest("Docker is not available on this machine")
        self.assertEqual(tse.node_platform(), f"linux/{probe.stdout.strip()}")

    def test_the_docker_helpers_survive_a_machine_with_no_docker(self):
        """Every one of these promised this and none of them delivered it.

        `image_in_node` is called from `cluster status` and its docstring says
        it must not blow up. `node_platform` says it returns None when it
        cannot tell. Both raised on a machine without the binary, because both
        checked a return code that a raised call never produced.
        """
        import shutil

        original = shutil.which("docker")
        with unittest.mock.patch.object(
            tse.subprocess, "run", side_effect=FileNotFoundError(2, "No such file")
        ):
            self.assertIsNone(tse.node_platform())
            self.assertIs(tse.image_in_node(tse.KIND_IMAGES[0]), False)
            self.assertIs(tse.cluster_exists(), False)
        # And the machine this ran on is unchanged by the test.
        self.assertEqual(shutil.which("docker"), original)

    def test_lab_images_are_tagged(self):
        """image_in_node splits on the last colon, so an untagged entry breaks it."""
        for image in tse.KIND_IMAGES:
            with self.subTest(image):
                repository, separator, tag = image.rpartition(":")
                self.assertTrue(separator, f"{image} has no tag")
                self.assertTrue(repository and tag)

    def test_image_in_node_is_safe_without_a_cluster(self):
        """It is called from `cluster status`, which must not blow up."""
        self.assertIsInstance(tse.image_in_node(tse.KIND_IMAGES[0]), bool)


class GeneratedFiles(unittest.TestCase):
    def test_every_managed_filename_is_gitignored(self):
        """Files tse writes into a shared _stack must never be committable.

        Committing one would freeze a single exercise's broken state into the
        repository and quietly change what every other exercise starts from.
        """
        ignored = (ROOT / ".gitignore").read_text()
        tracks = {exercise.track for exercise in EXERCISES}
        for track in sorted(tracks):
            for name in sorted(tse.managed_files(track)):
                with self.subTest(f"{track}/{name}"):
                    self.assertIn(f"labs/*/_stack/{name}", ignored,
                                  f".gitignore is missing labs/*/_stack/{name}")

    def test_stack_directories_hold_no_generated_files(self):
        for track in sorted({e.track for e in EXERCISES}):
            stack = ROOT / "labs" / track / "_stack"
            for name in sorted(tse.managed_files(track)):
                with self.subTest(f"{track}/{name}"):
                    self.assertFalse(
                        (stack / name).exists(),
                        f"{stack / name} is present. Run `tse stop` before committing.",
                    )


class ContributedFiles(unittest.TestCase):
    """What an exercise is allowed to hand to Docker and to kubectl.

    An audit proved this was unbounded: a contributed compose.override.yaml,
    which is a filename three real exercises already ship, produced a merged
    configuration carrying `privileged: true` and a bind mount of `/`. CI
    provisions every exercise on a branch, so that ran before any human read it.

    These tests exist for the same reason the planted-secret tests below do. A
    guard nobody has watched refuse anything is not a guard, and the guard here
    also has to keep accepting fifty real files, so both halves are asserted.
    """

    def refusal(self, checker, text, source):
        """The message a checker exits with, or None if it accepted the text."""
        try:
            checker(text, source)
        except SystemExit as stop:
            return str(stop.code)
        return None

    def test_the_allowlist_matches_gitignore(self):
        """The list of contributable names and the list of generated names are
        the same list, so a file the repository tracks can never be on it.

        That equality is what protects compose.yaml, the Dockerfiles and the
        service source without naming any of them: they are committed, so they
        are not generated, so they are not contributable.
        """
        ignored = {
            line.strip().removeprefix("labs/*/_stack/")
            for line in (ROOT / ".gitignore").read_text().splitlines()
            if line.strip().startswith("labs/*/_stack/")
        }
        self.assertEqual(tse.CONTRIBUTABLE_FILENAMES, ignored)

    def test_every_real_variant_is_still_accepted(self):
        """The guard must not have made the course itself unrunnable."""
        for exercise in EXERCISES:
            for variant in ("setup", "solution"):
                directory = exercise.path / variant
                if not directory.is_dir():
                    continue
                with self.subTest(f"{exercise.id}/{variant}"):
                    try:
                        tse.check_contributed_files(directory, stack=exercise.stack)
                    except SystemExit as stop:
                        self.fail(f"{exercise.id}/{variant} was refused: {stop.code}")

    def test_no_permitted_override_key_is_unused(self):
        """Every key the allowlist grants is one a real exercise needs.

        A permission kept for a use that never arrived is a permission nobody
        is thinking about, which is how the list widens back to where it started.
        """
        used = set()
        for exercise in EXERCISES:
            for variant in ("setup", "solution"):
                override = exercise.path / variant / "compose.override.yaml"
                if not override.is_file():
                    continue
                for line in override.read_text().splitlines():
                    stripped = line.split("#", 1)[0].rstrip()
                    if len(stripped) - len(stripped.lstrip(" ")) == 4:
                        used.add(stripped.strip().split(":", 1)[0].strip())
        self.assertEqual(
            tse.COMPOSE_OVERRIDE_KEYS, used - {""},
            "COMPOSE_OVERRIDE_KEYS and the keys the exercises use have diverged",
        )

    # One sample per family, planted the way a contributor would write it. The
    # first is the exact payload the audit rendered.
    HOSTILE_OVERRIDES = {
        "privileged": "services:\n  app:\n    privileged: true\n",
        "a host bind mount": "services:\n  app:\n    volumes:\n      - /:/host\n",
        "the docker socket":
            "services:\n  app:\n    volumes:\n      - /var/run/docker.sock:/s\n",
        "capabilities added back": "services:\n  app:\n    cap_add:\n      - SYS_ADMIN\n",
        "hardening switched off": "services:\n  app:\n    security_opt: []\n",
        "host networking": "services:\n  app:\n    network_mode: host\n",
        "a replaced image": "services:\n  app:\n    image: attacker/evil:latest\n",
        "a build directive": "services:\n  app:\n    build: /\n",
        "a replaced entrypoint": "services:\n  app:\n    entrypoint: /bin/sh\n",
        "an added device": "services:\n  app:\n    devices:\n      - /dev/kmsg\n",
        # Flow style on one line. An earlier version of the scan read only the
        # first word of a line, so this passed while saying the same thing as
        # the first case above.
        "flow style": "services: {app: {privileged: true}}\n",
        "an unexpected tag": "services:\n  app:\n    environment: !!python/object x\n",
        "tab indentation": "services:\n\tapp:\n\t\tprivileged: true\n",
        "a top level key beside services": "volumes:\n  evil:\n    driver: local\n",
        "no services at all": "# nothing here\n",
    }

    def test_every_hostile_override_is_refused(self):
        for label, text in self.HOSTILE_OVERRIDES.items():
            with self.subTest(label):
                self.assertIsNotNone(
                    self.refusal(tse.check_compose_override, text, "probe.yaml"),
                    f"an override that sets {label} was accepted",
                )

    HOSTILE_MANIFESTS = {
        "a host path volume":
            "kind: Deployment\nspec:\n  volumes:\n  - hostPath:\n      path: /\n",
        "host networking": "kind: Deployment\nspec:\n  hostNetwork: true\n",
        "a privileged container":
            "kind: Deployment\nspec:\n  securityContext:\n    privileged: true\n",
        "privilege escalation":
            "kind: Deployment\nspec:\n  securityContext:\n"
            "    allowPrivilegeEscalation: true\n",
        "a cluster role binding": "kind: ClusterRoleBinding\nmetadata:\n  name: x\n",
        "pinning a node": "kind: Deployment\nspec:\n  nodeName: control-plane\n",
        "no kind at all": "just: some\nyaml: here\n",
    }

    def test_every_hostile_manifest_is_refused(self):
        for label, text in self.HOSTILE_MANIFESTS.items():
            with self.subTest(label):
                self.assertIsNotNone(
                    self.refusal(tse.check_kubernetes_manifest, text, "probe.yaml"),
                    f"a manifest with {label} was accepted",
                )

    def test_a_stack_source_that_is_not_a_track_is_refused(self):
        """stack_source is joined into a path, so it cannot be taken on trust."""
        for bad in ("../../../../tmp/escape", "/etc", "nosuchtrack", ".."):
            with self.subTest(bad):
                exercise = tse.Exercise(
                    id="docker/probe",
                    path=ROOT / "labs" / "docker",
                    meta={"track": "docker", "stack_source": bad},
                )
                with self.assertRaises(SystemExit):
                    exercise.stack_dir()


class Resolution(unittest.TestCase):
    """How a learner refers to an exercise. Typing the full slug is not it."""

    def test_full_id_resolves(self):
        target = EXERCISES[0]
        self.assertEqual(tse.resolve(target.id).id, target.id)

    def test_numeric_prefix_resolves(self):
        self.assertEqual(tse.resolve("docker/01").id,
                         "docker/01-service-unavailable-after-deploy")

    def test_trailing_slash_is_tolerated(self):
        self.assertEqual(tse.resolve("docker/01/").id,
                         "docker/01-service-unavailable-after-deploy")

    def test_unique_substring_resolves(self):
        self.assertEqual(tse.resolve("credential-rotation").id,
                         "docker/03-data-access-lost-after-credential-rotation")

    def test_ambiguous_prefix_exits(self):
        with self.assertRaises(SystemExit):
            tse.resolve("docker/0")

    def test_unknown_reference_exits(self):
        with self.assertRaises(SystemExit):
            tse.resolve("nonexistent/99")


def evidence_rows(solution: str) -> list[list[str]]:
    """The rows of the "What the evidence proved" table.

    Load bearing twice: it is the quality signal that an exercise actually
    reasons about evidence, and it is the source the site's drills are
    generated from.
    """
    rows = []
    inside = False
    for line in solution.splitlines():
        if line.startswith("## What the evidence proved"):
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside and line.startswith("|") and not re.match(r"^\|[\s|:-]+\|$", line):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0].lower() not in {"command", "query", "evidence"}:
                rows.append(cells)
    return rows


class NotFiller(unittest.TestCase):
    """Guards against the failure mode of scale.

    At a hundred exercises the danger is not effort, it is variations on a
    theme with the names changed. Each check here is something a filler
    exercise does and a real one does not, so quality is a failing build
    rather than a matter of vigilance.
    """

    def _assert_unique(self, values: dict[str, str], label: str):
        seen: dict[str, str] = {}
        for exercise_id, value in values.items():
            normalized = " ".join((value or "").split()).lower()
            if not normalized:
                continue
            if normalized in seen:
                self.fail(f"{label} is duplicated between {seen[normalized]} and {exercise_id}")
            seen[normalized] = exercise_id

    def test_proof_questions_are_unique(self):
        self._assert_unique(
            {e.id: e.meta.get("proof_question", "") for e in EXERCISES}, "proof_question"
        )

    def test_teaches_are_unique(self):
        """Two exercises teaching the same distinction means one is redundant."""
        self._assert_unique({e.id: e.meta.get("teaches", "") for e in EXERCISES}, "teaches")

    def test_first_hints_are_unique(self):
        """Copy-pasting hint 1 is how a filler run starts."""
        self._assert_unique(
            {e.id: (e.path / "hints" / "1.md").read_text() for e in EXERCISES}, "hints/1.md"
        )

    def test_solutions_are_not_stubs(self):
        for exercise in EXERCISES:
            body = (exercise.path / "solution.md").read_text()
            with self.subTest(exercise.id):
                self.assertGreaterEqual(
                    len(body.splitlines()), 40,
                    f"{exercise.id}: solution.md is too short to be a real writeup",
                )

    def test_solutions_show_their_evidence(self):
        for exercise in EXERCISES:
            rows = evidence_rows((exercise.path / "solution.md").read_text())
            with self.subTest(exercise.id):
                self.assertGreaterEqual(
                    len(rows), 2,
                    f"{exercise.id}: needs an evidence table with at least two rows",
                )

    def test_setup_states_are_not_duplicated(self):
        """Two exercises breaking the system identically are one exercise."""
        seen: dict[str, str] = {}
        for exercise in EXERCISES:
            directory = exercise.path / "setup"
            if not directory.is_dir():
                continue
            fingerprint = repr(sorted(
                (item.name, item.read_bytes()) for item in directory.iterdir() if item.is_file()
            ))
            with self.subTest(exercise.id):
                self.assertNotIn(
                    fingerprint, seen,
                    f"{exercise.id} has the same broken state as {seen.get(fingerprint)}",
                )
            seen[fingerprint] = exercise.id


class Questions(unittest.TestCase):
    """The multiple choice set that replaced the spoken answer.

    Filler is as easy to write in a question as in an exercise, and a bad
    question is worse than none: it teaches the learner to pattern match on
    option length or on the one answer that sounds most cautious.
    """

    def test_every_exercise_has_a_question_set(self):
        for exercise in EXERCISES:
            with self.subTest(exercise.id):
                self.assertTrue(
                    (exercise.path / "questions.json").is_file(),
                    f"{exercise.id}: questions.json is missing",
                )
                self.assertEqual(
                    len(exercise.questions()), QUESTIONS_PER_EXERCISE,
                    f"{exercise.id}: expected {QUESTIONS_PER_EXERCISE} questions",
                )

    def test_each_question_has_one_answer_among_four(self):
        for exercise in EXERCISES:
            for number, question in enumerate(exercise.questions(), start=1):
                options = question.get("options", [])
                with self.subTest(f"{exercise.id} q{number}"):
                    self.assertEqual(
                        len(options), OPTIONS_PER_QUESTION,
                        f"{exercise.id} q{number}: expected {OPTIONS_PER_QUESTION} options",
                    )
                    self.assertEqual(
                        sum(1 for o in options if o.get("correct")), 1,
                        f"{exercise.id} q{number}: exactly one option must be correct",
                    )

    def test_every_option_explains_itself(self):
        """Including the correct one. "Correct" on its own teaches nothing."""
        for exercise in EXERCISES:
            for number, question in enumerate(exercise.questions(), start=1):
                options = question.get("options", [])
                with self.subTest(f"{exercise.id} q{number}"):
                    for index, option in enumerate(options, start=1):
                        self.assertTrue(
                            (option.get("explanation") or "").strip(),
                            f"{exercise.id} q{number} option {index}: no explanation",
                        )
                    texts = [(o.get("text") or "").strip().lower() for o in options]
                    self.assertEqual(len(set(texts)), len(texts),
                                     f"{exercise.id} q{number}: duplicated option text")
                    reasons = [(o.get("explanation") or "").strip().lower() for o in options]
                    self.assertEqual(len(set(reasons)), len(reasons),
                                     f"{exercise.id} q{number}: duplicated explanation")

    def test_no_lazy_options(self):
        for exercise in EXERCISES:
            for number, question in enumerate(exercise.questions(), start=1):
                for option in question.get("options", []):
                    with self.subTest(f"{exercise.id} q{number}"):
                        self.assertIsNone(
                            LAZY_OPTIONS.search(option.get("text", "")),
                            f"{exercise.id} q{number}: uses an 'of the above' option",
                        )

    def test_question_text_is_unique_across_the_course(self):
        seen: dict[str, str] = {}
        for exercise in EXERCISES:
            for question in exercise.questions():
                normalized = " ".join(question.get("question", "").split()).lower()
                with self.subTest(exercise.id):
                    self.assertNotIn(
                        normalized, seen,
                        f"{exercise.id} repeats a question from {seen.get(normalized)}",
                    )
                seen[normalized] = exercise.id

    def test_no_question_gives_itself_away(self):
        for exercise in EXERCISES:
            for number, question in enumerate(exercise.questions(), start=1):
                answer = next(
                    (o for o in question.get("options", []) if o.get("correct")), None
                )
                if answer is None:
                    continue
                shared = giveaway_overlap(question.get("question", ""), answer.get("text", ""))
                with self.subTest(f"{exercise.id} q{number}"):
                    self.assertIsNone(
                        shared,
                        f"{exercise.id} q{number}: the answer echoes the question ({shared!r})",
                    )

    def test_the_answer_is_not_always_in_the_same_place(self):
        """A drift toward one slot is the oldest tell in written exams."""
        positions: list[int] = []
        for exercise in EXERCISES:
            for question in exercise.questions():
                options = question.get("options", [])
                for index, option in enumerate(options):
                    if option.get("correct"):
                        positions.append(index)

        if not positions:
            self.skipTest("no questions authored yet")

        cap = max(2, round(0.45 * len(positions)))
        for slot in range(OPTIONS_PER_QUESTION):
            count = positions.count(slot)
            self.assertLessEqual(
                count, cap,
                f"the answer sits in slot {slot + 1} for {count} of {len(positions)} "
                f"questions, which is a pattern a learner can exploit",
            )


class Transcripts(unittest.TestCase):
    """Recorded output is committed and published, so it is held to that bar.

    Nothing here should be able to tell a reader anything about the machine
    that produced the recording. The recorder enforces this at write time; this
    enforces it on every build, including for a transcript edited by hand.
    """

    # Imported rather than restated. This list used to live here as well as in
    # tools/tse, and the two drifted: the copy here matched only three octets of
    # a 10.x address, so it fired on the semver in package-lock.json and would
    # have captured half of a real address. One definition, one behavior.
    PRIVATE = tse.TRANSCRIPT_LEAK_PATTERNS

    def transcripts(self):
        for exercise in EXERCISES:
            path = exercise.path / "transcript.json"
            if path.is_file():
                yield exercise, json.loads(path.read_text())

    def test_no_transcript_carries_anything_from_a_real_machine(self):
        for exercise, transcript in self.transcripts():
            for entry in transcript.get("entries", []):
                for pattern, description in self.PRIVATE:
                    found = pattern.search(entry.get("output", ""))
                    with self.subTest(f"{exercise.id}:{entry['command'][:40]}"):
                        self.assertIsNone(
                            found,
                            f"{exercise.id} transcript contains {description}: "
                            f"{found.group(0) if found else ''!r}. Re-record it.",
                        )

    def test_stored_output_carries_no_privacy_rule_matches(self):
        """Applying the privacy rules to a transcript must change nothing.

        If it does, the file was written before a rule existed and is still
        carrying whatever that rule was added to remove. Only the privacy rules
        are checked: container ids, ages and column alignment are deliberately
        kept as captured, because they keep the output readable and say nothing
        about the machine that produced it.
        """
        for exercise, transcript in self.transcripts():
            for entry in transcript.get("entries", []):
                output = entry.get("output", "")
                with self.subTest(f"{exercise.id}:{entry['command'][:40]}"):
                    self.assertEqual(tse.scrub(output, privacy_only=True), output,
                                     f"{exercise.id}: transcript needs re-recording")

    def test_no_forbidden_command_is_recorded(self):
        """The terminal replays investigation, never grading or the answer."""
        forbidden = re.compile(r"\btse\s+(answer|hint|check|quiz)\b")
        for exercise, transcript in self.transcripts():
            for entry in transcript.get("entries", []):
                with self.subTest(exercise.id):
                    self.assertIsNone(
                        forbidden.search(entry["command"]),
                        f"{exercise.id} records {entry['command']!r}, which would "
                        f"hand over the diagnosis",
                    )

    def test_entries_match_their_commands_file(self):
        for exercise, transcript in self.transcripts():
            blocks = tse.parse_commands((exercise.path / "commands.txt").read_text())
            recorded = [e["command"] for e in transcript.get("entries", [])]
            with self.subTest(exercise.id):
                self.assertEqual([b["command"] for b in blocks], recorded,
                                 f"{exercise.id}: commands.txt and transcript disagree")

    def test_every_entry_produced_output(self):
        for exercise, transcript in self.transcripts():
            for entry in transcript.get("entries", []):
                with self.subTest(f"{exercise.id}:{entry['command'][:40]}"):
                    self.assertTrue(entry.get("output", "").strip(),
                                    f"{exercise.id}: {entry['command'][:40]} recorded nothing")


class LeakGate(unittest.TestCase):
    """The same bar as the recordings, over every committed file.

    This file is one of the three exempt from the scan, which is what makes it
    the right place to keep planted samples: they have to look like the real
    thing to prove anything, and they cannot live anywhere the scan can read.
    """

    # One obviously fake sample per repository-wide rule, with the description
    # that rule should report. Every string here is a documentation placeholder
    # or a reserved value, never a real credential.
    PLANTED = [
        ("/Users/someone/Projects/thing", "a home directory"),
        ("arn:aws:eks:us-east-1:123456789012:cluster/prod", "an AWS ARN"),
        ("123456789012.dkr.ecr.us-east-1.amazonaws.com", "an ECR registry with an account id"),
        ("pod ip 10.244.0.23", "a private network address"),
        ("172.22.0.2", "a private network address"),
        ("192.168.1.5", "a private network address"),
        # AWS's own published example key id.
        ("AKIAIOSFODNN7EXAMPLE", "an AWS access key id"),
        ("ghp_" + "0" * 36, "a GitHub token"),
        # The format GitHub now issues by default. An outside audit found the
        # rule above did not cover it while every check here was passing.
        ("github_pat_" + "0" * 32, "a GitHub fine-grained token"),
        ("-----BEGIN RSA PRIVATE KEY-----", "a private key"),
        ("xoxb-000000000000-000000000000-abcdefghijklmnop", "a Slack token"),
        # A webhook URL carries no token prefix and is a credential by itself.
        ("https://hooks.slack.com/services/T00000000/B00000000/" + "X" * 24,
         "a Slack webhook URL"),
        ("fd12:3456:789a:1::1", "a private IPv6 address"),
        ("fe80::1ff:fe23:4567:890a", "a private IPv6 address"),
        ("someone@notreserved.test", "an email address"),
        # Everything below was planted by an audit and got straight through.
        # Twelve of seventeen credential formats did. The list had read as
        # thorough for weeks on the strength of the nine it did catch, which is
        # the same way the identity scan went missing.
        #
        # AWS's own published example secret, which is the half that spends
        # money. The id above opens nothing without it, and the id was the half
        # this list had.
        ("aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
         "an AWS secret"),
        ("AWS_SESSION_TOKEN=FwoGZXIvYXdzEBYaDGV4YW1wbGV0b2tlbg==", "an AWS secret"),
        # The provider whose key is most likely to be sitting in this author's
        # own shell history.
        ("sk-ant-api03-" + "0" * 90, "an AI provider API key"),
        ("sk-proj-" + "0" * 40, "an AI provider API key"),
        ("sk_live_" + "0" * 24, "a Stripe secret key"),
        ("AIzaSy" + "A" * 33, "a Google API key"),
        ("npm_" + "0" * 36, "an npm token"),
        ("pypi-AgEIcHlwaS5vcmc" + "A" * 32, "a PyPI token"),
        ("AccountKey=" + "A" * 86 + "==", "an Azure storage key"),
        ('"private_key_id": "0123456789abcdef0123456789abcdef01234567"',
         "a Google service account key"),
        ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.c2lnbmF0dXJlZ29lc2hlcmU",
         "a signed token"),
        # Base64 in a kubeconfig, which none of the prefix rules can see. This
        # course teaches Kubernetes, so a pasted kubeconfig is a realistic find.
        ("    client-certificate-data: LS0tLS1CRUdJTiBDRVJU",
         "a kubeconfig credential"),
        ("/Volumes/Backup Drive/projects", "a mounted volume"),
        (r"C:\Users\someone\Projects", "a Windows home directory"),
    ]

    # Formats this scan knowingly does not catch, recorded so the gap is a
    # decision somebody made rather than one nobody noticed.
    #
    # A bare AWS secret with nothing naming it is forty characters of base64,
    # which is also what a lockfile integrity hash is. A rule on shape alone
    # fires constantly, and a scan that cries wolf is a scan somebody turns off.
    # Every realistic way of writing one names it, and the named forms above are
    # caught. GitHub's own secret scanning, which is free on public repositories
    # and validates against the provider, is the right tool for the bare form.
    KNOWINGLY_UNCAUGHT = [
        ("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "a bare AWS secret"),
    ]

    # Real text from this repository that each rule has to live beside without
    # firing. Every one of these was an actual false positive when the transcript
    # rules were first pointed at the whole repository.
    TOLERATED = [
        ("10.29.8", "the preact version in package-lock.json"),
        ("nginx/1.10.3", "a version string that looks like an address"),
        ("postgres 10.4.2", "another one"),
        ("user1_1@example.invalid", "the seeded addresses in the SQL lab"),
        ("support@example.com", "a documentation address"),
        ("/home/runner/work/repo", "GitHub Actions' own working directory"),
        # Every commit in this repository authors as one of these. They exist
        # so a commit can be attributed without publishing a mailbox, so
        # finding one is the system working rather than a leak. The identity
        # scan would otherwise report all thirty odd commits.
        ("103166826+h-vance@users.noreply.github.com", "a GitHub noreply address"),
        ("noreply@github.com", "the address Dependabot commits as"),
        # A version string, not an address. The IPv6 rule needs at least two
        # colon separated groups after a unique local or link local prefix.
        ("fd00 build 1", "a word that starts like a private IPv6 prefix"),
    ]

    def test_the_repository_is_clean(self):
        for path in tse.tracked_files():
            if path in tse.LEAK_EXEMPT:
                continue
            try:
                text = (ROOT / path).read_text()
            except (UnicodeDecodeError, OSError):
                continue
            found = tse.scan_for_leaks(text, tse.leak_patterns_for(path))
            with self.subTest(path):
                self.assertEqual(
                    found, [],
                    f"{path} would publish {found[0][1] if found else ''}: "
                    f"{found[0][2] if found else ''!r}",
                )

    def test_every_exempt_path_still_exists(self):
        """An exemption that outlives its file is a hole nobody argued for."""
        for path, reason in tse.LEAK_EXEMPT.items():
            with self.subTest(path):
                self.assertTrue((ROOT / path).is_file(),
                                f"{path} is exempt ({reason}) but does not exist")

    def test_every_planted_sample_is_caught(self):
        for sample, description in self.PLANTED:
            found = tse.scan_for_leaks(sample, tse.REPO_LEAK_PATTERNS)
            with self.subTest(description):
                self.assertIn(description, [item[1] for item in found],
                              f"{sample!r} was not reported as {description}")

    def test_every_rule_has_a_planted_sample(self):
        """A rule that ships without a sample has never been proven to fire."""
        covered = {description for _, description in self.PLANTED}
        for _, description in tse.REPO_LEAK_PATTERNS:
            with self.subTest(description):
                self.assertIn(description, covered,
                              f"no planted sample proves the rule for {description} fires")

    def test_the_known_gaps_are_still_the_gaps(self):
        """A limitation written down has to stay true or stop being written down.

        If a later rule starts catching one of these, the note explaining why it
        is not caught has become false. Failing here is the good outcome: it
        means the gap closed, and the paragraph above the list should say so
        rather than keep arguing for a decision nobody is making any more.
        """
        for sample, what in self.KNOWINGLY_UNCAUGHT:
            found = tse.scan_for_leaks(sample, tse.REPO_LEAK_PATTERNS)
            with self.subTest(what):
                self.assertEqual(
                    found, [],
                    f"{what} is now caught, so the note saying it is not is stale",
                )

    def test_no_rule_fires_on_what_it_must_tolerate(self):
        for sample, what in self.TOLERATED:
            found = tse.scan_for_leaks(sample, tse.REPO_LEAK_PATTERNS)
            with self.subTest(what):
                self.assertEqual(found, [],
                                 f"{what} ({sample!r}) was wrongly reported as {found}")

    def test_recordings_are_held_to_more_than_everything_else(self):
        """The extra rules are the point of having two lists rather than one."""
        self.assertGreater(len(tse.TRANSCRIPT_LEAK_PATTERNS), len(tse.REPO_LEAK_PATTERNS))
        for rule in tse.REPO_LEAK_PATTERNS:
            self.assertIn(rule, tse.TRANSCRIPT_LEAK_PATTERNS)
        # A fixed date in a seed file makes a lab reproducible. The same string
        # in a recording means the recorder's clock leaked. Same pattern,
        # opposite meaning, and only the location tells them apart.
        stamp = "2026-08-01 09:00:00"
        self.assertEqual(tse.scan_for_leaks(stamp, tse.REPO_LEAK_PATTERNS), [])
        self.assertNotEqual(tse.scan_for_leaks(stamp, tse.TRANSCRIPT_LEAK_PATTERNS), [])

    def test_transcripts_are_scanned_under_the_stricter_rules(self):
        self.assertIs(
            tse.leak_patterns_for("labs/docker/01-x/transcript.json"),
            tse.TRANSCRIPT_LEAK_PATTERNS,
        )
        self.assertIs(tse.leak_patterns_for("labs/sql/_stack/seed.sql"), tse.REPO_LEAK_PATTERNS)

    # Every encoding a person could plausibly write a file in, and both of the
    # ways this went wrong. The marked forms raised and were skipped, silently
    # and without moving the count of files scanned. The unmarked wide forms did
    # not even raise: ASCII with a null after every character is valid UTF-8, so
    # the decode succeeded and handed the rules `g\x00h\x00p\x00_\x00`.
    ENCODINGS = [
        "utf-8", "utf-8-sig",
        "utf-16", "utf-16-le", "utf-16-be",
        "utf-32", "utf-32-le", "utf-32-be",
    ]

    def test_a_credential_is_found_whatever_it_was_written_in(self):
        line = "Token pasted from a Windows box: ghp_" + "A" * 36 + "\n"
        for encoding in self.ENCODINGS:
            with self.subTest(encoding):
                text = tse.decode_for_scanning(line.encode(encoding))
                self.assertIsNotNone(text, f"{encoding} was not recognized as text at all")
                found = tse.scan_for_leaks(text, tse.REPO_LEAK_PATTERNS)
                self.assertIn(
                    "a GitHub token", [item[1] for item in found],
                    f"a token written in {encoding} went unreported",
                )

    def test_bytes_that_are_not_text_are_refused_rather_than_skipped(self):
        """The caller has to be able to tell 'nothing in it' from 'never read'."""
        png = bytes([137, 80, 78, 71, 13, 10, 26, 10]) + bytes(range(256)) * 4
        self.assertIsNone(tse.decode_for_scanning(png))

    def test_ordinary_text_is_not_mistaken_for_a_wide_encoding(self):
        for sample in ("plain ascii\n", "café naïve\n", "日本語\n"):
            with self.subTest(sample):
                self.assertEqual(tse.decode_for_scanning(sample.encode("utf-8")), sample)

    def test_every_declared_binary_still_exists(self):
        """Same rule as the exemptions: a note about a file that is gone is a hole."""
        for path, reason in tse.LEAK_BINARY.items():
            with self.subTest(path):
                self.assertTrue((ROOT / path).is_file(),
                                f"{path} is declared binary ({reason}) but does not exist")

    def test_nothing_tracked_is_currently_unreadable(self):
        """The list of declared binaries is empty because it can be.

        Every file in the repository is text and every one of them is read. If
        this starts failing, a binary was added: either it belongs here and goes
        in LEAK_BINARY with a reason, or it does not belong here at all.
        """
        import subprocess
        listed = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.split()
        unreadable = []
        for name in listed:
            path = ROOT / name
            if not path.is_file() or name in tse.LEAK_BINARY:
                continue
            if tse.decode_for_scanning(path.read_bytes()) is None:
                unreadable.append(name)
        self.assertEqual(unreadable, [], "tracked files the leak scan cannot read")


class Links(unittest.TestCase):
    """Every part of the link check that can be tested without a network.

    Extraction and classification are the whole of the logic; the HTTP request
    is four lines around them. So all of it is covered here, offline, and runs
    in CI where reaching the internet would make the suite flaky.
    """

    def test_every_shape_a_link_is_written_in_is_found(self):
        text = "\n".join([
            "See [the guide](CONTRIBUTING.md) first.",
            'A tag: <a href="/prove-it-labs/start">start</a>',
            "Bare in prose: https://example.com/a and nothing else.",
            '[titled](https://example.com/b "why")',
            "[angled](<https://example.com/c>)",
        ])
        found = {target for _, target in tse.extract_links(text)}
        self.assertIn("CONTRIBUTING.md", found)
        self.assertIn("/prove-it-labs/start", found)
        self.assertIn("https://example.com/a", found)
        self.assertIn("https://example.com/b", found)
        self.assertIn("https://example.com/c", found)

    def test_trailing_punctuation_is_not_part_of_the_address(self):
        found = {t for _, t in tse.extract_links("Read https://example.com/page, then stop.")}
        self.assertIn("https://example.com/page", found)
        self.assertNotIn("https://example.com/page,", found)

    def test_a_lab_address_is_never_requested(self):
        """These are what the exercise tells a learner to curl.

        Requesting them from the machine running this check reaches nothing, or
        reaches something of somebody else's, and neither says anything about
        the course.
        """
        for target in [
            "http://127.0.0.1:8100/customers",
            "http://localhost:4321/prove-it-labs",
            "https://gateway:8443",
            "http://orders-api:8080/customers",
            "https://reports:8443",
            "http://postgres:5432",
        ]:
            with self.subTest(target):
                self.assertEqual(tse.classify_link(target), "lab")

    def test_a_url_built_from_a_variable_is_not_an_address(self):
        for target in [
            "https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-${ARCH}",
            "https://example.com/$(whoami)",
            "https://example.com/{{ version }}",
        ]:
            with self.subTest(target):
                self.assertEqual(tse.classify_link(target), "ignored")

    def test_a_public_host_is_external(self):
        self.assertEqual(tse.classify_link("https://kind.sigs.k8s.io/dl/v0.30.0"), "external")

    def test_the_self_exemption_covers_only_this_repository(self):
        """The exemption that could have hidden the bug it was written beside.

        While the repository was private its links to itself returned 404 and
        could not be checked. Exempting every github.com/<owner>/ link would
        also have exempted the stale one left behind by the rename, which is
        exactly the link this whole check found. Only the exact current address
        was ever skipped, which is what this asserts. The exemption has since
        expired on its own, and this still holds: it is the shape of the rule
        that mattered, not the window it applied in.
        """
        own = ("https://github.com/h-vance/prove-it-labs", "https://h-vance.github.io")
        self.assertEqual(
            tse.classify_link("https://github.com/h-vance/prove-it-labs/actions", own), "self")
        self.assertEqual(
            tse.classify_link("https://github.com/h-vance/technical-support-engineering", own),
            "external",
            "a link to the name this repository used to have must still be checked",
        )

    def test_the_self_exemption_is_derived_and_not_written_down(self):
        """A hard-coded name would go stale on the next rename, silently."""
        own = tse.own_urls()
        self.assertTrue(own, "no address for this repository could be derived")
        for url in own:
            self.assertEqual(url, url.lower())
            self.assertFalse(url.endswith(("/", ".git")))

    def test_a_site_link_must_carry_the_configured_base(self):
        """The bug this found: an internal link left on the old base path.

        `/technical-support-engineering/reference/spoken-answer-template` was a
        404 on the published site for anybody who clicked it.
        """
        base = tse.site_base_path()
        self.assertTrue(base.startswith("/"), f"no base path found, got {base!r}")
        self.assertIsNone(
            tse.check_local_link(f"{base}/reference/spoken-answer-template", "README.md", base))
        self.assertIsNotNone(
            tse.check_local_link("/some-other-name/reference/x", "README.md", base))

    def test_a_relative_link_has_to_resolve_on_disk(self):
        self.assertIsNone(tse.check_local_link("CONTRIBUTING.md", "README.md", "/x"))
        problem = tse.check_local_link("no-such-file.md", "README.md", "/x")
        self.assertIsNotNone(problem)
        self.assertIn("no such file", problem)

    def test_an_anchor_has_to_name_a_heading_that_exists(self):
        slugs = tse.heading_slugs("# The Ticket\n\n## Why This One Exists\n\ntext\n")
        self.assertEqual(slugs, {"the-ticket", "why-this-one-exists"})

    def test_punctuation_is_dropped_from_a_slug_rather_than_replaced(self):
        """github-slugger deletes punctuation. Replacing it is a two-way error.

        "the author's" has to become "the-authors". Turning the apostrophe into
        a hyphen gives "the-author-s", which no renderer produces, so a working
        link reads as broken and a broken one reads as fine. This checker had it
        wrong until an apostrophe in one of AUDIT.md's own headings found it.
        """
        self.assertEqual(
            tse.heading_slugs("## P3. A machine that is not the author's\n"),
            {"p3-a-machine-that-is-not-the-authors"},
        )
        self.assertEqual(
            tse.heading_slugs("## What `tse links` does (and does not)\n"),
            {"what-tse-links-does-and-does-not"},
        )
        self.assertEqual(
            tse.heading_slugs("## Quotes: “evidence”, not opinion\n"),
            {"quotes-evidence-not-opinion"},
        )

    def test_this_document_resolves_its_own_anchors(self):
        """AUDIT.md cross-references itself 23 times and is read on GitHub."""
        audit = ROOT / "AUDIT.md"
        if not audit.is_file():
            self.skipTest("AUDIT.md has not been written")
        text = audit.read_text()
        slugs = tse.heading_slugs(text)
        broken = sorted({
            target for target in re.findall(r"\]\(#([^)]+)\)", text)
            if target not in slugs
        })
        self.assertEqual(broken, [], f"AUDIT.md links to headings it does not have: {broken}")

    def test_the_whole_repository_currently_passes_offline(self):
        """The check, run for real, with no network involved."""
        base = tse.site_base_path()
        own = tse.own_urls()
        broken = []
        for name in tse.tracked_files():
            if not name.endswith(tse.LINK_SUFFIXES) or name in tse.LEAK_EXEMPT:
                continue
            text = tse.read_link_source(ROOT / name)
            if text is None:
                continue
            for number, target in tse.extract_links(text):
                if tse.classify_link(target, own) in ("ignored", "lab", "self", "external"):
                    continue
                problem = tse.check_local_link(target, name, base)
                if problem:
                    broken.append(f"{name}:{number}: {target} -- {problem}")
        self.assertEqual(broken, [])


class AffectedExercises(unittest.TestCase):
    """Which exercises a change can break, and what it must never miss.

    This decides what CI spends its minutes on, so the expensive mistake is not
    a slow run, it is an exercise nobody verified reporting green. Every test
    here is about the narrow direction.
    """

    def setUp(self):
        self.all = [exercise.id for exercise in tse.load_exercises()]

    def test_a_change_to_the_tools_verifies_everything(self):
        """The case that made this necessary.

        Bounding an assertion moved every grader's command into a fresh shell
        and broke the two exercises that used a variable or a function. That
        commit touched nothing under labs/, so anything keyed on exercise
        directories alone would have verified none of them.
        """
        for path in ("tools/lib/assert.sh", "tools/tse", "tools/lib/rubric.py"):
            with self.subTest(path):
                self.assertEqual(tse.affected_exercises([path]), self.all)

    def test_a_change_to_this_workflow_verifies_everything(self):
        self.assertEqual(
            tse.affected_exercises([".github/workflows/verify.yml"]), self.all)

    def test_a_shared_stack_verifies_its_whole_track(self):
        for track in {exercise.split("/")[0] for exercise in self.all}:
            with self.subTest(track):
                chosen = tse.affected_exercises([f"labs/{track}/_stack/compose.yaml"])
                self.assertEqual(chosen, [i for i in self.all if i.startswith(f"{track}/")])
                self.assertTrue(chosen, f"{track} selected nothing")

    def test_a_change_inside_one_exercise_verifies_that_one(self):
        for exercise in self.all:
            with self.subTest(exercise):
                for name in ("check.sh", "setup/compose.override.yaml", "meta.yaml"):
                    self.assertEqual(
                        tse.affected_exercises([f"labs/{exercise}/{name}"]), [exercise])

    def test_every_exercise_is_reachable(self):
        """A slug this cannot select is one that would never be verified again."""
        reachable = set()
        for exercise in self.all:
            reachable.update(tse.affected_exercises([f"labs/{exercise}/check.sh"]))
        self.assertEqual(sorted(reachable), sorted(self.all))

    def test_changes_are_combined_rather_than_replaced(self):
        chosen = tse.affected_exercises([
            f"labs/{self.all[0]}/check.sh",
            f"labs/{self.all[-1]}/check.sh",
        ])
        self.assertEqual(chosen, [self.all[0], self.all[-1]])

    def test_a_change_that_touches_no_exercise_selects_none(self):
        self.assertEqual(tse.affected_exercises(["README.md", "site/src/lib/labs.ts"]), [])

    def test_the_order_matches_tse_list(self):
        """CI reads this as a matrix, and a matrix that reshuffles is unreadable."""
        self.assertEqual(tse.affected_exercises(["tools/tse"]), self.all)

    def test_grouping_loses_nothing(self):
        """The property that matters: packing into jobs must not drop an exercise.

        One job per exercise spent about three quarters of its minutes on runner
        startup, teardown and per-job billing rounding rather than on testing,
        so they are grouped by stack. The saving is worthless if an exercise can
        fall out of the matrix on the way.
        """
        groups = tse.group_by_stack(self.all)
        packed = [exercise for group in groups for exercise in group["exercises"]]
        self.assertEqual(sorted(packed), sorted(self.all))
        self.assertEqual(len(packed), len(set(packed)), "an exercise is in two groups")

    def test_a_group_is_the_stack_its_exercises_actually_use(self):
        """A mixed incident borrows a stack, and must be grouped with it.

        mixed/01 runs on the Docker stack and mixed/02 on the api one. Grouping
        by the exercise's own track rather than by the stack it uses would build
        those stacks an extra time each, which is the cost this exists to remove.
        """
        by_id = {exercise.id: exercise for exercise in tse.load_exercises()}
        for group in tse.group_by_stack(self.all):
            for exercise in group["exercises"]:
                with self.subTest(exercise):
                    self.assertEqual(by_id[exercise].stack_source, group["stack"])

    def test_grouping_is_smaller_than_not_grouping(self):
        groups = tse.group_by_stack(self.all)
        self.assertLess(len(groups), len(self.all))

    def test_a_narrow_change_still_groups(self):
        one = tse.affected_exercises([f"labs/{self.all[0]}/check.sh"])
        groups = tse.group_by_stack(one)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["exercises"], one)

    def test_nothing_selected_makes_no_groups(self):
        """An empty matrix is not a valid job, so the workflow skips on zero."""
        self.assertEqual(tse.group_by_stack([]), [])


class DetectorsActuallyFire(unittest.TestCase):
    """A linter that cannot fail is not a linter.

    These assert the spoiler detector catches the kinds of sentence it exists
    to catch, so a regex that silently stops matching is caught here rather
    than by a learner being handed the answer.
    """

    def test_spoiler_terms_match_known_bad_tickets(self):
        bad = [
            "The container keeps restarting after our deploy.",
            "kubectl says the pod is not ready.",
            "We think an environment variable is missing.",
            "The API returns 403 for one of our users.",
            "Postgres seems to be refusing connections.",
            "Our client is being rate limited.",
            "The DNS name stopped resolving.",
            "Our users see a certificate warning in the browser.",
            "The TLS handshake fails against your endpoint.",
            "I think the report is missing an index.",
            "The join is dropping rows from our export.",
            "Your p99 latency metrics look wrong.",
            "We had to chown the data directory.",
        ]
        for sentence in bad:
            with self.subTest(sentence):
                self.assertTrue(SPOILER_TERMS.search(sentence),
                                f"spoiler detector missed: {sentence}")

    def test_lazy_option_detector_fires(self):
        for text in ("All of the above", "none of these", "Both of them", "all of above"):
            with self.subTest(text):
                self.assertTrue(LAZY_OPTIONS.search(text), f"lazy option missed: {text}")

    def test_lazy_option_detector_allows_real_options(self):
        for text in (
            "The service is listening, and nothing beyond that.",
            "Every one of the rows above the threshold was dropped.",
            "None of the requests carried an identifier.",
        ):
            with self.subTest(text):
                self.assertIsNone(LAZY_OPTIONS.search(text), f"false positive: {text}")

    def test_giveaway_detector_fires_on_an_echoed_answer(self):
        question = "The container exits immediately after it starts. What does that prove?"
        option = "That the container exits immediately after it starts for a reason inside it."
        self.assertIsNotNone(
            giveaway_overlap(question, option),
            "an answer repeating the question verbatim should be caught",
        )

    def test_giveaway_detector_allows_an_answer_in_its_own_words(self):
        question = "The container exits immediately after it starts. What does that prove?"
        option = "The process finished or failed on its own, rather than being stopped from outside."
        self.assertIsNone(
            giveaway_overlap(question, option),
            "a genuinely reworded answer should not be flagged",
        )

    def test_spoiler_terms_allow_ordinary_customer_language(self):
        good = [
            "Nobody on our team can load the customer dashboard.",
            "It spins for a while and then times out.",
            "Our order events are not showing up in your system any more.",
            "One of our analysts cannot export the incident report.",
            "The sync gets partway through and then starts erroring.",
            "Our monthly report is missing about a third of our accounts.",
            "Customers get a security warning when they visit the portal.",
            "The service stopped writing and the disk still looks fine to us.",
            "Two of our reports disagree about the same number.",
            "Everything is slow for one of our teams but nobody else.",
        ]
        for sentence in good:
            with self.subTest(sentence):
                self.assertIsNone(SPOILER_TERMS.search(sentence),
                                  f"spoiler detector false positive: {sentence}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
