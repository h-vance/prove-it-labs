#!/usr/bin/env bash
# Grades the exercise by gathering the same evidence a support engineer would.
source "$TSE_LIB/assert.sh"

COMPOSE="docker compose -f $TSE_STACK_DIR/compose.yaml -f $TSE_STACK_DIR/compose.override.yaml"

# Pinned here rather than read from the client's configuration, for the reason
# written into the previous exercise: reading it back asks "does the upload
# work" instead of "does the customer's address work", and pointing them at the
# other one then passes.
assert "The upload works on the address the customer has been on since May" \
    --run "$COMPOSE exec -T client sh -c 'GATEWAY_URL=https://reports:8443 /app/upload.sh'" \
    --contains '"status": "accepted"' \
    --expect 'the gateway accepting the export on the reports address' \
    --retries 10 --delay 2

assert "The address that was already working still works" \
    --run "$COMPOSE exec -T client sh -c 'GATEWAY_URL=https://gateway:8443 /app/upload.sh'" \
    --contains '"status": "accepted"' \
    --expect "the gateway address continuing to work, rather than the failure moving from one name to the other"

# A third assertion was written and removed, which is worth recording here
# rather than losing.
#
# It read `getent hosts reports` back and required the gateway's own address,
# meaning to catch two wrong fixes: pointing the record at something that
# merely answers, and deleting the record so the name stops resolving at all.
# Both were tried. Both fail the first assertion already, because neither
# delivers an upload, and the third never once failed on its own.
#
# What it did not catch is the fix this exercise actually warns about: a record
# holding the gateway's literal address instead of its name. That was tried
# too, and it passed all three, because today it resolves to exactly the same
# place. It goes wrong on the next rebuild, which is a thing no check run now
# can observe. It is taught in the solution and it is deliberately not graded,
# rather than graded by an assertion that cannot tell the two apart.

finish
