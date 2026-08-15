#!/usr/bin/env bash
# Grades the exercise by gathering the same evidence a support engineer would.
source "$TSE_LIB/assert.sh"

COMPOSE="docker compose -f $TSE_STACK_DIR/compose.yaml -f $TSE_STACK_DIR/compose.override.yaml"

# This one passes in the broken state too, and that is the point of printing
# it. The customer was told the deploy came up healthy, and they were told the
# truth. Showing it passing while the workflow below fails is the whole lesson:
# a health check runs inside the container and answers a narrower question than
# the customer asked.
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

# Pins the specific failure. Without this, publishing the port correctly and
# breaking something else in a way that still returns customers would pass.
assert "Published address targets the port the application listens on" \
    --run "docker ps --filter 'label=com.docker.compose.service=app' --filter 'label=com.docker.compose.project=proveit-docker' --format '{{.Ports}}'" \
    --contains "->8080/tcp" \
    --expect "127.0.0.1:8100 mapped to 8080 inside the container"

finish
