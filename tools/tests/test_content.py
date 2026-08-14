#!/usr/bin/env python3
"""Structural and editorial tests for every exercise.

CONTRIBUTING states rules about how an exercise must be written. Rules that are
only written down decay, so the ones that can be checked are checked here.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
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
    "## Say it out loud",
)

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
        for exercise in EXERCISES:
            if exercise.stack == "none":
                continue
            with self.subTest(exercise.id):
                for variant in ("setup", "solution"):
                    directory = exercise.path / variant
                    self.assertTrue(directory.is_dir(), f"{exercise.id}: no {variant}/")
                    self.assertTrue(any(directory.iterdir()),
                                    f"{exercise.id}: {variant}/ is empty")

    def test_setup_and_solution_provide_the_same_filenames(self):
        """Otherwise switching states leaves a stale file behind."""
        for exercise in EXERCISES:
            if exercise.stack == "none":
                continue
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

    def test_prerequisites_resolve(self):
        known = {e.id for e in EXERCISES}
        for exercise in EXERCISES:
            for prerequisite in exercise.meta.get("prerequisites") or []:
                with self.subTest(exercise.id):
                    self.assertIn(prerequisite, known,
                                  f"{exercise.id}: unknown prerequisite {prerequisite}")

    def test_no_placeholders_left(self):
        for exercise in EXERCISES:
            for path in exercise.path.rglob("*.md"):
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
        ]
        for sentence in bad:
            with self.subTest(sentence):
                self.assertTrue(SPOILER_TERMS.search(sentence),
                                f"spoiler detector missed: {sentence}")

    def test_spoiler_terms_allow_ordinary_customer_language(self):
        good = [
            "Nobody on our team can load the customer dashboard.",
            "It spins for a while and then times out.",
            "Our order events are not showing up in your system any more.",
            "One of our analysts cannot export the incident report.",
            "The sync gets partway through and then starts erroring.",
        ]
        for sentence in good:
            with self.subTest(sentence):
                self.assertIsNone(SPOILER_TERMS.search(sentence),
                                  f"spoiler detector false positive: {sentence}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
