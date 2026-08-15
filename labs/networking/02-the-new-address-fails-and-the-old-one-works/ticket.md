## CUSTOMER TICKET: the address you migrated us to fails on every call

**Account:** Ardent Logistics (enterprise)
**Impact:** nightly export failing again, one night so far
**Started:** the evening we switched to the new address

> Your migration note asked us to point our export at the new address. We did
> that yesterday afternoon and last night's run failed on every attempt.
>
> Before you ask: we checked. Your team fixed something like this for us in
> April and told us the date to watch was in 2035. We looked, and it is still
> 2035, so it is not that again.
>
> We also pointed the job back at the old address as a test and it went
> through immediately, first try, no changes to anything else. So the service
> is up, our credentials are fine, and our job works. It is only the address
> you asked us to move to.
>
> We would rather not stay on the old address if you are retiring it. What do
> you need from us?

**Your job**

1. Confirm what the customer already told you, rather than assuming it. Both
   addresses, same evidence, side by side.
2. Read the error properly. It is not the same failure as April, and one line
   is the only thing that says so.
3. Fix the new address without breaking the old one. They are both in use.

**Working notes**

The customer's integration runs in the `client` service, and `GATEWAY_URL`
controls which address it calls:

```bash
docker compose -f labs/networking/_stack/compose.yaml \
               -f labs/networking/_stack/compose.override.yaml \
               exec client /app/upload.sh
```

Both the gateway's configuration and the address the client uses are in
`labs/networking/_stack/compose.override.yaml`. After editing, run `tse apply`,
then `tse check`.

Moving the customer back to the old address is not a fix. The grader checks
the new one, and the customer has already asked you not to.
