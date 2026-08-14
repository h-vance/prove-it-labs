## CUSTOMER TICKET: order lookups return nothing again

**Account:** Juniper Labs (starter)
**Impact:** order lookups failing for all users
**Started:** after a monitoring change this morning

> This looks like the issue Tidewater reported last week. Order lookups return
> nothing and everything reports healthy. Our platform engineer already checked
> the labels this time because he saw your write-up, and he says they match, so
> he is out of ideas. He did adjust some health check settings this morning but
> those only affect monitoring.

**Your job**

1. Confirm what the customer ruled out, then keep going. The labels really are
   correct.
2. Prove why the request still does not reach the application.
3. Restore service and verify the customer's own workflow.

**Working notes**

The workload runs in the `tse-training` namespace on the `kind-proveit`
context. Unlike the Docker track there is no file to edit and no `tse apply`:
change the cluster directly, the way you would in production, then run
`tse check`. `tse reset` puts the ticket's state back.
