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

    def test_no_em_dashes(self):
        for path in sorted(ROOT.glob("labs/*/*/*.md")) + sorted(ROOT.glob("labs/*/*/hints/*.md")):
            with self.subTest(str(path.relative_to(ROOT))):
                self.assertNotIn("—", path.read_text(), f"{path} contains an em dash")

    # US spelling throughout. Caught "join behaviour" sitting in an evidence
    # layer, which renders as a chip on the exercise page, so it was learner
    # visible rather than an internal note. Only the endings that actually
    # differ are listed: a general -our or -ise rule would fire on "our",
    # "rise" and half the prose in the repository.
    BRITISH = re.compile(
        r"\b(?:colour|behaviour|favour|honour|labour|neighbour|rumour"
        r"|normalis|recognis|organis|initialis|customis|optimis|specialis|apologis|analyse"
        r"|centre|metre|litre|defence|offence|licence|pretence"
        r"|catalogue|dialogue|analogue"
        r"|labelled|cancelled|travelling|modelling|signalling)\w*",
        re.IGNORECASE,
    )

    def test_us_spelling(self):
        """Every word a reader sees, not only the one somebody happened to notice."""
        paths = (
            sorted(ROOT.glob("labs/*/*/*.md"))
            + sorted(ROOT.glob("labs/*/*/hints/*.md"))
            + sorted(ROOT.glob("labs/*/*/meta.yaml"))
            + sorted(ROOT.glob("labs/*/*/questions.json"))
            + sorted(ROOT.glob("reference/*.md"))
            + [ROOT / "README.md", ROOT / "CONTRIBUTING.md"]
        )
        for path in paths:
            if not path.is_file():
                continue
            found = self.BRITISH.search(path.read_text())
            with self.subTest(str(path.relative_to(ROOT))):
                self.assertIsNone(
                    found,
                    f"{path.relative_to(ROOT)} uses British spelling: "
                    f"{found.group(0) if found else ''!r}",
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
        import subprocess

        probe = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Arch}}"],
            capture_output=True, text=True,
        )
        if probe.returncode != 0 or not probe.stdout.strip():
            self.skipTest("Docker is not available on this machine")
        self.assertEqual(tse.node_platform(), f"linux/{probe.stdout.strip()}")

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
