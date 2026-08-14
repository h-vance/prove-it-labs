## CUSTOMER TICKET: two reports disagree and I do not know which to trust

**Account:** internal, raised by the sales operations team
**Impact:** account planning is blocked
**Started:** this morning

> The active accounts report says we have 108 enterprise accounts. The plan mix
> report says 12. Both of these are supposed to be counting our customers and
> they cannot both be right. I would assume the bigger one is picking up
> something extra, but I genuinely do not know which one to believe, and I need
> a number I can put in front of the leadership team on Thursday.

**Your job**

1. Establish the true number independently before trusting either report.
2. Prove what the wrong one is actually counting.
3. Correct it so it answers the question its title claims.

**Working notes**

The support database is on `127.0.0.1:5434`, database `support_lab`, user
`support`. The report lives in `labs/sql/_stack/query.sql`. Edit it, then run
`tse check`, which executes exactly that file. To explore interactively:

```bash
docker compose -f labs/sql/_stack/compose.yaml exec -e PGPASSWORD=demo-password \
  postgres psql -U support -d support_lab
```
