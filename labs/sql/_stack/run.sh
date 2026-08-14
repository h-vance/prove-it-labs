#!/usr/bin/env bash
# Runs the learner's query.sql against the support database and prints the result.
#
# Deliberately unaligned, pipe-separated output. The learner is reading data,
# not admiring a table, and it keeps assertions in check.sh readable.
set -uo pipefail

STACK_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

docker compose -f "$STACK_DIR/compose.yaml" exec -T \
    -e PGPASSWORD=demo-password postgres \
    psql -U support -d support_lab -A -F'|' --pset=footer=off \
    < "$STACK_DIR/query.sql" 2>&1
