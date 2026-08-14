# Solution: integration rejected with an authentication error

## What the evidence proved

| Evidence | What it proved | What it did not prove |
|---|---|---|
| A status line came back at all | The API is up. The outage theory is disproven | Nothing about the credential |
| `HTTP 401` | The credential was refused | Which of three refusals it was |
| `"code": "api_key_revoked"` | The key was valid and has been withdrawn | Who revoked it or why |
| `"detail": "... revoked on 2026-08-12"` | The revocation date matches when events stopped | |
| `credentials.md` | An active key was issued the same day | |

## Root cause

The customer's webhook integration authenticates with an API key that was
revoked on 2026-08-12 during a scheduled rotation. A replacement key was issued
at the same time, but their integration was never updated to use it, so every
delivery since has been refused.

The customer was right that nothing changed on their side. That is exactly the
problem: something changed on ours and their side did not follow.

## Scoped fix

Point the integration at the active key. In `labs/api/_stack/request.sh`:

```bash
API_KEY="wk_live_active_3c95"
```

Then `tse check`. In production the customer updates the secret in their own
configuration. You do not send them a key over a support channel: you tell them
which key is current and where to retrieve it.

## What "401" actually covered

Worth keeping, because this is asked directly in interviews:

| Code | Meaning | Who acts |
|---|---|---|
| `api_key_missing` | No credential sent | Customer's integration |
| `api_key_invalid` | Not recognized, often wrong environment | Customer, usually a typo |
| `api_key_revoked` | Was valid, deliberately withdrawn | Whoever rotated it |

Reporting all three as "authentication failure" throws away the part that
decides who fixes it.

## Customer update

> I reproduced the failure and the API is responding normally, so there is no
> outage. The calls are being refused because the API key your integration uses
> was revoked on 12 August as part of a scheduled key rotation, which matches
> the date your events stopped arriving. A replacement key was issued at the
> same time. Once your integration is updated to the current key, deliveries
> will resume. Your workspace admin can retrieve it from the API keys page. No
> events were lost on our side, but events sent during this window were not
> accepted and will need to be resent.

That last sentence matters. The customer's real question is whether they lost
data, and answering it before they ask is most of what makes an update good.

## Engineering escalation, if you needed one

You would not escalate this one, and knowing that is part of the exercise. It
resolves at first contact. Escalate only if the rotation was not communicated,
in which case the issue is the notification process rather than this account:

> Impact: one enterprise integration silently failing since 2026-08-12.
> Evidence: `401` with `api_key_revoked`, revocation date matching the outage
> start, request_id captured.
> Request: confirm which customers were notified of the 2026-08-12 rotation, as
> this account appears not to have been.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
