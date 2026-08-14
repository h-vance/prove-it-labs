-- Plan mix report: how many customers are on each plan.
-- Edit this until it answers the question correctly, then run `tse check`.
SELECT c.plan, COUNT(*) AS customer_count
FROM customers c
JOIN workspaces w ON w.customer_id = c.id
GROUP BY c.plan
ORDER BY c.plan;
