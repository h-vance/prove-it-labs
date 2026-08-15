#!/usr/bin/env bash
# Grades the exercise by gathering the same evidence a support engineer would.
source "$TSE_LIB/assert.sh"

COMPOSE="docker compose -f $TSE_STACK_DIR/compose.yaml -f $TSE_STACK_DIR/compose.override.yaml"

assert "The daily report submits" \
    --run "$COMPOSE exec -T worker python3 /app/reporter.py" \
    --contains '"status": "ok"' \
    --expect 'the reporter reporting {"status": "ok"} rather than a permission failure' \
    --retries 10 --delay 2

# The lazy fix for a permission problem is to run as a more powerful account.
# It works, it passes the assertion above, and it is how a hardening pass gets
# quietly undone. This is the guard against solving it that way.
assert "The service still runs as the unprivileged account" \
    --run "$COMPOSE exec -T worker id -u" \
    --equals "1000" \
    --expect "uid 1000, not root"

finish
