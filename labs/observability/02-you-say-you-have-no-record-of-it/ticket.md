## CUSTOMER TICKET: we have sent you three references and you say none of them exist

**Account:** Northwind Traders (enterprise)
**Impact:** month end report fails, and three support attempts have gone nowhere
**Started:** first raised nine days ago

> Our month end report fails. When it does, your product shows an error with a
> reference on it and tells us to quote that reference to support.
>
> We have now done that three times. Every time, the reply is that there is no
> record of it and could we please confirm we copied it correctly. We copied it
> correctly. Here is the most recent one, and a screenshot of where it came
> from: `req-nw7k2p9x4m31`.
>
> I want to be clear about how this looks from here. Your product tells us to
> quote a reference. We quote it. You tell us it does not exist. Either your
> product is showing us something meaningless, or somebody is not looking
> properly.
>
> The report still fails. At this point I care more about the failure than the
> reference, but we cannot get anyone to look at the failure without one.

**Your job**

1. Take the reference seriously. The customer copied it correctly and the
   product did show it to them.
2. Prove where it stops. "We have no record of it" is a statement about your
   search, not about their report.
3. Make it so the reference they are given can actually be followed all the
   way through.

**Working notes**

The service is on `127.0.0.1:8102`. You can reproduce their failure, and you
can supply the reference yourself rather than waiting for one:

```bash
curl -s -H 'X-Request-Id: req-nw7k2p9x4m31' \
  'http://127.0.0.1:8102/v1/reports?tenant=northwind&rows=50000' | jq
```

Two services handle a report, `api` and `downstream`. Both write to their own
logs:

```bash
docker compose -f labs/observability/_stack/compose.yaml \
               -f labs/observability/_stack/compose.override.yaml \
               logs api

docker compose -f labs/observability/_stack/compose.yaml \
               -f labs/observability/_stack/compose.override.yaml \
               logs downstream
```

Configuration is in `labs/observability/_stack/compose.override.yaml`. After
editing, run `tse apply`, then `tse check`.

Fixing the report itself is a separate ticket. This one is about being able to
find it.
