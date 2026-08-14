-- Support SaaS dataset for the SQL investigation track.
-- Adapted from the support-tech-sprint schema. All data is synthetic.
--
-- The shape matters more than the size. Three facts are deliberate:
--   * six customers have no workspace, so an inner join silently loses them
--   * workspaces hold wildly uneven user counts, so a join fans rows out
--   * api_requests is large and unindexed, so a lookup becomes a full scan

CREATE TABLE customers (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    plan       TEXT NOT NULL,
    status     TEXT NOT NULL,
    region     TEXT NOT NULL,
    created_at DATE NOT NULL
);

CREATE TABLE workspaces (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    name        TEXT NOT NULL,
    status      TEXT NOT NULL,
    created_at  DATE NOT NULL
);

CREATE TABLE users (
    id            INTEGER PRIMARY KEY,
    workspace_id  INTEGER NOT NULL REFERENCES workspaces(id),
    email         TEXT NOT NULL,
    role          TEXT NOT NULL,
    last_login_at TIMESTAMPTZ
);

CREATE TABLE api_requests (
    id           BIGSERIAL PRIMARY KEY,
    customer_id  INTEGER NOT NULL,
    path         TEXT NOT NULL,
    status_code  INTEGER NOT NULL,
    duration_ms  INTEGER NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL
);

-- 40 customers: 12 enterprise, 16 growth, 12 starter.
INSERT INTO customers (id, name, plan, status, region, created_at)
SELECT
    n,
    'Customer ' || n,
    CASE WHEN n <= 12 THEN 'enterprise'
         WHEN n <= 28 THEN 'growth'
         ELSE 'starter' END,
    'active',
    CASE WHEN n % 3 = 0 THEN 'us-east' WHEN n % 3 = 1 THEN 'eu-west' ELSE 'ap-south' END,
    DATE '2024-01-01' + (n * 7)
FROM generate_series(1, 40) AS n;

-- 34 workspaces. Customers 35 to 40 have none, which is the trap in the
-- first exercise: they are real, active, paying customers with no workspace yet.
INSERT INTO workspaces (id, customer_id, name, status, created_at)
SELECT n, n, 'Workspace ' || n, 'active', DATE '2024-02-01' + (n * 5)
FROM generate_series(1, 34) AS n;

-- Users are unevenly distributed: enterprise workspaces carry many, starter
-- workspaces carry one or two. Joining through them multiplies customer rows.
INSERT INTO users (id, workspace_id, email, role, last_login_at)
SELECT
    row_number() OVER (),
    w.id,
    'user' || w.id || '_' || s || '@example.invalid',
    CASE WHEN s = 1 THEN 'admin' ELSE 'member' END,
    TIMESTAMPTZ '2026-08-01 09:00:00+00' + (w.id || ' hours')::interval
FROM workspaces w
CROSS JOIN LATERAL generate_series(1, CASE WHEN w.id <= 12 THEN 9 ELSE 2 END) AS s;

-- 300,000 request rows, no index on customer_id. Enough that a full scan and
-- an index lookup are visibly different in a query plan.
INSERT INTO api_requests (customer_id, path, status_code, duration_ms, requested_at)
SELECT
    1 + (n % 40),
    CASE WHEN n % 4 = 0 THEN '/v2/orders'
         WHEN n % 4 = 1 THEN '/v2/customers'
         WHEN n % 4 = 2 THEN '/v2/usage'
         ELSE '/v2/reports/incidents' END,
    CASE WHEN n % 50 = 0 THEN 500 WHEN n % 17 = 0 THEN 404 ELSE 200 END,
    5 + (n % 400),
    TIMESTAMPTZ '2026-07-01 00:00:00+00' + (n || ' seconds')::interval
FROM generate_series(1, 300000) AS n;

ANALYZE;
