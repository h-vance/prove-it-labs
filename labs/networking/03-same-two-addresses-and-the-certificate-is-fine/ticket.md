## CUSTOMER TICKET: same address, same failure, and we checked it ourselves this time

**Account:** Ardent Logistics (enterprise)
**Impact:** nightly export failing, two nights
**Started:** Tuesday night, no change on our side

> This is the third time this year and we would like it to be the last, so we
> have done the work before raising it.
>
> Your engineer gave us a command in April that prints the dates and the names
> your server presents. We ran it. It is good until 2035 and it lists both of
> our addresses, so it is not April's problem and it is not May's problem
> either. We checked.
>
> The old address still works. The one you moved us to fails on every attempt,
> and it fails instantly, which is new. In May it sat there for a moment and
> then complained at length. Now it comes back straight away with a much
> shorter message and a different number at the front of it.
>
> We have not changed anything. Same job, same credentials, same payload, same
> two addresses we have been using since May.
>
> We are not going back to the old address again. Please tell us what is
> actually wrong this time.

**Your job**

1. The customer says it is not the same problem as either previous ticket.
   They have been right before. Confirm it rather than assuming it.
2. The failure is faster and the number is different. Both of those are
   evidence. Work out which stage of the connection is failing before you look
   at anything else.
3. Fix it without moving the customer, and without touching what the two
   previous tickets fixed.

**Working notes**

The customer's integration runs in the `client` service, and `GATEWAY_URL`
controls which address it calls:

```bash
docker compose -f labs/networking/_stack/compose.yaml \
               -f labs/networking/_stack/compose.override.yaml \
               exec client /app/upload.sh
```

Everything the platform team configures for this customer is in
`labs/networking/_stack/compose.override.yaml`. After editing, run `tse apply`,
then `tse check`.

Moving the customer back to the old address is not a fix. The grader checks
both, and the customer has told you twice now that they will not accept it.
