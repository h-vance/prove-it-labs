# Solution: service unavailable after a release

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `docker ps` | The app container is not running now | Nothing about whether it ever ran |
| `docker ps -a` | The container exists and is cycling, so the image resolved and the container was created | Nothing about why it exits |
| `docker compose logs app` | The process exits deliberately with `required environment variable APP_SECRET is not set` | Nothing about who changed it |
| `cat compose.override.yaml` | `APP_SECRET` is present but set to an empty string | Nothing about intent |

The important distinction: the variable was **not missing**. It was declared
and empty. That is why a quick scan of the release diff looks fine, and it is
why the application treats it as unset.

## Root cause

The release applied an override that declared `APP_SECRET` with an empty value.
The application validates required configuration at startup and exits rather
than running in an unknown security state. The `restart: on-failure` policy then
retried it, producing a container that appears intermittently rather than a
clean, obvious failure.

## Scoped fix

In `labs/docker/_stack/compose.override.yaml`:

```yaml
services:
  app:
    environment:
      APP_SECRET: "lab-secret"
```

Then:

```bash
tse apply
tse check
```

Nothing else needs to change. Resist widening the fix: the database, the port
mapping, and the image were all proven healthy by the evidence above.

## Customer update

> The dashboard outage was caused by a configuration value that was cleared
> during this morning's release. The application is designed to stop rather than
> start with incomplete security configuration, which is why it never came back
> up. We have restored the value and confirmed the customer dashboard is loading
> your data correctly. No data was lost and nothing on your side needs to change.
> I will follow up by 13:00 to confirm it is still stable ahead of your 14:00
> review.

Note what this does **not** say: it does not blame a person, it does not
speculate about how the value was cleared, and it does not promise it cannot
recur.

## Engineering escalation, if you needed one

> Impact: complete outage of the customer dashboard from 09:14.
> Evidence: `app` container in a restart loop; startup log line
> `ERROR: required environment variable APP_SECRET is not set`; the applied
> compose override declares `APP_SECRET: ""`.
> Confirmed: image resolved, container created, database healthy and reachable.
> Ruled out: image tag, port mapping, database availability.
> Suspected cause: the release pipeline emitted an empty value for a required
> secret rather than failing the deploy.
> Request: confirm whether the pipeline should fail closed when a required
> secret resolves empty.

## Say it out loud (90 seconds)

> I would first prove whether the application process ever started, because a
> timeout is equally consistent with a crash, a hang, and a routing problem. The
> first evidence I would check is `docker ps -a`, because it shows containers
> that exited or are restarting, which `docker ps` hides. If I see the container
> cycling, I read its logs, since a process that fails a precondition normally
> says so before exiting. Here the log names a required configuration value, and
> the applied config shows that value present but empty. My safe next step is to
> restore the value and recreate only that service. For the customer I would say
> the outage came from a configuration value cleared during the release, that
> service is restored, and that I will confirm stability before their review.
