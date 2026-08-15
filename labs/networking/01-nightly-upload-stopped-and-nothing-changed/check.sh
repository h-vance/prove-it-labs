#!/usr/bin/env bash
# Grades the exercise by gathering the same evidence a support engineer would.
source "$TSE_LIB/assert.sh"

COMPOSE="docker compose -f $TSE_STACK_DIR/compose.yaml -f $TSE_STACK_DIR/compose.override.yaml"

assert "The customer's nightly upload completes" \
    --run "$COMPOSE exec -T client /app/upload.sh" \
    --contains '"status": "accepted"' \
    --expect 'the gateway accepting the export rather than the client refusing to connect' \
    --retries 10 --delay 2

# The fast way to clear this error is to stop the client checking, and that is
# why the second assertion does not go anywhere near the client. It asks the
# running gateway what it is serving and reads the dates off it, so a fix that
# works by looking away still fails here.
assert "The certificate the gateway serves is in date" \
    --run "$COMPOSE exec -T client sh -c 'echo | openssl s_client -connect gateway:8443 -servername gateway 2>/dev/null | openssl x509 -noout -checkend 0'" \
    --contains "Certificate will not expire" \
    --expect "the served certificate still being valid, checked against the gateway rather than against the client"

finish
