-- Synthetic customer data. No real people, accounts, or identifiers.
CREATE TABLE IF NOT EXISTS customers (
    id           SERIAL PRIMARY KEY,
    company      TEXT        NOT NULL,
    plan         TEXT        NOT NULL,
    signed_up_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO customers (company, plan) VALUES
    ('Northwind Freight',    'enterprise'),
    ('Beacon Analytics',     'growth'),
    ('Copperline Robotics',  'growth'),
    ('Tidewater Health',     'enterprise'),
    ('Juniper Labs',         'starter'),
    ('Marlowe Logistics',    'growth'),
    ('Halcyon Media',        'starter'),
    ('Redwood Instruments',  'enterprise'),
    ('Sable Payments',       'growth'),
    ('Vantage Grid',         'starter');
