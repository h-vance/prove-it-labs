# Solution: data access lost after credential rotation

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `docker compose logs app` | The database **rejected** the login, rather than refusing the connection | Nothing about which side is wrong |
| The rejection wording | The network path works and the database is up | Nothing about who rotated what |
| `exec app printenv DB_USER DB_PASSWORD` | What the application presents | Whether it is correct |
| `exec postgres printenv POSTGRES_USER POSTGRES_PASSWORD` | What the database was created with | |

The distinction that matters: **connection refused** and **authentication
failed** are not the same evidence. The first means nothing was listening. The
second means something listened, evaluated you, and said no. Only the second
proves the network path is fine.

## Root cause

The overnight rotation updated the application's `DB_PASSWORD` but not the
credential the database was initialized with. PostgreSQL's user password is set
from `POSTGRES_PASSWORD` when the data directory is first created, and it is not
re-read on later restarts, so the database kept the original value while the
application moved on to the new one.

The two halves of one credential drifted apart. The symptom looked identical to
the previous incident because both end in the same customer-visible `503`, which
is exactly why the symptom is not evidence.

## Scoped fix

Bring the application back in step with the credential the database actually
holds:

```yaml
services:
  app:
    environment:
      DB_PASSWORD: demo-password
```

Then:

```bash
tse apply
tse check
```

In production the correct direction is usually the opposite: rotate the
database credential forward to match the new secret rather than reverting the
application to the old one. What matters here is that you can state which side
is out of step and why, before you change either.

## Customer update

> The customer list failure was caused by the overnight credential rotation
> being applied to the application but not to the database, so the database was
> correctly rejecting the application's login. This is different from the issue
> another account saw last week, which is why the earlier fix would not have
> resolved it. We have brought the two back in step and confirmed your customer
> list is loading. No data was lost, and no customer data was exposed by the
> failed logins.

## Engineering escalation, if you needed one

> Impact: `GET /customers` returning 503 for all users since the overnight
> rotation.
> Evidence: `database_connection_failed` with a password authentication failure
> for user `support`; database container healthy and accepting connections;
> application and database hold different values for the same credential.
> Confirmed: network path, service name resolution, database availability.
> Ruled out: connectivity, the `DB_HOST` misconfiguration seen previously.
> Suspected cause: the rotation updated the consumer but not the provider,
> and PostgreSQL does not re-apply `POSTGRES_PASSWORD` to an existing data
> directory.
> Request: confirm whether the rotation job is expected to update both sides,
> and whether other services rotated in the same window are affected.

## Say it out loud (90 seconds)

> The customer thinks this is a repeat of a previous incident, so the first
> thing I want to do is prove whether it actually is, because applying last
> week's fix without checking is how you report a resolution that did not
> resolve anything. I would read the application's own failure detail. Last time
> it was a refused connection. This time the database is rejecting the login,
> which is a different fact: it proves the network path and the database itself
> are fine, because something has to be listening in order to reject you. That
> narrows it to authentication. I would then compare what the application is
> presenting against what the database was built with, and they differ, which
> lines up with the rotation the customer mentioned. My safe next step is to
> bring the two back in step, and to ask whether other services rotated in the
> same window are affected, because one drifted credential is an incident and a
> shared rotation job is an outage waiting to happen.
