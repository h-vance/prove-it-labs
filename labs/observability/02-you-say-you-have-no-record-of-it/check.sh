#!/usr/bin/env bash
# Grades the exercise by gathering the same evidence a support engineer would.
source "$TSE_LIB/assert.sh"

COMPOSE="docker compose -f $TSE_STACK_DIR/compose.yaml -f $TSE_STACK_DIR/compose.override.yaml"

# A fresh reference per run, so the counts below are exactly one each and do not
# climb every time the exercise is graded. `assert` evaluates its command in
# this shell, so a function is callable.
trace_one_request() {
    local id="probe-$$-${RANDOM}"
    curl -s -o /dev/null -H "X-Request-Id: $id" \
        'http://127.0.0.1:8102/v1/reports?tenant=northwind&rows=50000'
    printf 'api=%s renderer=%s\n' \
        "$($COMPOSE logs api 2>/dev/null | grep -c -- "$id")" \
        "$($COMPOSE logs downstream 2>/dev/null | grep -c -- "$id")"
}

# Both halves matter and asserting only the second would pass while the first
# had quietly broken. The point is not that the renderer logs something, it is
# that both services log the *same* reference, which is the only thing that
# makes a search for it work.
assert "A reference the caller supplies is recorded by both services" \
    --run "trace_one_request" \
    --equals "api=1 renderer=1" \
    --expect "the caller's own reference appearing once in each service's log, not a fresh one per service" \
    --retries 10 --delay 2

# The failure itself is a separate ticket and must still be there. A learner
# who made the report succeed has removed the evidence rather than made it
# findable, and the customer would then have nothing to quote at all.
#
# Matched as a pattern rather than with --not-contains "0", which would have
# rejected a count of 10 for containing a zero.
assert "The failure the customer is chasing is still recorded, not made to disappear" \
    --run "$COMPOSE logs downstream 2>/dev/null | grep -c 'event=render_failed'" \
    --matches '^[1-9][0-9]*$' \
    --expect "the renderer still logging the failed report, since this ticket is about finding it rather than fixing it"

finish
