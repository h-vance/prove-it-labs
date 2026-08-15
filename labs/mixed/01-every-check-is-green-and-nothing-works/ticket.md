## CUSTOMER TICKET: the whole application is unreachable, but your status page says it is fine

**Account:** Halden Freight (enterprise)
**Impact:** every user, nothing loads at all
**Started:** this morning, after a change went out last night

> Nobody can get in. Every page just fails to load, not an error message, it
> simply returns nothing. We have checked from three different offices and two
> phones on mobile data, so it is not us.
>
> What I do not understand is that your own status page has been green the
> whole time, and the engineer we spoke to last night said the deploy came up
> clean and everything was reporting healthy. Something is clearly wrong
> somewhere, because we have had no service since about 6am.

**Your job**

1. Work out which layer is failing. This ticket does not tell you, and neither
   does the folder it is filed under.
2. Prove where the customer's request actually stops.
3. Restore service with the smallest correct change, then verify the workflow
   the customer described rather than the one that was already passing.

**Working notes**

The customer reaches this service at `http://127.0.0.1:8100`, and the workflow
they mean is `GET /customers`.

Nothing here tells you which system is involved. Finding that out is part of
the exercise, and it is a real skill: a ticket rarely arrives with the
technology attached. When you have found the configuration that is wrong and
changed it, run `tse apply` to recreate the services, then `tse check`.
