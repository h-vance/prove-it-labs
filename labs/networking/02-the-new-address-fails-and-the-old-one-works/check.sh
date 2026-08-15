#!/usr/bin/env bash
# Grades the exercise by gathering the same evidence a support engineer would.
source "$TSE_LIB/assert.sh"

COMPOSE="docker compose -f $TSE_STACK_DIR/compose.yaml -f $TSE_STACK_DIR/compose.override.yaml"

# The address is pinned here rather than read from the client's own
# configuration, and that is not a detail. Reading it back meant the grader
# asked "does the upload work" instead of "does the new address work", so
# pointing the customer at the old address and changing nothing else passed
# both checks. That was tried before this line was written, and it passed.
assert "The upload works on the address the customer was migrated to" \
    --run "$COMPOSE exec -T client sh -c 'GATEWAY_URL=https://reports:8443 /app/upload.sh'" \
    --contains '"status": "accepted"' \
    --expect 'the gateway accepting the export on the reports address' \
    --retries 10 --delay 2

# The obvious fix is to reissue for the new name, and the obvious way to get it
# wrong is to reissue for the new name only. That would pass the assertion
# above and break every caller still on the old address, which is most of them.
# A fix that moves a failure is not a fix, so both names are checked.
assert "The address it already worked on still works" \
    --run "$COMPOSE exec -T client sh -c 'GATEWAY_URL=https://gateway:8443 /app/upload.sh'" \
    --contains '"status": "accepted"' \
    --expect "the gateway address continuing to work, rather than the failure moving from one name to the other"

finish
