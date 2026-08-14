## CUSTOMER TICKET: customer list is empty and will not load

**Account:** Copperline Robotics (growth)
**Impact:** all users, core workflow unusable
**Started:** this morning

> Same thing your team fixed for Beacon last week, I think. The app loads but
> the customer list just shows service unavailable. Our security team did a
> scheduled rotation overnight, but that is supposed to be routine and it has
> never caused this before.

**Your job**

1. Prove the cause for **this** incident. Do not assume it matches the last one.
2. Restore service with the smallest correct change.
3. Verify the customer's own workflow, not just that something responds.

**Working notes**

The service is expected on `http://127.0.0.1:8100`. The customer workflow is
`GET /customers`. Runtime configuration lives in
`labs/docker/_stack/compose.override.yaml`. After editing it, run `tse apply`
to recreate the services, then `tse check`.
