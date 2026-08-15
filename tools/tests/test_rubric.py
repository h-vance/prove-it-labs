#!/usr/bin/env python3
"""Tests for the writing rubric.

A rubric that passes everything is worse than no rubric, because it converts
"nobody checked this" into "this was checked and it was fine". So every rule is
proven to fire, and proven to fire *alone*: each bad draft below is the good
draft with exactly one thing taken away, and the assertion is that exactly one
rule notices.

That second half is what catches an over-broad rule. A length check that also
happens to fail on tone, or a vocabulary check that trips on ordinary words,
would show up here as two failures where one was intended.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_loader = importlib.machinery.SourceFileLoader("rubric", str(ROOT / "tools" / "lib" / "rubric.py"))
_spec = importlib.util.spec_from_loader("rubric", _loader)
rubric = importlib.util.module_from_spec(_spec)
sys.modules["rubric"] = rubric
_loader.exec_module(rubric)

EVIDENCE = rubric.sections("""
# Evidence

## Workflow

- `customer list`

## Figures

- `47 minutes`

## Ruled out

- `a change to your data`

## Facts

- `server_started port=8080`
- `Up (healthy)`
""")

# Passes all six customer rules. Every bad draft below is this one with a
# single thing removed or added.
GOOD_UPDATE = """
Hi Dana,

Your customer list was failing to load for everyone this morning, for a total
of 47 minutes. Pages that did not read customer records kept working normally
throughout, which is why it looked partial from your side.

The cause was a configuration change made during last night's maintenance. It
changed the address our application uses to reach the database holding your
records, so those requests could not complete. We corrected it and confirmed
the list is loading again.

One thing I want to state plainly, because it is the question I would be
asking: there was no data lost and there was not a change to your data of any
kind. Your own records are exactly as they were before this started.

I am raising the change internally, because a maintenance step should not have
been able to make this edit without anyone catching it first. I will send you
the outcome of that review by Friday.
"""

# Passes all five escalation rules.
GOOD_ESCALATION = """
Impact: Halden Freight, enterprise, total loss of service for all users from
06:00 to 09:12. Found by the customer rather than by us.

Evidence: the application logged `server_started port=8080` on the way up while
the published mapping pointed elsewhere, and the container reported
`Up (healthy)` for the entire outage because its check runs inside the
container and never crossed the mapping that was wrong.

Confirmed: application process health, clean startup, database availability.

Ruled out: a change to your data, application crash, dependency failure.

Suspected cause: last night's release changed the published target while the
application kept listening where it always had.

Request: please confirm whether the same edit exists in any other service that
shares this release template, and tell me whether the platform team can own
adding a check that connects from outside the published address.
"""


def failing(rubric_name: str, draft: str) -> set[str]:
    """The descriptions of every rule this draft fails."""
    return {
        description
        for description, rule in rubric.RUBRICS[rubric_name]
        if rule(draft, EVIDENCE) is not None
    }


class GoodDraftsPass(unittest.TestCase):
    def test_a_good_customer_update_passes_every_rule(self):
        self.assertEqual(failing("customer", GOOD_UPDATE), set())

    def test_a_good_escalation_passes_every_rule(self):
        self.assertEqual(failing("escalation", GOOD_ESCALATION), set())


class EachRuleFiresAlone(unittest.TestCase):
    """One thing removed, one rule notices. Anything else is over-reach."""

    def assert_only(self, rubric_name: str, draft: str, expected: str):
        self.assertEqual(failing(rubric_name, draft), {expected})

    def test_missing_workflow(self):
        self.assert_only(
            "customer",
            GOOD_UPDATE.replace("customer list", "service"),
            "states the impact in the customer's terms",
        )

    def test_missing_figure(self):
        self.assert_only(
            "customer",
            GOOD_UPDATE.replace("for a total\nof 47 minutes", "for a while"),
            "cites a specific figure",
        )

    def test_missing_ruled_out(self):
        self.assert_only(
            "customer",
            GOOD_UPDATE.replace("there was not a change to your data of any\nkind",
                                "nothing else happened"),
            "names something ruled out",
        )

    def test_missing_next_step(self):
        # Everything up to the closing commitment, padded back to length so only
        # the ending rule can fire. The padding is deliberately free of any
        # commitment wording: an earlier version of this used "confirmed" in its
        # filler, which satisfied the rule and quietly proved nothing.
        without_ending = GOOD_UPDATE.split("I am raising the change")[0]
        padded = without_ending + ("\nEvery account on the plan saw the same "
                                   "behavior during that window. " * 3)
        self.assert_only("customer", padded, "ends with a next step and an owner")

    def test_internal_vocabulary(self):
        self.assert_only(
            "customer",
            GOOD_UPDATE.replace("our application", "our container"),
            "uses no internal vocabulary",
        )

    def test_too_long(self):
        # The commitment is restored after the padding on purpose. Appending
        # filler alone fails two rules rather than one, and that is the ending
        # rule working rather than over-reaching: see the test below.
        padded = (
            GOOD_UPDATE
            + ("\nWe appreciate your patience with all of this. " * 40)
            + "\nI will send you the outcome of that review by Friday."
        )
        self.assert_only("customer", padded, "is the right length")

    def test_a_commitment_buried_under_padding_does_not_count(self):
        """Not a quirk of the test. The rule reads where the reader reads.

        A next step sitting under forty lines of pleasantries is one nobody
        reaches, so the rule looking only at the closing lines is the behavior
        worth having rather than a limitation to work around.
        """
        buried = GOOD_UPDATE + ("\nWe appreciate your patience with all of this. " * 40)
        self.assertIn("ends with a next step and an owner", failing("customer", buried))

    def test_escalation_missing_a_section(self):
        self.assert_only(
            "escalation",
            GOOD_ESCALATION.replace("Suspected cause:", "Probably:"),
            "answers every question an engineer will ask",
        )

    def test_escalation_without_the_specifics(self):
        softened = (GOOD_ESCALATION
                    .replace("`server_started port=8080`", "the expected port")
                    .replace("`Up (healthy)`", "a healthy state"))
        self.assert_only("escalation", softened, "quotes the technical specifics")


class TheTwoRubricsDisagreeOnPurpose(unittest.TestCase):
    """The reason the module is parameterized rather than written once.

    A customer update fails for naming internal machinery. An escalation fails
    for leaving it out. If one rubric could grade both, one of them would be
    getting the wrong standard.
    """

    def test_internal_vocabulary_is_a_defect_in_only_one_of_them(self):
        with_machinery = GOOD_UPDATE.replace("our application", "our container")
        self.assertIn("uses no internal vocabulary", failing("customer", with_machinery))
        # The escalation rubric has no such rule at all.
        self.assertNotIn(
            "uses no internal vocabulary",
            {description for description, _ in rubric.RUBRICS["escalation"]},
        )

    def test_the_specifics_rule_exists_in_only_the_escalation(self):
        self.assertNotIn(
            "quotes the technical specifics",
            {description for description, _ in rubric.RUBRICS["customer"]},
        )


class RulesDoNotOverReach(unittest.TestCase):
    def test_ordinary_words_containing_a_banned_term_are_left_alone(self):
        """Substring matching would fire on these, and did until it was fixed."""
        draft = GOOD_UPDATE.replace(
            "Your own records are exactly as they were before this started.",
            "Your own records are exactly as they were, and the annulled "
            "invoices on the tripod report are untouched.",
        )
        self.assertNotIn("uses no internal vocabulary", failing("customer", draft))

    def test_an_exercise_without_a_section_does_not_fail_for_it(self):
        """Rules driven by evidence go quiet when that evidence is absent.

        A future exercise that declares no figures should not be failed for not
        citing one, or the rubric stops being reusable the moment it is reused.
        """
        empty: dict[str, str] = {}
        still_failing = {
            description
            for description, rule in rubric.RUBRICS["customer"]
            if rule(GOOD_UPDATE, empty) is not None
        }
        self.assertEqual(still_failing, set())


class EveryRuleIsTested(unittest.TestCase):
    """A rule that ships without a test proving it fires has never been proven."""

    PROVEN = {
        "customer": {
            "states the impact in the customer's terms",
            "cites a specific figure",
            "names something ruled out",
            "ends with a next step and an owner",
            "uses no internal vocabulary",
            "is the right length",
        },
        "escalation": {
            "answers every question an engineer will ask",
            "quotes the technical specifics",
            "names something ruled out",
            "ends with a request and an owner",
            "is the right length",
        },
    }

    def test_every_rule_has_a_case_that_fires_it(self):
        for name, rules in rubric.RUBRICS.items():
            for description, _ in rules:
                with self.subTest(f"{name}: {description}"):
                    self.assertIn(description, self.PROVEN[name])

    def test_no_rubric_is_missing_from_the_proven_list(self):
        self.assertEqual(set(rubric.RUBRICS), set(self.PROVEN))


class RealExercisesAgree(unittest.TestCase):
    """The committed drafts, graded exactly as the learner's will be."""

    CASES = (
        ("communication/01-the-update-you-owe-after-an-outage",
         "customer", "customer-update.md"),
        ("communication/02-the-escalation-that-does-not-come-back",
         "escalation", "escalation.md"),
    )

    def test_every_setup_draft_fails_and_every_solution_passes(self):
        for exercise, name, filename in self.CASES:
            directory = ROOT / "labs" / exercise
            evidence = rubric.sections((directory / "setup" / "evidence.md").read_text())
            for variant, should_fail in (("setup", True), ("solution", False)):
                draft = (directory / variant / filename).read_text()
                failures = {
                    description
                    for description, rule in rubric.RUBRICS[name]
                    if rule(draft, evidence) is not None
                }
                with self.subTest(f"{exercise}:{variant}"):
                    if should_fail:
                        self.assertTrue(failures, f"{exercise} {variant} draft passes already")
                    else:
                        self.assertEqual(failures, set())

    def test_the_two_evidence_files_are_identical_across_variants(self):
        """The evidence is reference material, not part of the answer."""
        for exercise, _, _ in self.CASES:
            directory = ROOT / "labs" / exercise
            with self.subTest(exercise):
                self.assertEqual(
                    (directory / "setup" / "evidence.md").read_text(),
                    (directory / "solution" / "evidence.md").read_text(),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
