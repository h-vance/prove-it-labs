#!/usr/bin/env python3
"""Tests for the scrubber that lets recorded output be compared to a real run.

Every sample here was captured from an actual lab, not written to fit the
regex. That matters: a scrubber tested against invented output proves only that
the author can invent output matching their own pattern.

Two directions are checked for every rule, because both failures are real and
only one of them is loud:

  - The rule fires on genuine output. A rule that stops matching makes the
    comparison fail at random, which gets the check switched off.
  - The rule leaves the evidence alone. A rule broad enough to erase
    "OOMKilled" makes the comparison pass no matter what happened, which is
    worse, because nothing ever complains.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_loader = importlib.machinery.SourceFileLoader("tse", str(ROOT / "tools" / "tse"))
_spec = importlib.util.spec_from_loader("tse", _loader)
tse = importlib.util.module_from_spec(_spec)
sys.modules["tse"] = tse
_loader.exec_module(tse)

scrub = tse.scrub
rules_that_fire = tse.rules_that_fire

# Real captured output, one sample per rule. Keyed by rule name so a rule added
# without a sample fails the meta-test at the bottom of this file.
SAMPLES: dict[str, str] = {
    "sha256": "#10 exporting manifest sha256:29a30554bb30befe34078b083cb91056608997b9a5 done",
    "digest": "Digest: " + "a" * 64,
    "container-id": (
        "2edceae0a95a   proveit-docker-app   \"python /app/app.py\"     "
        "12 seconds ago   Restarting (1) 1 second ago              proveit-docker-app-1"
    ),
    "relative-age": "779e4abd9f39   postgres:16-alpine   ...   11 seconds ago   Up 10 seconds",
    "uptime": "a070a8d795f8   postgres:16-alpine   13 seconds ago   Up 12 seconds (healthy)",
    "iso-timestamp": "requested_at >= '2026-07-01 00:00:00+00'::timestamp with time zone",
    "rfc1123-timestamp": "      Started:      Fri, 14 Aug 2026 14:42:00 -0400",
    "plan-node-time": (
        "Aggregate  (cost=8015.84..8015.86 rows=1 width=12) "
        "(actual time=14.940..14.940 rows=1 loops=1)"
    ),
    "plan-total-time": "Execution Time: 14.965 ms",
    "plan-buffers": "  Buffers: shared hit=2728",
    "restart-count": "/proveit-docker-app-1 restart=7 exit=1",
    "pod-suffix": "orders-api-8c8575974-4bx5s   0/1     CrashLoopBackOff   2 (23s ago)   48s",
    "k8s-restarts": "orders-api-8c8575974-4bx5s   0/1     CrashLoopBackOff   2 (23s ago)   48s",
    "k8s-restart-count": "    Restart Count:  2",
    "k8s-age": "orders-api-8c8575974-4bx5s   0/1     CrashLoopBackOff   2 (23s ago)   48s",
    "ephemeral-port": (
        "0c02ee579b5d   kindest/node:v1.36.1   Up 4 days   "
        "127.0.0.1:57702->6443/tcp   proveit-control-plane"
    ),
    "column-padding": "CONTAINER ID   IMAGE                COMMAND                  CREATED",
}

# Evidence that has to survive scrubbing. These are the strings the exercises
# are actually about, and the writeups quote them by name.
#
# Written with single spaces because collapsing column padding is deliberate:
# `Exit Code:    137` and `Exit Code: 137` are the same claim, and only the
# second one compares equal across two runs with different column widths.
MUST_SURVIVE = [
    "OOMKilled",
    "Exit Code: 137",
    "Seq Scan on api_requests",
    "Rows Removed by Filter: 292500",
    "rows=7500",
    "CrashLoopBackOff",
    "ERROR: required environment variable APP_SECRET is not set",
    "CreateContainerConfigError",
    "ImagePullBackOff",
    "HTTP/1.1 429 Too Many Requests",
    "RateLimit-Remaining: 0",
    "Retry-After: 11",
    "insufficient_scope",
    "api_key_revoked",
    "route_not_found",
    "7500|191",
    "exit=1",
    "0/1",
]


class RulesFire(unittest.TestCase):
    """Each rule matches the real output it was written for."""

    def test_every_rule_fires_on_its_sample(self):
        for name, sample in SAMPLES.items():
            with self.subTest(name):
                self.assertIn(name, rules_that_fire(sample),
                              f"the {name} rule no longer matches real output")

    def test_scrubbing_actually_changes_volatile_output(self):
        for name, sample in SAMPLES.items():
            with self.subTest(name):
                self.assertNotEqual(scrub(sample), sample,
                                    f"{name}: scrubbing left the sample untouched")

    def test_two_runs_of_the_same_command_scrub_alike(self):
        """The point of the whole exercise: same system, different instant."""
        pairs = [
            (
                "2edceae0a95a   proveit-docker-app   12 seconds ago   "
                "Restarting (1) 1 second ago   proveit-docker-app-1",
                "ba6fff415e65   proveit-docker-app   17 seconds ago   "
                "Restarting (1) Less than a second ago   proveit-docker-app-1",
            ),
            (
                "orders-api-8c8575974-4bx5s   0/1   CrashLoopBackOff   2 (23s ago)   48s",
                "orders-api-7d4f8b6c9-qw86v   0/1   CrashLoopBackOff   5 (1m12s ago)   3m2s",
            ),
            (
                "  Buffers: shared read=2728\nExecution Time: 17.385 ms",
                "  Buffers: shared hit=2728\nExecution Time: 14.965 ms",
            ),
        ]
        for first, second in pairs:
            with self.subTest(first[:40]):
                self.assertEqual(scrub(first), scrub(second))


class RulesDoNotOverReach(unittest.TestCase):
    """A scrubber that erases the evidence passes everything, which is worse."""

    def test_evidence_survives(self):
        for phrase in MUST_SURVIVE:
            with self.subTest(phrase):
                self.assertIn(phrase, scrub(phrase),
                              f"scrubbing destroyed evidence: {phrase}")

    def test_evidence_survives_in_context(self):
        """The same strings, inside output that does trigger rules."""
        block = (
            "orders-api-8c8575974-4bx5s   0/1   CrashLoopBackOff   2 (23s ago)   48s\n"
            "    Last State:     Terminated\n"
            "      Reason:       OOMKilled\n"
            "      Exit Code:    137\n"
            "      Started:      Fri, 14 Aug 2026 14:42:00 -0400\n"
            "    Restart Count:  2\n"
        )
        scrubbed = scrub(block)
        self.assertIn("OOMKilled", scrubbed)
        self.assertIn("Exit Code: 137", scrubbed)
        self.assertIn("Terminated", scrubbed)
        self.assertIn("<timestamp>", scrubbed)

    def test_a_meaningful_duration_is_not_mistaken_for_noise(self):
        """191 is the answer to sql/03, not a timing to be tidied away."""
        self.assertIn("7500|191", scrub("count|avg\n7500|191"))

    def test_leading_indentation_survives_padding_collapse(self):
        """Column padding is collapsed. Structure in YAML and JSON is not."""
        yaml = 'services:\n  app:\n    environment:\n      APP_SECRET: ""\n'
        self.assertEqual(scrub(yaml), yaml)

    def test_row_counts_beside_scrubbed_timings_are_left_alone(self):
        line = ("Seq Scan on api_requests  (cost=0.00..7978.00 rows=7568 width=4) "
                "(actual time=0.005..14.669 rows=7500 loops=1)")
        scrubbed = scrub(line)
        self.assertIn("rows=7500", scrubbed)
        self.assertIn("rows=7568", scrubbed)
        self.assertIn("loops=1", scrubbed)
        self.assertIn("actual time=<t>..<t>", scrubbed)

    def test_scrubbing_is_stable(self):
        """Scrubbing an already scrubbed string changes nothing further."""
        for sample in SAMPLES.values():
            once = scrub(sample)
            with self.subTest(sample[:40]):
                self.assertEqual(scrub(once), once)


class EveryRuleIsTested(unittest.TestCase):
    def test_no_rule_lacks_a_real_sample(self):
        named = {name for name, _, _ in tse.SCRUB_RULES}
        untested = named - set(SAMPLES)
        self.assertEqual(
            untested, set(),
            f"these rules have no captured sample: {sorted(untested)}. "
            f"Capture real output rather than writing one to fit the pattern.",
        )

    def test_no_sample_is_for_a_rule_that_no_longer_exists(self):
        named = {name for name, _, _ in tse.SCRUB_RULES}
        stale = set(SAMPLES) - named
        self.assertEqual(stale, set(), f"samples for removed rules: {sorted(stale)}")


class CommandParsing(unittest.TestCase):
    def test_blocks_annotations_and_multiline(self):
        parsed = tse.parse_commands(
            "# keep: OOMKilled, Exit Code: 137\n"
            "# alias: k get pods\n"
            "# wait: 5\n"
            "kubectl -n tse-training get pods\n"
            "---\n"
            "# just a comment\n"
            "docker compose \\\n"
            "    logs app\n"
        )
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["keep"], ["OOMKilled", "Exit Code: 137"])
        self.assertEqual(parsed[0]["aliases"], ["k get pods"])
        self.assertEqual(parsed[0]["wait"], 5)
        self.assertEqual(parsed[0]["command"], "kubectl -n tse-training get pods")
        self.assertIn("\\\n", parsed[1]["command"])
        self.assertEqual(parsed[1]["keep"], [])

    def test_normalization_joins_what_a_learner_pastes(self):
        """A command copied across three lines is the same command."""
        multiline = "docker compose -f a.yaml \\\n    -f b.yaml \\\n    logs --tail 20 app"
        single = "docker compose -f a.yaml -f b.yaml logs --tail 20 app"
        self.assertEqual(tse.normalize_command(multiline), tse.normalize_command(single))

    def test_normalization_preserves_case(self):
        self.assertEqual(tse.normalize_command("kubectl get PODS"), "kubectl get PODS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
