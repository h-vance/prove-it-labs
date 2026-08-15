# Solution: the escalation that does not come back

## What the evidence proved

Nothing to investigate again. The incident was `mixed/01` and the notes were
handed to you. What was under test is whether an engineer can act on what you
wrote.

| Rule | What it is really asking |
|---|---|
| Answers every question an engineer will ask | Can this be picked up, or does it need a reply first |
| Quotes the technical specifics | Did you send observations, or conclusions |
| Names something ruled out | Will somebody waste an hour re-checking what you already eliminated |
| Ends with a request and an owner | Is there anything here to assign |
| Is the right length | Is the detail actually present |

Note what is missing compared to `communication/01`. There is no rule against
internal vocabulary here, and the rule about specifics is its mirror image. The
same module grades both, driven by the exercise's own evidence file, which is
the only reason one linter can hold two nearly opposite standards.

## Root cause

The returned draft was a customer update sent to an engineer.

Every instinct that made the last exercise's message good made this one
useless: it softened the specifics, replaced observations with a conclusion,
and closed on a polite non-request. Priya could not have assigned it to anybody,
so she sent it back, which is the cheapest possible outcome. The expensive
version is the one that gets triaged, half understood, and quietly deprioritized.

## Scoped fix

Rewrite `labs/communication/_stack/escalation.md` under six labels: impact,
evidence, confirmed, ruled out, suspected cause, request. Quote at least two
observations verbatim from `evidence.md` rather than describing them.

Then:

```bash
tse check
```

## Customer update

None owed. The customer was updated in `communication/01`, and this escalation
is what that update committed you to. The only thing that reaches them from
here is whether you can hold the date you gave, which is why the request asks
Priya what is realistic rather than telling her what you need.

## Engineering escalation, if you needed one

This is the artifact, so here it is in full:

> **Impact:** Halden Freight, enterprise, total loss of service for all users
> from 06:00 to 09:12. Every request was accepted and closed with no response.
> Found by the customer, not by us.
>
> **Evidence:** the published mapping was `127.0.0.1:8100->8081/tcp` while the
> application logged `server_started port=8080` on the way up. Requests to the
> published address returned nothing. The container reported `Up (healthy)`
> throughout, because the health check runs inside the container and connects
> straight to the application, never crossing the mapping that was wrong.
>
> **Confirmed:** application process health, clean application startup, database
> availability, and that the fault was entirely in the published mapping.
>
> **Ruled out:** application crash, dependency failure, credential or data
> problem.
>
> **Suspected cause:** last night's release changed the container-side target of
> the published port from 8080 to 8081. The application has always listened on
> 8080.
>
> **Request:** two things, and the second matters more than the first.
>
> 1. The one-digit fix is already in. Please confirm whether the same edit exists
>    in any other service that shares this release template, because one
>    misconfigured service is an incident and a shared template is an outage
>    waiting for the next deploy.
>
> 2. We have no signal that can see this class of fault. Every check we own runs
>    inside the container and passed for three hours while the service was
>    completely unreachable. A check that connects from outside the published
>    address would have caught this in seconds. Can the platform team own adding
>    one, and tell me what is realistic, so I can hold to the date I gave the
>    customer.

The second request is the one that makes this escalation worth writing. The
first closes an incident. The second closes a class of incident, and it is
available to you only because you noticed that every signal was green.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
