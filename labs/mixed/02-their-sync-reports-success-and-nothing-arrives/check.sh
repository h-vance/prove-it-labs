#!/usr/bin/env bash
# Grades the exercise by running the customer's own request script.
source "$TSE_LIB/assert.sh"

assert "API is up and serving" \
    --run "curl -s --max-time 3 http://127.0.0.1:8101/health" \
    --contains '"status": "healthy"' \
    --expect "HTTP 200 from /health" \
    --retries 20 --delay 2

# This passes in the broken state too, and printing it is the point. The
# customer told the truth: their job really does get an accepted response on
# every run. Showing that passing while the two below fail is the lesson.
assert "Customer webhook delivery is accepted" \
    --run "bash \$TSE_STACK_DIR/request.sh" \
    --contains '"status": "accepted"' \
    --expect 'HTTP 202 with {"status": "accepted"} from POST /v2/webhooks/events' \
    --retries 3 --delay 2

assert "The workspace the customer sent was understood" \
    --run "bash \$TSE_STACK_DIR/request.sh" \
    --contains '"workspace": "ws_4471"' \
    --expect 'the response echoing back "workspace": "ws_4471" rather than null'

assert "The event the customer sent was understood" \
    --run "bash \$TSE_STACK_DIR/request.sh" \
    --contains '"event": "order.created"' \
    --expect 'the response echoing back "event": "order.created" rather than null'

finish
