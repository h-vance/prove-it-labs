## CUSTOMER TICKET: order events have stopped reaching us

**Account:** Northwind Freight (enterprise)
**Impact:** order events not delivered since 2026-08-12
**Started:** sometime Tuesday

> Our order events are not showing up in your system any more. Nothing on our
> side has been deployed for three weeks. Our logs just show the call failing
> with an error, so we assume your API is having problems. Can you confirm
> there is an outage?

**Your job**

1. Reproduce the failure before you accept or reject the customer's theory.
2. Prove what is actually being refused, and by what.
3. Get the customer's own workflow succeeding, then write the update.

**Working notes**

The API is at `http://127.0.0.1:8101`. The customer's own request lives in
`labs/api/_stack/request.sh`. Run it to reproduce, edit it until it succeeds,
then run `tse check`. Credentials you have access to are listed in
`labs/api/_stack/credentials.md`.
