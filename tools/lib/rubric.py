#!/usr/bin/env python3
"""Mechanical checks on a written answer, and an honest account of their limits.

The communication exercises are graded on prose, which is the part of support
work that decides whether an escalation gets acted on or sent back. Prose is
also the thing a linter is worst at, so this module is deliberately narrow: it
checks the claims a machine can actually verify, it names the rule that failed
rather than gesturing at "clarity", and it says out loud that passing is not the
same as being well written.

What it checks is driven by the exercise's own evidence file rather than baked
in here. That is what lets one module grade a customer update and an internal
escalation, which are graded on nearly opposite things: a customer update fails
for naming internal machinery, and an escalation fails for leaving it out.

Zero dependencies, like everything else in tools/. PEP 668 blocks a system pip
install in a Codespace, so a rubric that needed one could not run where the
course runs.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Words that belong in an engineering channel and not in a message to a
# customer. Deliberately not a style list: every one of these names a piece of
# internal machinery the customer neither has nor can act on.
INTERNAL_VOCABULARY = (
    "container", "compose", "docker", "kubernetes", "pod", "kubectl",
    "environment variable", "env var", "localhost", "hostname", "dns",
    "stack trace", "traceback", "null", "exit code", "stderr",
    "deployment manifest", "replica", "endpoint slice", "sidecar",
)

# The shape of an escalation. Each is a question the receiving engineer has to
# have answered before they can pick the work up.
ESCALATION_SECTIONS = (
    ("impact", ("impact",)),
    ("evidence", ("evidence",)),
    ("confirmed", ("confirmed",)),
    ("ruled out", ("ruled out",)),
    ("suspected cause", ("suspected cause", "suspected")),
    ("request", ("request", "asking for", "need from you")),
)

# A closing that commits somebody to something. An update that ends on a
# statement of fact leaves the customer with nothing to expect.
COMMITMENTS = (
    "i will", "i'll", "we will", "we'll", "i have", "we have", "i am", "we are",
    "let me know", "tell me", "send me", "reply", "confirm", "get back to you",
)


def sections(markdown: str) -> dict[str, str]:
    """Split a document into its level-two sections, keyed by lowercase heading."""
    found: dict[str, str] = {}
    heading = None
    body: list[str] = []
    for line in markdown.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            if heading is not None:
                found[heading] = "\n".join(body).strip()
            heading = match.group(1).strip().lower()
            body = []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        found[heading] = "\n".join(body).strip()
    return found


def quoted(text: str) -> list[str]:
    """The backticked items in a section, which is how evidence marks a fact."""
    return [item.strip() for item in re.findall(r"`([^`]+)`", text) if item.strip()]


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text)


def normalize(text: str) -> str:
    """Lowercase with runs of whitespace collapsed, for forgiving comparison."""
    return " ".join(text.lower().split())


# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #
#
# Each returns None when it passes, or a sentence naming what is missing. The
# sentence is what the learner reads, so it says what to do, never just what is
# wrong.


def cites_a_figure(draft: str, evidence: dict[str, str]) -> str | None:
    figures = quoted(evidence.get("figures", ""))
    if not figures:
        return None
    body = normalize(draft)
    if any(normalize(figure) in body for figure in figures):
        return None
    return (
        "Cite at least one specific figure. Reassurance without a number reads "
        "as reassurance without evidence, and the customer cannot tell the two "
        "apart.\n       Available: " + ", ".join(repr(f) for f in figures)
    )


def names_the_workflow(draft: str, evidence: dict[str, str]) -> str | None:
    phrases = quoted(evidence.get("workflow", ""))
    if not phrases:
        return None
    body = normalize(draft)
    if any(normalize(phrase) in body for phrase in phrases):
        return None
    return (
        "Say what the customer could not do, in their words. Impact stated as "
        "the affected workflow is something they can check; impact stated as a "
        "component name is not.\n       Expected one of: "
        + ", ".join(repr(p) for p in phrases)
    )


def names_something_ruled_out(draft: str, evidence: dict[str, str]) -> str | None:
    items = quoted(evidence.get("ruled out", ""))
    if not items:
        return None
    body = normalize(draft)
    if any(normalize(item) in body for item in items):
        return None
    return (
        "Name something you ruled out. \"We looked into it\" is not that, and "
        "the things you eliminated are usually what the customer is most "
        "worried about.\n       Available: " + ", ".join(repr(i) for i in items)
    )


def ends_with_a_next_step(draft: str, _evidence: dict[str, str]) -> str | None:
    tail = normalize(" ".join(draft.strip().splitlines()[-6:]))
    if any(phrase in tail for phrase in COMMITMENTS):
        return None
    return (
        "End with a next step and who owns it. A message that closes on a "
        "statement of fact leaves the reader with nothing to expect and no "
        "reason to reply."
    )


def avoids_internal_vocabulary(draft: str, _evidence: dict[str, str]) -> str | None:
    # Word boundaries, not substrings. "pod" inside "tripod" and "null" inside
    # "annulled" are not the failures this is looking for, and a rule that
    # fires on them teaches people to distrust it.
    body = normalize(draft)
    found = sorted({
        term for term in INTERNAL_VOCABULARY
        if re.search(rf"\b{re.escape(term)}\b", body)
    })
    if not found:
        return None
    return (
        "Remove the internal vocabulary: " + ", ".join(found) + ".\n"
        "       The customer cannot act on any of it, and naming it invites "
        "questions you then have to answer instead of closing the ticket."
    )


def uses_the_technical_specifics(draft: str, evidence: dict[str, str]) -> str | None:
    """The inverse of the rule above, and the reason this module is parameterized.

    An escalation that has been softened into customer language makes the
    receiving engineer go and find the details again, which is the whole cost
    the escalation was supposed to save them.
    """
    facts = quoted(evidence.get("facts", ""))
    if not facts:
        return None
    body = normalize(draft)
    cited = [fact for fact in facts if normalize(fact) in body]
    if len(cited) >= 2:
        return None
    return (
        f"Quote at least two of the technical specifics; found {len(cited)}.\n"
        "       An escalation written in customer language makes the engineer "
        "gather the evidence again, which is the cost it exists to save.\n"
        "       Available: " + ", ".join(repr(f) for f in facts)
    )


def has_every_section(draft: str, _evidence: dict[str, str]) -> str | None:
    body = normalize(draft)
    missing = [
        label for label, accepted in ESCALATION_SECTIONS
        if not any(term in body for term in accepted)
    ]
    if not missing:
        return None
    return (
        "Missing: " + ", ".join(missing) + ".\n"
        "       Each one is a question the receiving engineer has to have "
        "answered before they can pick this up. Leaving one out is what gets "
        "an escalation handed back."
    )


def within_length(low: int, high: int):
    def rule(draft: str, _evidence: dict[str, str]) -> str | None:
        count = len(words(draft))
        if low <= count <= high:
            return None
        if count < low:
            return (
                f"Too short at {count} words; aim for {low} to {high}. There is "
                "not room in fewer to say what happened, what you proved, and "
                "what happens next."
            )
        return (
            f"Too long at {count} words; aim for {low} to {high}. Past this "
            "length the reader starts skimming, and the part they skip is "
            "usually the part you needed them to read."
        )
    return rule


RUBRICS = {
    "customer": [
        ("states the impact in the customer's terms", names_the_workflow),
        ("cites a specific figure", cites_a_figure),
        ("names something ruled out", names_something_ruled_out),
        ("ends with a next step and an owner", ends_with_a_next_step),
        ("uses no internal vocabulary", avoids_internal_vocabulary),
        ("is the right length", within_length(90, 260)),
    ],
    "escalation": [
        ("answers every question an engineer will ask", has_every_section),
        ("quotes the technical specifics", uses_the_technical_specifics),
        ("names something ruled out", names_something_ruled_out),
        ("ends with a request and an owner", ends_with_a_next_step),
        ("is the right length", within_length(90, 300)),
    ],
}

# Printed after the mechanical rules pass. Scored by the learner, because none
# of it can be checked here and pretending otherwise would be worse than saying
# so.
TONE_CHECKLIST = """
A linter cannot tell whether a sentence sounds like a person wrote it, so the
part that matters most is yours to judge. Read it back once, out loud, and
answer honestly:

  1. Would you send this to somebody who is already annoyed with you?
  2. Does it apologize for the right thing, once, without grovelling?
  3. Is every sentence something you could defend if the customer forwarded it
     to their own engineers?
  4. Does it say what you do not yet know, rather than quietly leaving it out?
  5. If you read only the first and last sentence, do you still know what
     happened and what happens next?

Nothing here is graded. A message that passes every rule above and fails these
is a message you would not want to receive.
"""


def grade(rubric: str, draft_path: Path, evidence_path: Path) -> int:
    if rubric not in RUBRICS:
        print(f"rubric: unknown rubric {rubric!r}", file=sys.stderr)
        return 2
    if not draft_path.is_file():
        print(f"rubric: no draft at {draft_path}", file=sys.stderr)
        return 2

    draft = draft_path.read_text()
    # Refuse rather than grading against nothing.
    #
    # Four of the six rules open with "no evidence section, so nothing to check
    # here", which is right when a particular section is legitimately absent and
    # very wrong when the whole file is. With no evidence at all the rubric
    # quietly drops to checking length and vocabulary, and a draft that cites no
    # figure, rules nothing out and never names the workflow scores six of six.
    # An audit demonstrated exactly that.
    if not evidence_path.is_file():
        print(
            f"rubric: no evidence at {evidence_path}, so this draft cannot be "
            "graded.\n"
            "        Most of the rules compare the draft against it, and "
            "without it they\n"
            "        would all pass by having nothing to disagree with.",
            file=sys.stderr,
        )
        return 2
    evidence = sections(evidence_path.read_text())

    failures = []
    for description, rule in RUBRICS[rubric]:
        problem = rule(draft, evidence)
        if problem is None:
            print(f"PASS  {description}")
        else:
            print(f"FAIL  {description}")
            print(f"      {problem}")
            failures.append(description)
        print()

    total = len(RUBRICS[rubric])
    if failures:
        print(f"{len(failures)} of {total} checks failed.")
        return 1

    print(f"{total} of {total} checks passed.")
    print(TONE_CHECKLIST)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rubric", required=True, choices=sorted(RUBRICS))
    parser.add_argument("--draft", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    return grade(args.rubric, args.draft, args.evidence)


if __name__ == "__main__":
    raise SystemExit(main())
