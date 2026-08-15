#!/usr/bin/env bash
# Grades the written escalation against the rules a machine can honestly check.
source "$TSE_LIB/assert.sh"

# A different rubric to the one communication/01 uses, on purpose. The module
# is parameterized rather than hard-coded around a single document, and this is
# what proves it: the rule that fails a customer update for naming internal
# machinery has no counterpart here, and the rule that fails an escalation for
# leaving it out has no counterpart there.
assert "The escalation meets every rule that can be checked" \
    --run "python3 \$TSE_LIB/rubric.py --rubric escalation --draft \$TSE_STACK_DIR/escalation.md --evidence \$TSE_STACK_DIR/evidence.md" \
    --contains "checks passed" \
    --expect "every rubric rule passing, with the tone checklist printed"

finish
