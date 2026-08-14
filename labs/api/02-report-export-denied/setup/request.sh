#!/usr/bin/env bash
# The customer's report export call, exactly as their system makes it.
# Edit this until it succeeds, then run `tse check`.
set -uo pipefail

API=http://127.0.0.1:8101
TOKEN="tok_viewer_5d10"

curl -s -D - -o /tmp/tse-body.json \
    -X GET "$API/v2/reports/incidents" \
    -H "Authorization: Bearer $TOKEN" \
    | head -1
cat /tmp/tse-body.json
