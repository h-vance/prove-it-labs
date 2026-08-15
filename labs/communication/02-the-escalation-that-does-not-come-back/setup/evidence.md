# Evidence: total outage with every signal green

This is the same incident as `mixed/01`, so you already know how it was proved.
Nothing here is new. What is new is who you are writing to.

The customer update went out this morning and committed you to raising the
cause internally. This is that escalation.

## Facts

The technical specifics, exactly as they were observed. An escalation that
paraphrases these makes the receiving engineer go and gather them again, which
is the entire cost it exists to save. Quote at least two.

- `127.0.0.1:8100->8081/tcp`
- `server_started port=8080`
- `Up (healthy)`
- `every request accepted and closed with no response`

## Ruled out

Eliminated with evidence during the incident.

- `application crash`
- `dependency failure`
- `credential or data problem`

## What actually happened

A release changed the container-side target of the published port from 8080 to
8081. The application listens on 8080 and always has. The forwarding layer
accepted connections on the published address and delivered them to a port with
nothing behind it.

The container health check runs inside the container and connects directly to
the application, so it never crossed the broken mapping and reported healthy
for the entire outage. Every dashboard was green while the service was totally
unavailable, from 06:00 until a customer told us at 09:12.

## Why this is worth an engineer's time

The one-digit fix is already in. What is not fixed is that no signal we own
could see this, and nothing stops the same edit shipping again next week.
