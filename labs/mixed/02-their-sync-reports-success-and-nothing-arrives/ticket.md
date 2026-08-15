## CUSTOMER TICKET: our sync says it worked every night and nothing is in your system

**Account:** Halden Freight (enterprise)
**Impact:** no events delivered since the integration went live
**Started:** since we switched the integration on, eight days ago

> Our nightly job has run every night since we turned it on and it has reported
> success every single time. We log the response from your side and it comes
> back as accepted, every run, no failures at all.
>
> But nothing has ever shown up in your dashboard. Not one event in eight days.
> Our team has been through our side twice and cannot find anything wrong,
> because from where we are sitting it is working perfectly.
>
> We are starting to wonder whether the events are being dropped after you
> accept them.

**Your job**

1. Work out which layer is failing. This ticket does not tell you, and neither
   does the folder it is filed under.
2. Prove whether the request is understood, not just whether it is accepted.
3. Make the customer's own call succeed in the sense they actually meant, then
   verify it.

**Working notes**

The customer's integration call is reproduced exactly as their system makes it.
Once you have found what is running, you will find their call alongside it, and
that file is what you edit. Their credentials and the current contract are
documented with the service.

When you have changed it, run `tse check`.
