# Solution: the dashboard is green and one customer is timing out

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `/metrics` | 100 requests, 5 slow, 95% within the objective | Nothing about any individual account |
| `/metrics?tenant=northwind` | 5 requests, 5 slow, 0% within the objective | |
| `/metrics?tenant=contoso` | 5 requests, none slow, 100% | That slow is normal here, which is what rules out a capacity problem |
| `/v1/reports?tenant=northwind` | Correct data, and `config_source: directory` | |
| `/v1/reports?tenant=contoso` | Same data shape, and `config_source: local` | |
| `logs downstream | grep directory` | Directory lookups happen for one account and no other | |

The two readings are the diagnosis, and neither means anything without the
other. Ninety-five percent of requests met the objective. Zero percent of this
customer's did. Same service, same instant, both correct.

That is worth stating plainly because it is what made this expensive. Nobody
was being lazy. The reading everybody quoted was accurate and it was answering
a question the customer had not asked. An account that is one twentieth of the
traffic can be entirely unusable while costing the overall figure five points,
which is not enough to turn anything red.

The third reading is the one that turns an observation into a diagnosis.
Knowing this account is worse than average tells you nothing you did not
already believe. Knowing another account is at a hundred percent tells you slow
is not normal here, which rules out capacity, load, and a bad afternoon, and
leaves only things the service does per account.

## Root cause

`northwind` was missing from `tenants.json`, the service's local copy of who
its customers are.

When an account is not in that copy, the service falls back to the
authoritative directory. The fallback is correct and returns exactly the right
plan and limits. It also takes a second and a half, it runs on every single
request, and nothing caches it. So the account was never broken in the sense of
returning anything wrong. It was answered from the slow path, every time, since
the day they were onboarded.

Nothing about this is a bug in the fallback. A service without one would simply
fail for any account added since the local copy was last written. The bug is
that an onboarding step did not finish, and that nothing noticed for a week
because no reading was scoped to the account it affected.

## Scoped fix

Add them to `labs/observability/_stack/tenants.json`, with the values the
directory holds for them:

```json
"northwind": {
  "plan": "enterprise",
  "row_limit": 50000
}
```

Then:

```bash
tse apply
tse check
```

Their requests drop from about 1.5 seconds to about 15 milliseconds, and
`config_source` changes from `directory` to `local`.

**Not the fix:** adding them with a placeholder or with a row copied from
another account. It resolves locally, the latency disappears completely, the
customer stops complaining, and an enterprise account is quietly running on a
starter row limit. That surfaces weeks later as a truncated report and is a far
worse ticket than a slow one. The check reads the plan and the limit for
exactly this reason.

## Customer update

> You were right, and I am sorry it took three tickets to get here.
>
> Our dashboard reports across all traffic, and your account is a small share
> of it, so an account that is completely slow moves that number by about five
> points. It stayed green while every one of your requests was over a second.
> Both things were true, and we were only looking at the one that could not
> answer your question.
>
> Here is what we can see for your account specifically: of your last five
> requests, all five were over our one second target, against ninety-five
> percent of all traffic meeting it. That is the reading we should have pulled
> the first time you raised it.
>
> The cause was on our side. When your account was set up, it was not added to
> the service's local record of customer configuration, so every request was
> looking your details up from our directory rather than reading them locally.
> You were always getting the correct plan and limits, just by the slow route,
> every single time.
>
> That is now corrected and your reports return in a few hundredths of a second.
> Nothing changed about what they contain or what you are entitled to. If your
> month end close needs anything rerun, tell me which reports and I will confirm
> the timings myself.

## Engineering escalation, if you needed one

> Impact: one enterprise account had every request served from the directory
> fallback for at least a week. Three tickets, two closed as working as
> intended, month end close delayed.
> Evidence: `within_objective_pct` 95.0 overall and 0.0 for this account, from
> the same endpoint at the same time; `config_source: directory` on their
> reports and `local` on everybody else's; directory lookups in the renderer's
> log for one account only.
> Confirmed: correct data returned throughout, one and a half seconds per
> request, reproducible on every request.
> Ruled out: capacity and load, since another account was at 100% in the same
> window. Their client, their reports, and the size of their data.
> Suspected cause: onboarding did not add them to `tenants.json`, and the
> fallback made that invisible by being correct.
> Request: two things, and the second matters more. The fallback has no cache,
> so a missing entry costs a second and a half on every request forever rather
> than once. And nothing alerts on an account whose objective rate is zero while
> the overall rate is healthy, which is the shape of every ticket like this one.

The missing entry is fixed for this customer. What will happen again is the
next account onboarded with a step skipped, and the reason nobody caught it for
a week is that every dashboard was measuring the service instead of its
customers.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
