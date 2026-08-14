#!/usr/bin/env bash
# Grades the exercise by running the learner's query against the real database.
source "$TSE_LIB/assert.sh"

# shellcheck disable=SC2034  # expanded by assert's eval, which shellcheck cannot follow
REPORT="SELECT count(*), avg(duration_ms)::int FROM api_requests WHERE customer_id = 7 AND requested_at >= TIMESTAMPTZ '2026-07-01' AND requested_at < TIMESTAMPTZ '2026-07-08';"

assert "Database is up and seeded" \
    --run "bash \$TSE_STACK_DIR/ready.sh" \
    --equals "40" \
    --expect "40 customers in the support database" \
    --retries 30 --delay 3

assert "Report still returns the right answer" \
    --run "bash \$TSE_STACK_DIR/run.sh" \
    --contains "7500|191" \
    --expect "7500 requests averaging 191ms for that account and week" \
    --retries 3 --delay 2

# Graded on the plan, not the clock. At this size a full scan finishes in
# milliseconds, so a wall-clock threshold would be both flaky and misleading.
# The plan is the honest signal: a scan grows with the table and a lookup does
# not, which is exactly what the customer felt as their data grew.
assert "The database no longer reads the whole table to answer it" \
    --run "bash \$TSE_STACK_DIR/explain.sh \"\$REPORT\"" \
    --not-contains "Seq Scan on api_requests" \
    --expect "a plan with no sequential scan over api_requests" \
    --retries 3 --delay 2

finish
