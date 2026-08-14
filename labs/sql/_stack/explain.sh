#!/usr/bin/env bash
# Prints the query plan for the statement passed as the first argument.
#
# EXPLAIN ANALYZE executes the statement, so this is only ever pointed at
# read-only reporting queries. Never run it against a write without a
# transaction you intend to roll back.
set -uo pipefail

STACK_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

docker compose -f "$STACK_DIR/compose.yaml" exec -T \
    -e PGPASSWORD=demo-password postgres \
    psql -U support -d support_lab -A --pset=footer=off \
    -c "EXPLAIN (ANALYZE, BUFFERS) $1" 2>&1
