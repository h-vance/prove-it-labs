#!/usr/bin/env bash
# The customer's nightly usage sync, corrected to respect the rate limit the
# API advertises rather than hammering through it.
set -uo pipefail

API=http://127.0.0.1:8101
API_KEY="wk_live_active_3c95"
PAGES=8
MAX_ATTEMPTS=5

for page in $(seq 1 "$PAGES"); do
    attempt=0
    while true; do
        attempt=$((attempt + 1))
        status=$(curl -s -o /tmp/tse-page.json -D /tmp/tse-page.headers \
            -w '%{http_code}' \
            -X GET "$API/v2/usage?page=$page" \
            -H "X-API-Key: $API_KEY")

        if [[ $status != "429" ]]; then
            break
        fi
        if (( attempt >= MAX_ATTEMPTS )); then
            break
        fi

        # The server states exactly how long to wait. Honor it rather than
        # guessing at a backoff, and never retry immediately.
        wait_for=$(grep -i '^Retry-After:' /tmp/tse-page.headers \
            | tr -d '\r' | awk '{print $2}')
        sleep "${wait_for:-2}"
    done
    echo "page=$page HTTP $status"
done
