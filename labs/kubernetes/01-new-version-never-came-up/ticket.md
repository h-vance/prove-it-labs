## CUSTOMER TICKET: this morning's release never went live

**Account:** Northwind Freight (enterprise)
**Impact:** order lookups unavailable to all users
**Started:** after the 08:40 release

> We were told the release went out at 08:40 but the new version is definitely
> not live, and now the order screen is not loading at all. Our deploy pipeline
> reported success, so we assumed it worked. Nothing changed on our side.

**Your job**

1. Prove how far the release actually got before you name a cause.
2. Restore service with the smallest correct change.
3. Verify the customer's own workflow, not just that something responds.

**Working notes**

The workload runs in the `tse-training` namespace on the `kind-proveit`
context. Unlike the Docker track there is no file to edit and no `tse apply`:
change the cluster directly, the way you would in production, then run
`tse check`. `tse reset` puts the ticket's state back.
