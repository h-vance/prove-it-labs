## CUSTOMER TICKET: customer lookup returns not found for accounts that exist

**Account:** Copperline Robotics (growth)
**Impact:** account lookups failing across their support tooling
**Started:** noticed this morning

> Our internal tool looks up customer records through your API and it has
> started saying not found for accounts we can see perfectly well in your web
> app. The account IDs are correct, I checked three of them by hand. We have not
> changed this integration since we built it last year.

**Your job**

1. Reproduce the failure before you accept the customer's framing.
2. Prove whether the record is missing or the request is.
3. Get the lookup succeeding, then write the update.

**Working notes**

The API is at `http://127.0.0.1:8101`. The customer's own request lives in
`labs/api/_stack/request.sh`. Run it to reproduce, edit it until it succeeds,
then run `tse check`. Credentials you have access to are listed in
`labs/api/_stack/credentials.md`.
