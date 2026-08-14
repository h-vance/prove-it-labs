## CUSTOMER TICKET: order lookups return nothing, but everything looks healthy

**Account:** Tidewater Health (enterprise)
**Impact:** order lookups failing for all users
**Started:** after yesterday's platform work

> Our order lookups have stopped returning anything since some platform work
> yesterday. Our team checked and everything reports healthy on your side, so
> they are stuck. The application does not error, it just gets nothing back.

**Your job**

1. Everything healthy plus nothing working is a specific pattern. Work out what
   it points at.
2. Prove where the request stops before you name a cause.
3. Restore service and verify the customer's own workflow.

**Working notes**

The workload runs in the `tse-training` namespace on the `kind-proveit`
context. Unlike the Docker track there is no file to edit and no `tse apply`:
change the cluster directly, the way you would in production, then run
`tse check`. `tse reset` puts the ticket's state back.
