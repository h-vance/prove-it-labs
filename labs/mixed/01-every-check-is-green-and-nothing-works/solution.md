# Solution: every check is green and nothing works

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `docker compose ls` | What is running, and which files configure it | Nothing about the fault. This was orientation |
| `docker ps` | The container is up and its health check reports healthy | Nothing about whether anyone outside can reach it |
| `curl http://127.0.0.1:8100/customers` | The connection is accepted and closed with no reply | Nothing about which side closed it |
| `docker compose logs app` | The application started cleanly and is serving requests on `8080` | Nothing about which address those requests arrive on |
| `docker ps --format '{{.Ports}}'` | Traffic to `8100` is forwarded to `8081` inside the container | |

The last two lines are the whole diagnosis, and neither means anything alone.
The application is listening on one port. The published mapping delivers to a
different one. Every request is handed to a port with nothing behind it.

Worth stating plainly, because it is the habit this exercise is built to
break: the health check passing was never evidence that the customer could
reach anything. It runs inside the container and connects directly to the
application, so it never crosses the mapping that is broken. It was telling the
truth about a narrower question than the one being asked.

## Root cause

Last night's change edited the published address and set the container-side
target to `8081`. The application listens on `8080` and always has.

The forwarding layer accepts connections on `127.0.0.1:8100` because the
mapping exists, then tries to deliver them to `8081` inside the container,
where nothing is listening. The connection is closed with nothing sent, which
is why the customer described it as pages returning nothing rather than as an
error.

Everything inside the container stayed healthy throughout, because nothing
inside the container was wrong.

## Scoped fix

In `labs/docker/_stack/compose.override.yaml`, point the mapping at the port
the application actually listens on:

```yaml
services:
  app:
    ports: !override
      - "127.0.0.1:8100:8080"
```

Then:

```bash
tse apply
tse check
```

`!override` is there because Compose adds published ports from a second file to
the ones in the first rather than replacing them. Without it you get two
mappings competing for the same published address, which fails in a new and
more confusing way.

## Customer update

> The outage was caused by a configuration change in last night's release. The
> address our platform publishes for your service was pointed at the wrong
> internal port, so connections were accepted and then dropped before reaching
> the application. That is why pages returned nothing rather than an error, and
> why our own health checks stayed green: those run inside the service and were
> not affected by the change. We have corrected the address and confirmed your
> user list is loading. No data was affected at any point. We are also reviewing
> why our external checks did not catch this, since your experience should not
> have been the first signal.

## Engineering escalation, if you needed one

> Impact: total loss of service for all users from roughly 06:00, every request
> accepted and closed with no response.
> Evidence: container healthy throughout; application logs show a clean start
> and `port=8080`; published mapping is `127.0.0.1:8100->8081/tcp`; requests to
> `8100` return an empty reply.
> Confirmed: application process health, application startup, database
> availability.
> Ruled out: application crash, dependency failure, credential or data problem.
> Suspected cause: the release changed the container-side target of the
> published port from 8080 to 8081.
> Request: our health checks cannot see this class of fault, because they run
> inside the container. Can we add a check that connects from outside the
> published address, so the next one is caught by us rather than by a customer.

That last request is the part that stops this recurring. The fix takes one
digit. The monitoring gap is what let it run from 06:00 until a customer
complained.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
