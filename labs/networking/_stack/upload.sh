#!/bin/sh
# The customer's nightly export upload.
#
# This is their integration, not ours, which is why it is baked into the image
# rather than sitting in the exercise where it could be edited. Support does not
# get to change the customer's client, and "make the client stop checking" is
# not a fix that would survive being written down in a ticket.
set -u

ENDPOINT="${GATEWAY_URL:?GATEWAY_URL is not set}/v1/exports"
PAYLOAD='{"export":"nightly","rows":4812}'

echo "uploading to $ENDPOINT"
curl -sS --max-time 10 \
    -X POST "$ENDPOINT" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD"
status=$?

echo
if [ "$status" -eq 0 ]; then
    echo "upload finished"
else
    echo "upload failed (curl exit $status)"
fi
exit "$status"
