#!/usr/bin/env bash
# Prints the query plan for the statement passed as the first argument.
#
# EXPLAIN ANALYZE executes the statement, so this is only ever pointed at
# read-only reporting queries. Never run it against a write without a
# transaction you intend to roll back.
set -uo pipefail

STACK_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Parallelism is turned off deliberately, and it is a teaching decision rather
# than a performance one.
#
# With workers enabled the same query plans as Finalize Aggregate over Gather
# over Partial Aggregate over Parallel Seq Scan: four extra concepts that have
# nothing to do with what this exercise is about. Worse, the rows scanned are
# then reported per worker, so the plan shows 146250 while the solution talks
# about the 300,000 rows the scan actually reads. Serially it reports
# "Rows Removed by Filter: 292500" beside "rows=7500", and the number in the
# writeup is one the learner can see for themselves.
#
# It also makes the plan the same shape on every machine, which is what lets
# the recorded transcripts be checked against a real run in CI.
docker compose -f "$STACK_DIR/compose.yaml" exec -T \
    -e PGPASSWORD=demo-password \
    -e PGOPTIONS="-c max_parallel_workers_per_gather=0" postgres \
    psql -U support -d support_lab -A --pset=footer=off \
    -c "EXPLAIN (ANALYZE, BUFFERS) $1" 2>&1
