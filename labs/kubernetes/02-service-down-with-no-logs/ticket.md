## CUSTOMER TICKET: order service is down and we cannot see why

**Account:** Beacon Analytics (growth)
**Impact:** order lookups unavailable to all users
**Started:** after a config change last night

> The order service is completely down since a config change went in last
> night. Our on-call engineer went looking and says there is nothing in the
> logs at all, which is what is confusing us. If it had crashed we would expect
> an error somewhere. Can you tell us what happened?

**Your job**

1. Treat the absence of logs as evidence and work out what it rules out.
2. Prove the cause before you name it.
3. Restore service and verify the customer's own workflow.

**Working notes**

The workload runs in the `tse-training` namespace on the `kind-proveit`
context. Unlike the Docker track there is no file to edit and no `tse apply`:
change the cluster directly, the way you would in production, then run
`tse check`. `tse reset` puts the ticket's state back.
