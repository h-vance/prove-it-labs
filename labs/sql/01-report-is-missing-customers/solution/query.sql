-- Plan mix report: how many customers are on each plan.
-- LEFT JOIN keeps customers that have no workspace yet, and COUNT(DISTINCT)
-- keeps the answer correct even if a customer ever gains a second one.
SELECT c.plan, COUNT(DISTINCT c.id) AS customer_count
FROM customers c
LEFT JOIN workspaces w ON w.customer_id = c.id
GROUP BY c.plan
ORDER BY c.plan;
