#!/usr/bin/env bash
# Grades the exercise by running the customer's own request script.
source "$TSE_LIB/assert.sh"

assert "API is up and serving" \
    --run "curl -s --max-time 3 http://127.0.0.1:8101/health" \
    --contains '"status": "healthy"' \
    --expect "HTTP 200 from /health" \
    --retries 20 --delay 2

assert "Customer webhook delivery is accepted" \
    --run "bash \$TSE_STACK_DIR/request.sh" \
    --contains '"status": "accepted"' \
    --expect 'HTTP 202 with {"status": "accepted"} from POST /v2/webhooks/events' \
    --retries 3 --delay 2

finish
