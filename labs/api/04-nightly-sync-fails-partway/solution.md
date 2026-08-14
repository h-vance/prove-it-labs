# Solution: nightly sync fails partway through

## What the evidence proved

| Evidence | What it proved | What it did not prove |
|---|---|---|
| First pages succeed, later ones fail | The credential and the route are fine | Nothing about the cause |
| The same **position** fails across runs | The failure is positional, not data-dependent | |
| `HTTP 429` | The API is deliberately throttling, not erroring | |
| `RateLimit-Limit: 5`, `RateLimit-Remaining: 0` | The exact budget and that it is spent | |
| `Retry-After: 11` | Precisely how long to wait | |
| Waiting and retrying returns `200` | The records are fine. Nothing is corrupt | |

## Root cause

The sync issues requests as fast as it can. The API allows 5 requests per
10-second window per key, so the first pages succeed, the budget is exhausted,
and every subsequent request is rejected with `429` until the window rolls over.
The client treats `429` as a permanent failure and drops the page, producing an
incomplete file.

This is not a fault on either side. The API is throttling correctly and the
client is not honoring the contract it is being told about.

## Why the customer's theory was wrong, and why it was reasonable

They concluded corrupt records because some requests worked. That is a sound
instinct, and the test that kills it is cheap: if bad records were the cause, the
failures would follow those records. They do not. They follow the **position in
the run**, which stays constant even as the data behind it changes.

The general rule worth keeping:

> When early requests succeed and later ones fail, suspect rate before data.

The other giveaway is in the customer's own message: the problem started when
their volume grew. Volume changes how many requests a run makes. It does not
usually corrupt anything.

## Scoped fix

The client must absorb throttling rather than fail on it. The API states exactly
how long to wait, so honor that value instead of guessing:

```bash
if [[ $status == "429" ]]; then
    wait_for=$(grep -i '^Retry-After:' /tmp/tse-page.headers | tr -d '\r' | awk '{print $2}')
    sleep "${wait_for:-2}"
    continue   # retry the same page, do not skip it
fi
```

Two mistakes to avoid, both common:

- **Retrying immediately.** This turns one throttled client into a permanently
  throttled one and can look like an attack.
- **Guessing a fixed delay.** `Retry-After` is authoritative. A guess is either
  too short, which fails again, or too long, which slows every run.

Then `tse check`.

## Customer update

> I reproduced the sync and your records are not corrupt. Every page that failed
> returns correctly when it is retried, including the ones in the middle of the
> run. The failures are our API rate limiting your client: the sync requests
> pages faster than the account's limit of 5 requests per 10 seconds, so once the
> budget is used the remaining requests are rejected until the window resets.
> This started when your volume grew because more records means more requests in
> the same burst.
>
> The fix is on the client side, and our API gives it the information it needs.
> When a request is rejected we return a `Retry-After` header stating how many
> seconds to wait. If the sync waits for that period and retries the same page,
> the run will complete. I would avoid retrying immediately, since that keeps the
> client throttled continuously.
>
> No usage data was lost. The records were never sent, so a completed run will
> pick them all up.

## Engineering escalation, if you needed one

> Impact: enterprise account's nightly usage export incomplete since their
> volume increase, blocking billing review.
> Evidence: `429` with `RateLimit-Limit: 5`, `RateLimit-Remaining: 0`, and
> `Retry-After` present; failures positional rather than record-linked; retried
> pages return `200` with valid data.
> Confirmed: authentication, routing, data integrity.
> Ruled out: corrupt records, credential expiry, partial outage.
> Suspected cause: client does not implement backoff on `429`.
> Request: confirm whether this account's rate limit is appropriate for their
> current volume, and whether our published integration guide documents
> `Retry-After` handling clearly enough to have prevented this.

## Say it out loud (90 seconds)

> The customer thinks they have corrupt records, and that is testable, so I
> would test it rather than argue. If specific records were the cause, the
> failures would follow those records. I would run the sync twice and check
> whether the same pages fail. They do, and the failing position stays constant
> while the data behind it does not, so it is positional rather than
> data-dependent. Then I would look at what the failing responses actually are,
> and they are 429s, which is not a fault, it is throttling. The headers give me
> the limit, what is remaining, and a Retry-After value. That also explains why
> this started when their volume grew: more records means more requests per run,
> so they now cross the limit where before they did not. The fix is on their
> side, in the client honoring Retry-After and retrying the same page rather than
> dropping it. For the customer I would lead with the fact that their data is
> intact, because that is what they are actually worried about, then explain the
> limit and the header, and ask internally whether their limit still suits their
> volume.
