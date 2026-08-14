# Solution: lookups return not found for accounts that exist

## What the evidence proved

| Evidence | What it proved | What it did not prove |
|---|---|---|
| `HTTP 404` | Something was not found | Whether it was the record or the route |
| `"code": "route_not_found"` | Nothing serves that path. The lookup never ran | Nothing about the account |
| `Sunset: Sat, 01 Aug 2026` | The route was withdrawn on a specific date | |
| `Link: </v2>; rel="successor-version"` | What replaced it | |
| Same ID against `/v2` returns the record | The data was always fine | |

## Root cause

The customer's tool calls `/v1/customers/{id}`. The v1 API was withdrawn on
1 August 2026 and the current API is served under `/v2`. Every lookup has failed
since that date. The account records were never missing.

The customer said nothing changed on their side, which is true. The change was
on ours, and their integration had no reason to notice until someone looked.

## The distinction that decides the ticket

A `404` is an answer about an **address**, and there were two candidate
addresses. Reading the error code rather than the status separated them
immediately:

- `record_not_found` would mean the route worked and the account did not exist.
  That would be a data question.
- `route_not_found` means the request never reached account lookup at all. That
  is a routing and versioning question.

Everything after that follows from picking the right branch.

## Read the headers

The most useful evidence here was not in the body:

```bash
curl -i http://127.0.0.1:8101/v1/customers/cus_8823
```

`Sunset` (RFC 8594) declares when a resource stops being served. `Link` with
`rel="successor-version"` names the replacement. A deprecating API that sets
these is telling you the answer directly, and most people never look, because
the body is what gets printed in application logs.

## Scoped fix

In `labs/api/_stack/request.sh`, call the current version:

```bash
curl ... "$API/v2/customers/cus_8823"
```

Then `tse check`.

## Customer update

> I reproduced the failure and the accounts are not missing. Your tool is
> calling version 1 of our API, which was withdrawn on 1 August, so those
> requests are being rejected before any account lookup happens. That is why the
> IDs look correct and still return not found. Pointing the integration at
> `/v2` resolves it, and I have confirmed the same account IDs return correctly
> there. The response format for this endpoint is unchanged, so it should be a
> path change only.
>
> One thing worth flagging: this has been failing since 1 August rather than
> since this morning, so it is worth checking whether anything else in your
> tooling still calls the older version. I am happy to review a list of the
> endpoints you use.

That closing offer is the difference between fixing a ticket and preventing the
next four.

## Engineering escalation, if you needed one

Not for the account. Possibly for the process:

> Impact: enterprise customer integration failing silently for two weeks after
> the v1 withdrawal.
> Evidence: `404 route_not_found` on `/v1/customers/{id}` with `Sunset`
> 2026-08-01; the same IDs resolve on `/v2`.
> Request: confirm whether v1 callers were identified and notified before the
> withdrawal date, and whether other accounts are still calling v1 today.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
