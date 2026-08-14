#!/usr/bin/env bash
# Grades the exercise by gathering the same evidence a support engineer would.
source "$TSE_LIB/assert.sh"

COMPOSE="docker compose -f $TSE_STACK_DIR/compose.yaml -f $TSE_STACK_DIR/compose.override.yaml"

# Deliberately not asserting on "is it running". A crash-looping container is
# intermittently running, and a freshly created one has not failed yet, so both
# are true at the wrong moment. Health status is computed over time by the
# healthcheck, which makes it the one state here that cannot be caught lying.
assert "Application container reaches a healthy state" \
    --run "docker inspect --format '{{.State.Health.Status}}' \"\$($COMPOSE ps -q app 2>/dev/null)\" 2>/dev/null || echo unavailable" \
    --equals "healthy" \
    --expect "the container healthcheck reporting 'healthy' rather than 'starting' or unavailable" \
    --retries 20 --delay 2

assert "Application reports itself healthy" \
    --run "curl -s --max-time 3 http://127.0.0.1:8100/health" \
    --contains '"status": "healthy"' \
    --expect 'HTTP 200 with {"status": "healthy"} from /health' \
    --retries 15 --delay 2

assert "Customer workflow returns their data" \
    --run "curl -s --max-time 3 http://127.0.0.1:8100/customers" \
    --contains '"customer_count": 10' \
    --expect '{"status": "ok", "customer_count": 10} from /customers' \
    --retries 10 --delay 2

assert "Application no longer logs a startup configuration error" \
    --run "$COMPOSE logs --tail 50 app 2>&1 | grep -c 'is not set' || true" \
    --equals "0" \
    --expect "no 'required environment variable ... is not set' lines in recent logs"

finish
