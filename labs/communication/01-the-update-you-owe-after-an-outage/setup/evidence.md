# Evidence: the customer list would not load

Everything below was established during the incident. You are not being asked
to investigate anything here. You are being asked to write the update, and
these are the facts you have to work from.

This is the same incident as `docker/02`, so you already know how it was
proved. Nothing in this file is new.

## Workflow

What the customer could not do, in the words they would use. Your update has to
name it, because that is the only part of this they can check for themselves.

- `customer list`
- `list of customers`

## Figures

Specifics you are allowed to give them. Every one of these is true, and at
least one of them belongs in the update: a reassurance with no number in it
reads exactly like a reassurance with nothing behind it.

- `47 minutes`
- `all users`
- `no data was lost`

## Ruled out

Things you eliminated with evidence, which are usually the things the customer
is quietly most worried about. Say at least one of them out loud.

- `the database being unavailable`
- `a change to your data`
- `anything on your side`

## What actually happened

Maintenance the previous night changed the address the application uses to
reach its database. It was pointed at itself rather than at the database, so
every request that needed customer records failed while everything else kept
working. The address was corrected and the workflow confirmed.

Total customer-visible impact was 47 minutes, from the first failed request to
the confirmed fix.
