#!/usr/bin/env bash
# Prints the customer row count once the database is up and seeded.
# Seeding 300,000 request rows takes a few seconds on first start, so checks
# poll this rather than assuming the container being healthy means data exists.
set -uo pipefail

STACK_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

docker compose -f "$STACK_DIR/compose.yaml" exec -T \
    -e PGPASSWORD=demo-password postgres \
    psql -U support -d support_lab -Atc 'SELECT count(*) FROM customers' 2>&1
