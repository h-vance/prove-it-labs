# Draft update to Beacon Analytics

Hi Dana,

Your customer list was failing to load for all users between 08:14 and 09:01
this morning, a total of 47 minutes. Any page that did not read customer
records kept working normally throughout, which is why the outage looked
partial from your side.

The cause was a configuration change made during last night's maintenance
window. It changed the address our application uses to reach the database that
holds your customer records, so those requests could not complete. We have
corrected the address and confirmed the customer list is loading again.

Two things I want to state plainly, because they are the questions I would be
asking. There was no change to your data: no data was lost and nothing was
altered. And this was not caused by anything on your side, so there is nothing
for your team to undo or reconfigure.

I am raising the change itself internally, because a maintenance step should
not have been able to make this edit without it being caught before it reached
you. I will send you the outcome of that review by Friday. If you see any other
page still failing in the meantime, send me the page name and I will check it
against the same setting the same day.
