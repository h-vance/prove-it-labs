#!/usr/bin/env bash
# Grades the exercise by gathering the same evidence a support engineer would.
source "$TSE_LIB/assert.sh"

COMPOSE="docker compose -f $TSE_STACK_DIR/compose.yaml -f $TSE_STACK_DIR/compose.override.yaml"

assert "Application container reaches a healthy state" \
    --run "docker inspect --format '{{.State.Health.Status}}' \"\$($COMPOSE ps -q app 2>/dev/null)\" 2>/dev/null || echo unavailable" \
    --equals "healthy" \
    --expect "the container healthcheck reporting 'healthy'" \
    --retries 20 --delay 2

assert "Customer workflow returns their data" \
    --run "curl -s --max-time 3 http://127.0.0.1:8100/customers" \
    --contains '"customer_count": 10' \
    --expect '{"status": "ok", "customer_count": 10} from /customers' \
    --retries 15 --delay 2

# Asserting on the workflow alone would also pass if the app silently served
# stale or empty data, so this pins the specific failure mode to zero.
assert "Application is no longer failing to reach its database" \
    --run "$COMPOSE logs --tail 50 app 2>&1 | grep -c 'database_connection_failed' || true" \
    --equals "0" \
    --expect "no database_connection_failed events in recent logs"

finish
