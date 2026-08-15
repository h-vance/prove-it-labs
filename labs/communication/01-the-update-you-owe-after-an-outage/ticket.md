## CUSTOMER TICKET: we need something in writing about this morning

**Account:** Beacon Analytics (growth)
**Impact:** resolved, update outstanding
**Started:** the outage is over, the ticket is not

> Thanks for getting it working again. I need to send something to my own
> leadership before end of day and I would rather forward yours than write my
> own version of it.
>
> What I need to be able to answer is what happened, how long we were affected,
> whether any of our data is wrong now, and whether this is going to happen
> again next time you do maintenance. Please do not send me the engineering
> detail, I will not be able to use it and neither will they.

**Your job**

1. Write the update. The investigation is already done and the facts are
   given to you.
2. Say what was affected in words the customer can check for themselves.
3. Cite at least one figure, name at least one thing you eliminated, and end
   by committing somebody to something.

**Working notes**

There is no system to bring up for this one. `tse start` puts two files in
front of you: the evidence you have to work from, and a draft that somebody
else started and did badly.

Rewrite the draft, then run `tse check`. The grader checks the things a machine
honestly can, then hands you a short list to judge yourself, because the part
that decides whether this update lands is not something a linter can see.
