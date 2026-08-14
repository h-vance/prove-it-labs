#!/usr/bin/env bash
# The customer's integration call, exactly as their system makes it.
# Edit this until it succeeds, then run `tse check`.
set -uo pipefail

API=http://127.0.0.1:8101
API_KEY="wk_live_revoked_8f21"

curl -s -D - -o /tmp/tse-body.json \
    -X POST "$API/v2/webhooks/events" \
    -H "X-API-Key: $API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{"workspace":"northwind","event":"order.created"}' \
    | head -1
cat /tmp/tse-body.json
