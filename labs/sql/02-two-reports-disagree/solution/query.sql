-- Active accounts report: customers with at least one user, by plan.
-- The joins are needed to establish "has at least one user", but the thing
-- being counted is customers, so count customers rather than result rows.
SELECT c.plan, COUNT(DISTINCT c.id) AS customer_count
FROM customers c
JOIN workspaces w ON w.customer_id = c.id
JOIN users u ON u.workspace_id = w.id
GROUP BY c.plan
ORDER BY c.plan;
