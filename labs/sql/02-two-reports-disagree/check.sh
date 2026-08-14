#!/usr/bin/env bash
# Grades the exercise by running the learner's query against the real database.
source "$TSE_LIB/assert.sh"

assert "Database is up and seeded" \
    --run "bash \$TSE_STACK_DIR/ready.sh" \
    --equals "40" \
    --expect "40 customers in the support database" \
    --retries 30 --delay 3

assert "Report counts customers rather than result rows" \
    --run "bash \$TSE_STACK_DIR/run.sh" \
    --contains 'enterprise|12' \
    --expect 'enterprise|12, matching the 12 enterprise customers rather than their user rows' \
    --retries 3 --delay 2

finish
