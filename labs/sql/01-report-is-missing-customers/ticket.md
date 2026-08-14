## CUSTOMER TICKET: our plan mix report is undercounting

**Account:** internal, raised by the finance team
**Impact:** monthly board reporting is wrong
**Started:** noticed during this month's close

> The plan mix report says we have 34 accounts. We have 40. I checked the
> account list by hand twice. The enterprise and growth numbers look right to
> me, it seems to be the smaller plans that are off, which makes even less
> sense. Nothing about this report changed as far as I know.

**Your job**

1. Establish the true numbers independently before you read the report.
2. Prove where the rows are being lost.
3. Correct the report so it answers the question that was asked.

**Working notes**

The support database is on `127.0.0.1:5434`, database `support_lab`, user
`support`. The report lives in `labs/sql/_stack/query.sql`. Edit it, then run
`tse check`, which executes exactly that file. To explore interactively:

```bash
docker compose -f labs/sql/_stack/compose.yaml exec -e PGPASSWORD=demo-password \
  postgres psql -U support -d support_lab
```
