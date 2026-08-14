## CUSTOMER TICKET: order service keeps restarting

**Account:** Copperline Robotics (growth)
**Impact:** intermittent failures, roughly every few minutes
**Started:** after a tuning change on Tuesday

> The order service keeps dying and coming back. Users get errors for maybe
> thirty seconds, then it recovers, then it happens again. We changed a cache
> setting on Tuesday to improve performance but that is a config value, not
> code, so we do not think that is related. Nobody has deployed new code in
> two weeks.

**Your job**

1. Prove whether the application is failing or something is stopping it.
2. Those are different causes with different fixes, so do not guess.
3. Restore stable service and verify the customer's own workflow.

**Working notes**

The workload runs in the `tse-training` namespace on the `kind-proveit`
context. Unlike the Docker track there is no file to edit and no `tse apply`:
change the cluster directly, the way you would in production, then run
`tse check`. `tse reset` puts the ticket's state back.
