# Solution: two reports disagreeing

## What the evidence proved

| Query | What it proved | What it did not prove |
|---|---|---|
| `SELECT count(*) FROM customers WHERE plan='enterprise'` | 12 is the true figure | Which report is wrong, until compared |
| The active accounts report | Returns 108, so it is the inflated one | What it is counting instead |
| The same joins without `GROUP BY` | Each customer appears once per user | |
| Users per workspace | Nine for enterprise, two for the rest | Which matches the 9x and 2x inflation exactly |

The customer's instinct that the larger number was "picking up something extra"
happened to be right, but it was a guess. Verifying independently is what turns
it into a diagnosis, and roughly half the time in this situation the smaller
number is the wrong one instead.

## Root cause

The active accounts report joins customers to workspaces to users. That
relationship is one-to-many, so each customer row is multiplied into one row per
user **before** any aggregate runs. `COUNT(*)` then counts result rows, which
are users, while the report's title claims they are customers.

The inflation factor is not random, and that is what makes it identifiable:
enterprise accounts have nine users each and were inflated roughly ninefold,
the smaller plans have two and were inflated roughly twofold.

## Scoped fix

```sql
SELECT c.plan, COUNT(DISTINCT c.id) AS customer_count
FROM customers c
JOIN workspaces w ON w.customer_id = c.id
JOIN users u ON u.workspace_id = w.id
GROUP BY c.plan
ORDER BY c.plan;
```

The joins stay. The report is "customers with at least one user", and
establishing that genuinely requires walking to the users table. What changes is
what gets counted once you are there.

Note the corrected report returns 6 starter accounts, not 12. That is correct
and is not the previous ticket's bug: the other six starter accounts have no
users, and this report is deliberately about the ones that do. Two reports can
legitimately disagree when they are asking different questions, which is exactly
why naming the question precisely matters.

## Customer update

> The figure you can use is 12. I verified it against the account records
> directly rather than trusting either report.
>
> The active accounts report was counting user records rather than accounts.
> It walks from accounts through to users to establish which accounts have at
> least one user, and in doing so it produces one row per user, so a
> twelve-account plan with nine users each was reported as 108. The plan mix
> report was never affected because it does not walk that far.
>
> The report now counts accounts and returns 12. One thing to note: it shows 6
> starter accounts rather than 12, and that is correct, because six starter
> accounts have no users yet and this report is specifically about accounts that
> do. If you need the total including those, that is the plan mix report.

## Engineering escalation, if you needed one

Not an incident. Worth raising with whoever owns the reporting suite that the
two reports have similar titles and answer materially different questions, which
is what let this sit unnoticed.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
