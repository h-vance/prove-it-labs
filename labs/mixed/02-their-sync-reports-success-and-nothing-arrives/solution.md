# Solution: their sync reports success and nothing arrives

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `docker compose ls` | What is running, and where its files are | Nothing about the fault. This was orientation |
| `bash request.sh`, first line | The call returns `202 Accepted`, exactly as the customer reported | Nothing about what was accepted |
| `bash request.sh`, the body | `workspace` and `event` both came back `null` | Nothing yet about why |
| A deliberately unreadable payload | The service names the two fields it reads: `workspace` and `event` | |
| The customer's payload | Those values are sent as `workspace_id` and `event_type` | |

The customer's credentials were valid, their route was current, their JSON was
well formed, and their values were right. Every layer anyone would normally
suspect was working. That is what made this survive eight days of their team
looking at it.

Worth naming, because it is the habit this exercise exists to build: a success
status was treated as proof the request had done something. It is not. It is
proof the request was accepted. What the server understood is a separate
question, and the answer to it was sitting in the response body the whole time.

## Root cause

The customer's integration labels its fields `workspace_id` and `event_type`.
The service reads `workspace` and `event`.

The service takes the fields it recognizes and ignores the rest, which is
ordinary and mostly desirable behavior. An unrecognized field name is not an
error to it, so nothing was reported. The two fields it wanted were simply
absent, so it recorded an event with no workspace and no type, and answered
`202 Accepted` because the request itself was perfectly well formed.

Nothing was dropped after acceptance, which was the customer's theory. The
events arrived carrying nothing to identify them.

## Scoped fix

In `labs/api/_stack/request.sh`, label the values with the names the service
reads:

```bash
-d '{"workspace":"ws_4471","event":"order.created","id":"evt_9013"}'
```

Then:

```bash
tse check
```

The values do not change. Only the two field names do.

## Customer update

> Your job has been running correctly and the responses you logged were
> accurate. The problem is in the field names rather than anything failing. Your
> payload sends the workspace as `workspace_id` and the event as `event_type`,
> and our webhook endpoint reads those two values from `workspace` and `event`.
> Because the rest of the request is valid, our service accepted it and returned
> success, but the two values it needed to file the event were not present under
> the names it looks for. Nothing was dropped on our side after acceptance.
> Renaming those two fields will make the events appear. I have confirmed a test
> event end to end with the corrected names against your workspace. I am sorry
> this took eight days to surface. A success response that carries an empty
> result is a bad experience, and I have raised it with our API team.

## Engineering escalation, if you needed one

> Impact: one enterprise integration delivered zero usable events for eight
> days while receiving `202 Accepted` on every request.
> Evidence: `POST /v2/webhooks/events` returns 202 with `"workspace": null` and
> `"event": null` when the payload uses unrecognized field names.
> Confirmed: authentication, route version, payload validity, network delivery.
> Ruled out: anything dropping events after acceptance.
> Suspected cause: the endpoint accepts payloads whose required fields are
> absent, and reports success.
> Request: can the endpoint reject a webhook that carries neither `workspace`
> nor `event`, rather than accepting it. Silent acceptance means the customer
> cannot detect this and neither can we, and this one only surfaced because
> somebody eventually looked at an empty dashboard.

That request is the real outcome of this ticket. The field rename fixes one
customer. Rejecting an empty payload fixes everyone who makes the same mistake
next.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
