#!/usr/bin/env bash
# Grades the exercise by running the customer's own sync script.
source "$TSE_LIB/assert.sh"

assert "API is up and serving" \
    --run "curl -s --max-time 3 http://127.0.0.1:8101/health" \
    --contains '"status": "healthy"' \
    --expect "HTTP 200 from /health" \
    --retries 20 --delay 2

# The sync is run exactly once and its output is graded from a file. Running it
# per assertion would leave the client rate limited from the previous run, so
# the grader would be measuring its own traffic rather than the customer's.
SYNC_OUTPUT=$(mktemp)
trap 'rm -f "$SYNC_OUTPUT"' EXIT
bash "$TSE_STACK_DIR/request.sh" >"$SYNC_OUTPUT" 2>&1

assert "Every page of the nightly sync completed" \
    --run "grep -c 'HTTP 200' '$SYNC_OUTPUT' || true" \
    --equals "8" \
    --expect "all 8 pages returning HTTP 200"

assert "No page was left rejected by the rate limiter" \
    --run "grep -c 'HTTP 429' '$SYNC_OUTPUT' || true" \
    --equals "0" \
    --expect "no page ending on HTTP 429, meaning throttling was absorbed rather than ignored"

finish
