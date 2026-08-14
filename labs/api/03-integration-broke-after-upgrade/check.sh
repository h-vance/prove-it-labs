#!/usr/bin/env bash
# Grades the exercise by running the customer's own request script.
source "$TSE_LIB/assert.sh"

assert "API is up and serving" \
    --run "curl -s --max-time 3 http://127.0.0.1:8101/health" \
    --contains '"status": "healthy"' \
    --expect "HTTP 200 from /health" \
    --retries 20 --delay 2

assert "Customer lookup returns the account record" \
    --run "bash \$TSE_STACK_DIR/request.sh" \
    --contains '"company": "Northwind Freight"' \
    --expect 'HTTP 200 with the customer record for cus_8823' \
    --retries 3 --delay 2

finish
