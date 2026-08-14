#!/usr/bin/env bash
# The customer's lookup call, exactly as their system makes it.
# Edit this until it succeeds, then run `tse check`.
set -uo pipefail

API=http://127.0.0.1:8101

curl -s -D - -o /tmp/tse-body.json \
    -X GET "$API/v1/customers/cus_8823" \
    | head -1
cat /tmp/tse-body.json
