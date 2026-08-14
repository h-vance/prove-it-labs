-- Per-account request summary for the first week of July.
-- Edit this until the database can answer it without reading the whole table,
-- then run `tse check`.
SELECT count(*) AS requests, avg(duration_ms)::int AS avg_ms
FROM api_requests
WHERE customer_id = 7
  AND requested_at >= TIMESTAMPTZ '2026-07-01'
  AND requested_at <  TIMESTAMPTZ '2026-07-08';
