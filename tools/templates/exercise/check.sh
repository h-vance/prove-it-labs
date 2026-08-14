#!/usr/bin/env bash
# Grades the exercise by gathering the same evidence a support engineer would.
source "$TSE_LIB/assert.sh"

# Every assert prints the command it ran and the output it evaluated. Write
# assertions against the customer's workflow, not against the implementation
# detail you happen to have broken.

assert "TODO what this proves, phrased as a fact about the system" \
    --run "TODO the command" \
    --contains "TODO" \
    --expect "TODO what a passing result looks like, in plain English" \
    --retries 10 --delay 2

finish
