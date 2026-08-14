## CUSTOMER TICKET: dashboard unavailable since this morning

**Account:** Northwind Freight (enterprise)
**Impact:** all users, complete outage
**Started:** shortly after the 09:14 release

> Nobody on our team can load the customer dashboard. It spins for a while and
> then times out. It was working fine yesterday afternoon and we have not
> changed anything on our side. We have a board review at 14:00 and this is the
> data we present from. Please treat as urgent.

**Your job**

1. Prove what is actually failing before you name a cause.
2. Restore service with the smallest correct change.
3. Verify the customer's own workflow, not just that something responds.

**Working notes**

The service is expected on `http://127.0.0.1:8100`. The customer workflow is
`GET /customers`. Runtime configuration lives in
`labs/docker/_stack/compose.override.yaml`. After editing it, run `tse apply`
to recreate the services, then `tse check`.
