# Solution: a report that was instant is now painful

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `EXPLAIN (ANALYZE, BUFFERS)` on the report | The plan contains `Seq Scan on api_requests` | Nothing about the query's correctness |
| Rows examined against rows returned | 300,000 read to return 7,500 | Nothing about why nothing better exists |
| `\d api_requests` | Nothing indexes `customer_id` | |
| The same plan after indexing | `Bitmap Index Scan`, and the row counts are unchanged | |
| Running the report itself | 7,500 requests averaging 191ms, before and after | That the fix altered no results |

The timing is the least useful number here and the customer already had it.
The plan is what answers the question they actually asked.

## Root cause

Nothing supports looking up rows by `customer_id`, so the only way PostgreSQL
can answer "requests for one account in one week" is to read every row in the
table and discard the ones that do not match. It read 300,000 rows to return
7,500.

The query was never wrong. It has always been a full scan, and a full scan on a
small table is instant. What changed is the table: the cost of that scan is the
size of `api_requests`, and `api_requests` grows every day. That is precisely
why it degraded gradually rather than breaking on a particular date, and why
nobody could point at a change that caused it.

## Why timing was the wrong instrument

At today's size the scan finishes in about 14 milliseconds and the indexed
lookup in about 4. A stopwatch would have told you this is fine.

The customer did not ask whether it is fine today. They asked where it ends up
in six months, and the plan answers that directly: a sequential scan is work
proportional to the table, and an index lookup is not. One of those curves bends
and the other does not.

This is the general lesson. Timing tells you what happened once, on this
machine, with this cache state. The plan tells you what will keep happening.

## Scoped fix

```sql
CREATE INDEX IF NOT EXISTS idx_api_requests_customer_time
    ON api_requests (customer_id, requested_at);
```

Column order is deliberate. The equality predicate comes first, then the range,
so the index can seek straight to one account and then walk the time window
inside it. Reversed, the range would have to be scanned across every account.

Then confirm two things rather than one: that the plan changed, and that the
numbers did not. An index that changes your results is not an index, it is a
bug.

## Cost worth stating out loud

An index is not free. It consumes disk, and every insert into `api_requests`
now has to maintain it. On a write-heavy request log that is a real trade, and
it is the customer's trade to make rather than yours to make silently. Here the
table is read for reporting far more often than any single row is written, so
it is clearly worth it, but say so rather than assume it.

## Customer update

> Your instinct that this is about growth rather than a change was exactly
> right, and it is the reason nothing showed up in the deploy history.
>
> The report has always worked by reading the entire request history and
> keeping the rows for the account you asked about. That is instant when the
> history is small, and it gets steadily slower as the history grows, which
> matches what you have been feeling. To answer your real question: it would
> have kept getting worse in direct proportion to how much history you
> accumulate.
>
> We have added an index so the database can go straight to one account's rows
> instead of reading all of them. The report now returns the same numbers,
> which I verified, and the work it does no longer grows with the size of the
> table.
>
> One thing to be aware of: an index costs a little storage and a little
> overhead on every write. For a table you report from this often that is a
> clear win, but if you would like the same treatment on other reports, tell me
> which and I will look at each rather than indexing everything by reflex.

## Engineering escalation, if you needed one

> Impact: gradual degradation of the per-account usage report, not yet
> user-blocking, on a trajectory that does not improve.
> Evidence: plan shows `Seq Scan on api_requests`, 300,000 rows examined for
> 7,500 returned; no index covers `customer_id`; results identical before and
> after indexing.
> Confirmed: query correctness, result stability, absence of a schema or code
> change.
> Ruled out: a regression, a data quality problem, resource pressure.
> Suspected cause: the access pattern was never indexed, and the table has
> grown past the point where a full scan is acceptable.
> Request: confirm whether other reports filter `api_requests` by account, and
> whether a retention policy on request history is planned, since that changes
> whether indexing or pruning is the better answer long term.

## Say it out loud (90 seconds)

> The customer has told me nothing changed except the volume of data, which
> rules out a regression and points at how the work scales rather than what the
> work is. I would deliberately not reach for a stopwatch, because timing tells
> me about today and they asked me about six months from now. Instead I would
> ask the database how it intends to answer the question, with EXPLAIN ANALYZE,
> and I would note that on a write statement that actually executes it, so it
> belongs in a transaction you roll back. Here the plan shows a sequential scan
> reading 300,000 rows to return 7,500, which means nothing exists that lets it
> find one account directly. That explains the gradual decline exactly, because
> the cost of a scan is the size of the table. The fix is an index on the
> account column and then the timestamp, in that order, so it can seek and then
> walk the time window. I would verify the plan changed and the numbers did not,
> and I would tell the customer the index has a small write cost rather than
> letting them discover it.
