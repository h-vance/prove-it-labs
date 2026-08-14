#!/usr/bin/env bash
# The customer's nightly usage sync, exactly as their system runs it.
# It pages through usage records as fast as it can.
# Edit this until every page succeeds, then run `tse check`.
set -uo pipefail

API=http://127.0.0.1:8101
API_KEY="wk_live_active_3c95"
PAGES=8

for page in $(seq 1 "$PAGES"); do
    status=$(curl -s -o /tmp/tse-page.json -w '%{http_code}' \
        -X GET "$API/v2/usage?page=$page" \
        -H "X-API-Key: $API_KEY")
    echo "page=$page HTTP $status"
done
