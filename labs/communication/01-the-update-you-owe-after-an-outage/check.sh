#!/usr/bin/env bash
# Grades the written update against the rules a machine can honestly check.
source "$TSE_LIB/assert.sh"

# The rubric prints its own per-rule verdict, which is more useful here than a
# single pass or fail: a message can be right about the facts and still fail on
# not committing anyone to anything, and the learner needs to know which.
assert "The customer update meets every rule that can be checked" \
    --run "python3 \$TSE_LIB/rubric.py --rubric customer --draft \$TSE_STACK_DIR/customer-update.md --evidence \$TSE_STACK_DIR/evidence.md" \
    --contains "checks passed" \
    --expect "every rubric rule passing, with the tone checklist printed"

finish
