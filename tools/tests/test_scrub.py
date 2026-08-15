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
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_loader = importlib.machinery.SourceFileLoader("tse", str(ROOT / "tools" / "tse"))
_spec = importlib.util.spec_from_loader("tse", _loader)
tse = importlib.util.module_from_spec(_spec)
sys.modules["tse"] = tse
_loader.exec_module(tse)

# Shared with site/scripts/check-terminal.mjs, which asserts the same cases
# against the built page. Kept in one file so the two normalizers cannot drift
# apart while both of their test suites stay green.
FIXTURES = json.loads((ROOT / "tools" / "tests" / "fixtures" / "normalize.json").read_text())

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
    "request-id": (
        'X-Request-Id: 3fdd64a1f2ad\n  "request_id": "6c9286061d44",\n'
        "api-1  | level=info request_id=bcac353dce6c method=GET path=/health"
    ),
    "private-ip": (
        "app-1  | level=error event=database_connection_failed "
        "detail='psql: error: connection to server at \"postgres\" (172.22.0.2), "
        "port 5432 failed: FATAL'"
    ),
    "plan-estimate": (
        "Seq Scan on api_requests  (cost=0.00..7978.00 rows=7568 width=4) "
        "(actual time=0.005..14.669 rows=7500 loops=1)"
    ),
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
    "image-pull-state": "orders-api-77bc985956-bml6h   0/1   ImagePullBackOff   0   14s",
    "crash-loop-state": "orders-api-8c8575974-dkg9b   0/1   CrashLoopBackOff   3 (9s ago)   45s",
    "endpointslice-suffix": "orders-api-kdwnq   IPv4   8080   10.244.0.23,10.244.0.24   12m",
    "k8s-age": "orders-api-8c8575974-4bx5s   0/1     CrashLoopBackOff   2 (23s ago)   48s",
    "ephemeral-port": (
        "0c02ee579b5d   kindest/node:v1.36.1   Up 4 days   "
        "127.0.0.1:57702->6443/tcp   proveit-control-plane"
    ),
    # Captured on an arm64 laptop. A CI runner on amd64 produced
    # pod-template-hash=6cfff686f for the same deployment.
    "pod-template-hash": (
        "orders-api-56cb47dd7f-x9wpk   1/1   Running   0   30s   "
        "app.kubernetes.io/name=orders-api,pod-template-hash=56cb47dd7f"
    ),
    "ls-date": "-rw-r-----    1 root     reporting       78 Aug 15 14:16 credentials.conf",
    # Two builds of the networking image issue the same certificate fields over
    # a fresh key, so this block is the only thing in `openssl s_client` output
    # that moves. Measured: 28 lines differed between two independent builds
    # and 27 of them were this.
    "certificate-body": (
        "-----BEGIN CERTIFICATE-----\n"
        "MIIDBjCCAe6gAwIBAgIBCzANBgkqhkiG9w0BAQsFADAaMRgwFgYDVQQDDA9Qcm92\n"
        "ZSBJdCBMYWIgQ0EwHhcNMjUwMTAxMDAwMDAwWhcNMjUwNDAxMDAwMDAwWjASMRAw\n"
        "nRbKoPpc2pBPBw==\n"
        "-----END CERTIFICATE-----"
    ),
    # Recorded on Docker Desktop. A Linux runner produced curl: (56) for the
    # identical fault.
    "curl-accepted-then-nothing": "curl: (52) Empty reply from server",
    "unpublished-port": (
        "proveit-docker-app-1  Up 20 seconds (healthy)  8080/tcp, 127.0.0.1:8100->8081/tcp"
    ),
    # Seven attempts locally, six on a CI runner, in the same wait.
    "repeated-log-line": (
        "app-1  | ERROR: required environment variable APP_SECRET is not set\n"
        "app-1  | ERROR: required environment variable APP_SECRET is not set\n"
        "app-1  | ERROR: required environment variable APP_SECRET is not set"
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
    # The loopback address is the whole point of docker/02, so the rule that
    # tidies away Compose's bridge addresses must not touch it.
    "127.0.0.1",
    "port 5432 failed: Connection refused",
    "HTTP/1.0 503 Service Unavailable",
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
            (
                "orders-api-kdwnq   IPv4   8080   10.244.0.23,10.244.0.24   12m",
                "orders-api-hk8zx   IPv4   8080   10.244.0.46,10.244.0.45   3m2s",
            ),
        ]
        for first, second in pairs:
            with self.subTest(first[:40]):
                self.assertEqual(scrub(first), scrub(second))


class RulesDoNotOverReach(unittest.TestCase):
    """A scrubber that erases the evidence passes everything, which is worse."""

    def test_evidence_survives_into_storage(self):
        """What a learner reads is the stored form, so that is what is checked.

        Storage applies only the privacy rules. The comparison pass is allowed
        to be more aggressive, because it is answering a narrower question:
        whether two runs of the same broken system agree.
        """
        for phrase in MUST_SURVIVE:
            with self.subTest(phrase):
                self.assertIn(phrase, scrub(phrase, privacy_only=True),
                              f"scrubbing destroyed evidence: {phrase}")

    def test_comparison_treats_only_genuine_equivalents_as_equal(self):
        """The states comparison is allowed to fold together, and why.

        Each pair is the same fact caught at two moments. Anything not listed
        here has to compare unequal, or the check stops meaning anything.
        """
        equivalent = [
            ("Reason: ErrImagePull", "Reason: ImagePullBackOff"),
            ("restart=3 exit=1", "restart=19 exit=1"),
            ("Restart Count:  2", "Restart Count:  7"),
        ]
        for first, second in equivalent:
            with self.subTest(first):
                self.assertEqual(scrub(first), scrub(second))

        distinct = [
            ("Reason: OOMKilled", "Reason: Completed"),
            ("restart=3 exit=1", "restart=3 exit=0"),
            ("Seq Scan on api_requests", "Bitmap Index Scan on api_requests"),
            ("HTTP/1.1 429 Too Many Requests", "HTTP/1.1 200 OK"),
        ]
        for first, second in distinct:
            with self.subTest(first):
                self.assertNotEqual(scrub(first), scrub(second))

    def test_a_crash_loop_log_folds_on_count_but_not_on_content(self):
        """How many attempts happened is machine speed. What they said is not."""
        line = "app-1  | ERROR: required environment variable APP_SECRET is not set\n"
        self.assertEqual(scrub(line * 7), scrub(line * 6))
        other = "app-1  | ERROR: required environment variable DB_PASSWORD is not set\n"
        self.assertNotEqual(scrub(line * 7), scrub(other * 7))

    def test_repeated_lines_never_fold_two_pods_into_one(self):
        """The over-reach this rule was deliberately scoped to avoid.

        Once pod suffixes, restart counts and ages are replaced, two replicas
        scrub to byte-identical lines. A general "collapse repeated lines" rule
        would fold them together, and a deployment quietly dropping from two
        replicas to one would then compare equal.
        """
        two = (
            "orders-api-8c8575974-6n2ts   0/1   CrashLoopBackOff   3 (41s ago)   75s\n"
            "orders-api-8c8575974-krbtq   0/1   CrashLoopBackOff   3 (35s ago)   75s\n"
        )
        one = "orders-api-8c8575974-6n2ts   0/1   CrashLoopBackOff   3 (41s ago)   75s\n"
        self.assertNotEqual(scrub(two), scrub(one))

    def test_a_listing_date_folds_but_the_permissions_beside_it_do_not(self):
        """The mode and ownership are the evidence; the mtime is build noise."""
        first = "-rw-r-----    1 root     reporting       78 Aug 15 14:16 credentials.conf"
        second = "-rw-r-----    1 root     reporting       78 Sep  2 09:04 credentials.conf"
        self.assertEqual(scrub(first), scrub(second))
        for evidence in ("-rw-r-----", "root", "reporting"):
            self.assertIn(evidence, scrub(first))

    def test_a_changed_mode_still_compares_unequal(self):
        strict = "-rw-r-----    1 root     reporting       78 Aug 15 14:16 credentials.conf"
        loose = "-rw-r--r--    1 root     reporting       78 Aug 15 14:16 credentials.conf"
        self.assertNotEqual(scrub(strict), scrub(loose))

    def test_a_certificate_date_is_not_mistaken_for_a_listing_date(self):
        """Caught while recording networking/01, before it reached CI.

        `openssl x509 -dates` opens with the same month, day and clock that
        `ls -l` prints, so the listing rule swallowed the expiry that the whole
        exercise turns on. The rule now reads the seconds, which `ls` never
        prints, and this is what stops it regressing.
        """
        dates = "notBefore=Jan  1 00:00:00 2025 GMT\nnotAfter=Apr  1 00:00:00 2025 GMT"
        self.assertNotIn("<date>", scrub(dates))
        for evidence in ("2025", "notAfter", "Apr"):
            self.assertIn(evidence, scrub(dates))

    def test_a_certificate_that_expires_on_a_different_day_still_differs(self):
        """The rule above must not be so generous that a rotation looks identical."""
        expired = "notAfter=Apr  1 00:00:00 2025 GMT"
        current = "notAfter=Dec 31 23:59:59 2035 GMT"
        self.assertNotEqual(scrub(expired), scrub(current))

    def test_a_certificate_body_folds_but_everything_around_it_survives(self):
        """Two builds issue identical fields over a fresh key, and only this moves."""
        def block(body: str) -> str:
            return (
                "subject=C=US, O=Prove It Lab, CN=gateway\n"
                "-----BEGIN CERTIFICATE-----\n"
                f"{body}\n"
                "-----END CERTIFICATE-----\n"
                "notAfter=Apr  1 00:00:00 2025 GMT"
            )

        first = block("MIIDBjCCAe6gAwIBAgIBCzANBgkqhkiG9w0BAQsFADAaMRgwFgYDVQQDDA9Qcm92")
        second = block("aCMutIgKC1CyBgQwIBAgIBCzANBgkqhkiG9w0BAQsFADAaMRgwFgYDVQQDDA9Qcm")
        self.assertEqual(scrub(first), scrub(second))
        for evidence in ("CN=gateway", "notAfter=Apr", "2025"):
            self.assertIn(evidence, scrub(first))

    def test_folding_the_body_does_not_hide_a_different_certificate(self):
        """The fields are what identify it, so a changed name must still differ."""
        body = "-----BEGIN CERTIFICATE-----\nMIIDBjCCAe6gAwIBAgIBCzAN\n-----END CERTIFICATE-----"
        one_name = f"X509v3 Subject Alternative Name:\n    DNS:gateway\n{body}"
        two_names = f"X509v3 Subject Alternative Name:\n    DNS:gateway, DNS:reports\n{body}"
        self.assertNotEqual(scrub(one_name), scrub(two_names))

    def test_the_age_column_folds_even_when_labels_follow_it(self):
        """Found the hard way: a rule anchored to end of line, and a column after it.

        kubernetes/05 records `get pods --show-labels`, which puts the labels
        after the age. The comparison was reading a raw age on every run and
        passing only while two runs landed on the same second.
        """
        labels = "app.kubernetes.io/name=orders-api,pod-template-hash=5bcc9b9944"
        first = f"orders-api-8c8575974-6n2ts   0/1     Running   0          40s   {labels}"
        second = f"orders-api-8c8575974-6n2ts   0/1     Running   0          41s   {labels}"
        self.assertEqual(scrub(first), scrub(second))

    def test_the_widened_age_rule_leaves_query_plans_alone(self):
        """The lookahead now accepts a following key=value column.

        Query plans are full of key=value, so this is where an age rule would
        start eating the numbers sql/03 is entirely about.
        """
        for evidence in (
            "cost=0.00..1234.00 rows=7500 width=91",
            "Rows Removed by Filter: 292500",
            "Seq Scan on api_requests",
        ):
            with self.subTest(evidence):
                self.assertEqual(scrub(evidence), evidence)

    def test_the_two_ways_a_dead_target_is_reported_fold_together(self):
        """Docker Desktop closes the connection, Linux resets it."""
        self.assertEqual(
            scrub("curl: (52) Empty reply from server"),
            scrub("curl: (56) Recv failure: Connection reset by peer"),
        )

    def test_a_refused_connection_stays_distinct_from_an_accepted_one(self):
        """The fork mixed/01 turns on, and the one thing this must never fold.

        Refused means nothing accepted the connection. The other two mean
        something accepted it and gave nothing back, which points at an entirely
        different layer.
        """
        refused = "curl: (7) Failed to connect to 127.0.0.1 port 8100: Connection refused"
        for accepted in (
            "curl: (52) Empty reply from server",
            "curl: (56) Recv failure: Connection reset by peer",
        ):
            with self.subTest(accepted):
                self.assertNotEqual(scrub(refused), scrub(accepted))

    def test_an_unpublished_port_folds_only_when_a_published_one_follows(self):
        desktop = "proveit-docker-app-1  Up 20 seconds (healthy)  127.0.0.1:8100->8081/tcp"
        linux = (
            "proveit-docker-app-1  Up 20 seconds (healthy)  8080/tcp, 127.0.0.1:8100->8081/tcp"
        )
        self.assertEqual(scrub(desktop), scrub(linux))
        # A service that publishes nothing still shows what it exposes, because
        # that absence is sometimes the evidence.
        exposed_only = "proveit-docker-postgres-1  Up 22 seconds (healthy)  5432/tcp"
        self.assertIn("5432/tcp", scrub(exposed_only))

    def test_a_request_id_folds_in_all_three_forms_it_is_printed_in(self):
        """One value, three renderings, and only one of them was covered.

        The header and JSON forms were there from the start. The key=value form
        in the service's own logs was not, and it went unnoticed until a new
        exercise recorded a command that printed those logs.
        """
        for form in ('"request_id": "{}"', "X-Request-Id: {}", "request_id={}"):
            with self.subTest(form):
                self.assertEqual(
                    scrub(form.format("bcac353dce6c")),
                    scrub(form.format("4bb8567e8c77")),
                )

    def test_the_request_id_rule_leaves_neighboring_fields_alone(self):
        line = "level=info request_id=bcac353dce6c method=GET path=/health status=200"
        scrubbed = scrub(line)
        for survives in ("method=GET", "path=/health", "status=200"):
            self.assertIn(survives, scrubbed)

    def test_a_tagged_request_id_folds_the_same_as_a_bare_one(self):
        """The observability services tag what they generate, and the rule missed it.

        `req-` at the edge and `gen-` in the renderer both put a leading letter
        where the rule wanted hex, so it matched nothing and every recorded log
        line carried an id that moved on the next run.
        """
        for prefix in ("req-", "gen-", ""):
            with self.subTest(prefix or "bare"):
                self.assertEqual(
                    scrub(f"request_id={prefix}bcac353dce6c event=x"),
                    scrub(f"request_id={prefix}4bb8567e8c77 event=x"),
                )

    def test_a_reference_a_customer_quotes_is_left_alone(self):
        """observability/02 records a customer quoting theirs, so it must survive.

        Folding the identifier that an exercise is entirely about would leave
        its page showing a placeholder where the evidence should be. A
        reference carrying a letter outside hex is not matched, which is what
        keeps the generated ids foldable and this one readable.
        """
        line = "request_id=req-nw7k2p9x4m31 event=report_failed tenant=northwind"
        self.assertEqual(scrub(line), line)
        self.assertIn("req-nw7k2p9x4m31", scrub(line))

    def test_both_wordings_of_a_failing_pull_fold_together(self):
        """kubelet's two messages for one stuck pull, from `kubectl logs`.

        Which one a command catches depends only on where in the backoff it
        ran. CI caught the opposite one to the laptop that recorded it.
        """
        stem = 'Error from server (BadRequest): container "app" is waiting to start: '
        self.assertEqual(
            scrub(f"{stem}trying and failing to pull image"),
            scrub(f"{stem}image can't be pulled"),
        )

    def test_the_pull_failure_rule_leaves_the_event_message_alone(self):
        """"Failed to pull image" is a keep marker for kubernetes/01."""
        message = 'Failed to pull image "orders-api:3.12-alpne": not found'
        self.assertIn("Failed to pull image", scrub(message))
        self.assertIn("not found", scrub(message))

    def test_a_template_hash_folds_but_the_rest_of_the_labels_do_not(self):
        labels = "app.kubernetes.io/name=orders-api,pod-template-hash="
        self.assertEqual(scrub(f"{labels}56cb47dd7f"), scrub(f"{labels}6cfff686f"))
        self.assertNotEqual(
            scrub("app.kubernetes.io/name=orders-api,pod-template-hash=56cb47dd7f"),
            scrub("app.kubernetes.io/name=payments-api,pod-template-hash=56cb47dd7f"),
        )

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

    def test_measured_rows_survive_while_estimates_do_not(self):
        """A plan line carries both a guess and a measurement, and they differ.

        `rows=7568` in the cost parenthetical is what the planner expected and
        it drifts with table statistics. `rows=7500` in the actual parenthetical
        is what the query really read, and the writeup quotes it. Only the
        second one is evidence, so only the second one is preserved.
        """
        line = ("Seq Scan on api_requests  (cost=0.00..7978.00 rows=7568 width=4) "
                "(actual time=0.005..14.669 rows=7500 loops=1)")
        scrubbed = scrub(line)
        self.assertIn("Seq Scan on api_requests", scrubbed)
        self.assertIn("rows=7500", scrubbed)
        self.assertIn("loops=1", scrubbed)
        self.assertIn("actual time=<t>..<t>", scrubbed)
        self.assertNotIn("rows=7568", scrubbed)
        self.assertIn("(cost=<cost> rows=<est> width=<w>)", scrubbed)

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

    def test_every_fixture_case_normalizes_as_recorded(self):
        """The shared contract between this normalizer and the site's.

        The terminal on the exercise page has to collapse a typed command the
        same way this does, or a learner types something reasonable and gets
        told it was never recorded. These cases are asserted twice: here, and
        against the built page by site/scripts/check-terminal.mjs. One file, so
        the two cannot quietly disagree about what they are implementing.
        """
        for case in FIXTURES:
            with self.subTest(case["why"]):
                self.assertEqual(tse.normalize_command(case["typed"]), case["normalized"])

    def test_the_fixture_covers_more_than_the_trivial_case(self):
        """A fixture list of identity cases proves nothing about either side."""
        changed = [case for case in FIXTURES if case["typed"] != case["normalized"]]
        self.assertGreaterEqual(len(changed), 5)


class MatchKeys(unittest.TestCase):
    """What the site looks a typed command up against."""

    def test_keys_cover_the_command_and_every_alias(self):
        keys = tse.match_keys("docker  ps -a", ["docker ps --all", "docker ps -a"])
        self.assertEqual(keys, ["docker ps --all", "docker ps -a"])

    def test_keys_are_deduplicated(self):
        """An alias that normalizes onto the command is not a second key."""
        self.assertEqual(tse.match_keys("docker ps -a", ["docker   ps -a"]), ["docker ps -a"])

    def test_blank_aliases_are_dropped(self):
        self.assertEqual(tse.match_keys("docker ps", ["", "   "]), ["docker ps"])

    def test_curls_two_statuses_for_one_fault_agree(self):
        """The exit status carries the same information as the message.

        Folding one without the other left the comparison failing on the half
        that was missed, which is how this was found.
        """
        curl = "curl -sS --max-time 5 http://127.0.0.1:8100/customers"
        self.assertTrue(tse.exits_agree(curl, 52, 56))
        self.assertTrue(tse.exits_agree(curl, 56, 52))

    def test_a_refused_connection_still_disagrees(self):
        curl = "curl -sS http://127.0.0.1:8100/customers"
        self.assertFalse(tse.exits_agree(curl, 7, 52))
        self.assertFalse(tse.exits_agree(curl, 0, 52))

    def test_those_statuses_mean_nothing_special_to_other_commands(self):
        self.assertFalse(tse.exits_agree("bash labs/api/_stack/request.sh", 52, 56))
        self.assertTrue(tse.exits_agree("docker ps", 0, 0))

    def test_an_alias_added_without_re_recording_is_caught(self):
        """The one drift nothing else would notice.

        Adding an alias to commands.txt changes no output and no exit code, so
        every other comparison passes. What it changes is the lookup key, and
        the symptom is a command that silently does nothing on the page.
        """
        entry = {"command": "docker ps -a", "output": "CONTAINER ID", "exit": 0}
        recorded = {"entries": [{**entry, "aliases": [], "match": ["docker ps -a"]}]}
        fresh = [{**entry, "aliases": ["docker ps --all"],
                  "match": ["docker ps --all", "docker ps -a"]}]

        drift = tse.compare_transcript(recorded, fresh)
        self.assertEqual(len(drift), 1)
        self.assertIn("spellings in commands.txt changed", drift[0])

    def test_an_unchanged_recording_reports_no_drift(self):
        entry = {"command": "docker ps -a", "aliases": ["docker ps --all"],
                 "match": ["docker ps --all", "docker ps -a"],
                 "output": "CONTAINER ID", "exit": 0}
        self.assertEqual(tse.compare_transcript({"entries": [entry]}, [dict(entry)]), [])

    def test_every_recorded_entry_carries_derivable_keys(self):
        """A stored key that does not follow from its own command is stale.

        The keys were backfilled into the existing recordings rather than
        re-recorded, since they depend only on fields those files already held.
        This is what makes that safe to have done.
        """
        for path in sorted((ROOT / "labs").glob("*/*/transcript.json")):
            for entry in json.loads(path.read_text())["entries"]:
                with self.subTest(f"{path.parent.name}:{entry['command'][:40]}"):
                    self.assertEqual(
                        entry.get("match"),
                        tse.match_keys(entry["command"], entry["aliases"]),
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
