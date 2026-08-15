# Solution: the update you owe after an outage

## What the evidence proved

There was nothing to investigate here, which is the point. The facts were
handed to you in `evidence.md` and the exercise is entirely about what you do
with them.

| Rule | What it is really asking |
|---|---|
| States the impact in the customer's terms | Can they check your first sentence without trusting you |
| Cites a specific figure | Is there anything behind the reassurance |
| Names something ruled out | Did you answer the question underneath their ticket |
| Ends with a next step and an owner | Does anything happen after they read it |
| Uses no internal vocabulary | Are you writing to them or about them |
| Is the right length | Will they read to the end |

The starting draft failed all six, and it was factually correct throughout.
That gap is the whole lesson: being right about the system and being useful to
the customer are separate achievements.

## Root cause

The draft was written at the wrong altitude for its reader.

It named the setting, the kind of setting, and the value it had been given. All
true, none of it usable by somebody who told you plainly they would be
forwarding this to their leadership. What it never said was what the customer
could not do, for how long, or what happens next.

## Scoped fix

Rewrite `labs/communication/_stack/customer-update.md` so that:

- The first sentence names the workflow and the duration.
- The cause is described at the customer's altitude, not the system's.
- At least one eliminated cause is stated out loud, particularly their data.
- The last paragraph commits a named person to something with a date.

Then:

```bash
tse check
```

## Customer update

This is the artifact, so here it is in full:

> Hi Dana,
>
> Your customer list was failing to load for all users between 08:14 and 09:01
> this morning, a total of 47 minutes. Any page that did not read customer
> records kept working normally throughout, which is why the outage looked
> partial from your side.
>
> The cause was a configuration change made during last night's maintenance
> window. It changed the address our application uses to reach the database that
> holds your customer records, so those requests could not complete. We have
> corrected the address and confirmed the customer list is loading again.
>
> Two things I want to state plainly, because they are the questions I would be
> asking. There was no change to your data: no data was lost and nothing was
> altered. And this was not caused by anything on your side, so there is nothing
> for your team to undo or reconfigure.
>
> I am raising the change itself internally, because a maintenance step should
> not have been able to make this edit without it being caught before it reached
> you. I will send you the outcome of that review by Friday. If you see any other
> page still failing in the meantime, send me the page name and I will check it
> against the same setting the same day.

## Engineering escalation, if you needed one

You do not, for this one. The incident is closed and the fix is in. What the
update commits you to is a separate piece of work, and `communication/02` is
where you write that.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
