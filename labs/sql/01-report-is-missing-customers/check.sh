#!/usr/bin/env bash
# Grades the exercise by running the learner's query against the real database.
source "$TSE_LIB/assert.sh"

assert "Database is up and seeded" \
    --run "bash \$TSE_STACK_DIR/ready.sh" \
    --equals "40" \
    --expect "40 customers in the support database" \
    --retries 30 --delay 3

assert "Report counts every customer, including those without a workspace" \
    --run "bash \$TSE_STACK_DIR/run.sh" \
    --contains 'starter|12' \
    --expect 'starter|12 in the plan mix, matching the 12 starter customers that exist' \
    --retries 3 --delay 2

finish
