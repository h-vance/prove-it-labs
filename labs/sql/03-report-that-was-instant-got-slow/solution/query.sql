-- Per-account request summary for the first week of July.
--
-- The query was never the problem. Nothing supported looking a customer up, so
-- the database had to read every row to find one account's. The index matches
-- the filter: equality on customer_id first, then the range on requested_at.
CREATE INDEX IF NOT EXISTS idx_api_requests_customer_time
    ON api_requests (customer_id, requested_at);

SELECT count(*) AS requests, avg(duration_ms)::int AS avg_ms
FROM api_requests
WHERE customer_id = 7
  AND requested_at >= TIMESTAMPTZ '2026-07-01'
  AND requested_at <  TIMESTAMPTZ '2026-07-08';
