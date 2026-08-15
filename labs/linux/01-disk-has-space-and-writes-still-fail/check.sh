#!/usr/bin/env bash
# Grades the exercise by gathering the same evidence a support engineer would.
source "$TSE_LIB/assert.sh"

COMPOSE="docker compose -f $TSE_STACK_DIR/compose.yaml -f $TSE_STACK_DIR/compose.override.yaml"

assert "The export completes" \
    --run "$COMPOSE exec -T worker python3 /app/exporter.py" \
    --contains '"status": "ok"' \
    --expect 'the exporter reporting {"status": "ok"} rather than a write failure' \
    --retries 10 --delay 2

# Pins the failure mode. Without this, raising the inode budget would also pass
# while leaving the export writing one file per row, which is the actual defect.
assert "The export writes a sensible number of files" \
    --run "$COMPOSE exec -T worker sh -c 'ls /var/spool/exports | wc -l'" \
    --equals "5" \
    --expect "5 chunk files for 5000 rows, not one per row"

# The spool directory has room to run again tomorrow. An export that succeeds
# by exactly filling the budget has not been fixed, it has been rescheduled.
assert "The spool directory is not left full" \
    --run "$COMPOSE exec -T worker sh -c 'df -i /var/spool/exports | tail -1'" \
    --not-contains "100%" \
    --expect "inode usage below 100% after the export"

finish
