-- Active accounts report: customers with at least one user, by plan.
-- Edit this until it answers the question correctly, then run `tse check`.
SELECT c.plan, COUNT(*) AS customer_count
FROM customers c
JOIN workspaces w ON w.customer_id = c.id
JOIN users u ON u.workspace_id = w.id
GROUP BY c.plan
ORDER BY c.plan;
