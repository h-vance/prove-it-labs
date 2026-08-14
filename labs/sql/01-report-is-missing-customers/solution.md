# Solution: a report quietly missing customers

## What the evidence proved

| Query | What it proved | What it did not prove |
|---|---|---|
| `SELECT count(*) FROM customers` | 40 customers exist. The finance team was right | Nothing about the report |
| The report's own output | It returns 34, and only the smaller plans are short | Where the six went |
| `LEFT JOIN ... WHERE w.id IS NULL` | Exactly six customers have no workspace | |
| Their plan values | All six are on smaller plans, which explains the pattern | |

Establishing the true total first is what made the rest quick. Starting from
the report invites you to explain why it is correct.

## Root cause

The report joins `workspaces` to reach data it does not use. An inner join
keeps only rows with a match on both sides, so the six customers who have not
created a workspace yet are discarded before the count runs.

Nothing errored, because nothing is wrong with the SQL. It is valid, it runs,
and it answers a subtly different question: not "how many customers are on each
plan" but "how many customers who have a workspace are on each plan".

The pattern the finance team noticed is real and was the best clue in the
ticket. The six accounts without workspaces are all recent, and recent accounts
skew to smaller plans, so the loss concentrated there.

## Scoped fix

```sql
SELECT c.plan, COUNT(DISTINCT c.id) AS customer_count
FROM customers c
LEFT JOIN workspaces w ON w.customer_id = c.id
GROUP BY c.plan
ORDER BY c.plan;
```

`LEFT JOIN` keeps customers with no workspace. `COUNT(DISTINCT c.id)` keeps the
answer correct if an account ever gains a second one, which an inner join
against a growing table will eventually cause.

Dropping the join entirely also works here and is arguably cleaner. Keeping it
is the more defensive choice if the report is expected to grow workspace
columns later.

## Customer update

> You were right, and the pattern you spotted was the key to it. The report
> only counts accounts that have created a workspace, and six of ours have not
> yet. Those six are all recent signups, which is why the shortfall showed up in
> the smaller plans and the enterprise and growth numbers looked fine.
>
> The report now counts every account regardless of workspace, and returns 40.
> Nothing was wrong with the underlying account data, so no previous month's
> account list was affected, only this report's view of it.
>
> Worth checking whether any other report joins through workspaces the same way,
> because it would undercount identically and just as quietly. Send me the list
> and I will go through them.

## Engineering escalation, if you needed one

You would not escalate this. It resolves at first contact and the fix is a
query change. If the same join pattern turns out to be copied across a reporting
suite, that is worth raising as a review item rather than an incident.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
