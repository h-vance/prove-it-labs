# Solution: customer data not loading

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `docker compose ps` | Both containers are up and the database is healthy | Nothing about whether they can talk |
| `curl /customers` | The app answers, and answers `503` | Nothing about which dependency failed |
| `docker compose logs app` | The failure is `database_connection_failed`, with a connection-refused detail | Nothing about why the connection was refused |
| `exec app printenv DB_HOST` | The app is aiming at `localhost` | Nothing on its own, until you know where it is evaluated |
| `exec app getent hosts localhost` | Inside the container, `localhost` is the container itself | |

The database was never down, and the credentials were never wrong. Both of
those are worth ruling out explicitly, because both are the first guess most
people reach for.

## Root cause

The maintenance change set `DB_HOST` to `localhost`. Inside a container,
`localhost` is that container's own network namespace, so the application spent
every request trying to connect to a database inside itself. Nothing is
listening on port 5432 there, so the connection is refused immediately.

This is why the symptom looked like a database outage while the database was
provably healthy: the app never reached it.

On the shared Compose network, the database is reachable by its **service
name**, `postgres`, which Compose resolves through its internal DNS.

## Scoped fix

In `labs/docker/_stack/compose.override.yaml`:

```yaml
services:
  app:
    environment:
      DB_HOST: postgres
```

Then:

```bash
tse apply
tse check
```

## Customer update

> The customer list failure was caused by a connection setting changed during
> last night's maintenance. The application was pointed at the wrong address for
> the database, so those requests could not complete, which is why only the
> pages that read customer data were affected. We have corrected the setting and
> confirmed the customer list is loading. No data was lost or changed. If you
> notice any other pages still failing, tell me which ones and I will check them
> against the same setting.

## Engineering escalation, if you needed one

> Impact: `GET /customers` returning 503 for all users since the maintenance
> window.
> Evidence: app healthy and serving; `database_connection_failed` with
> connection refused; `DB_HOST=localhost` inside the app container; `postgres`
> container healthy and accepting connections on the Compose network.
> Confirmed: database availability, database credentials, app process health.
> Ruled out: database outage, credential rotation, schema change.
> Suspected cause: maintenance replaced the Compose service name with
> `localhost`, which resolves to the app container itself.
> Request: confirm whether the maintenance template is shared with other
> services that would have taken the same edit.

That last line matters. One misconfigured service is an incident. A shared
template is an outage waiting for the next deploy.

## Say it out loud (90 seconds)

> The application is running and returning an error, so this is not a startup
> failure, which already tells me more than the ticket did. I would read the
> application logs first, because a service that is running will normally say
> what it could not reach. Here it reports a database connection failure, so my
> next job is to prove which part of that path is broken: the database itself,
> the name, or the credentials. I would check the database container's health
> first because it is one command and it rules out an entire branch. It is
> healthy, so I would prove what hostname the app is using and what that name
> means from inside the app container. It is set to localhost, which inside a
> container points at the container itself, so the app was never reaching the
> database. The fix is to use the Compose service name. For the customer I would
> say a connection setting was changed during maintenance, we have corrected it,
> and no data was affected.
