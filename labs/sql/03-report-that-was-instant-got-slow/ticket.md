## CUSTOMER TICKET: per-account usage report has become painful

**Account:** internal, raised by the support team
**Impact:** the report is still usable but noticeably worse
**Started:** gradually, over the last few months

> The per-account usage summary used to come back immediately. It has been
> getting steadily worse and now there is a real pause every time we run it.
> Nobody has changed the report. The only thing that has changed is that we
> have a lot more history than we did. I am mostly worried about where this
> ends up in six months rather than how it feels today.

**Your job**

1. Prove how the database is answering the question, not just how long it took.
2. The customer's real question is about the trend, so answer that one.
3. Make the report answerable without reading everything, and verify the
   numbers did not change.

**Working notes**

The support database is on `127.0.0.1:5434`, database `support_lab`, user
`support`. The report lives in `labs/sql/_stack/query.sql`. Edit it, then run
`tse check`, which executes exactly that file. To explore interactively:

```bash
docker compose -f labs/sql/_stack/compose.yaml exec -e PGPASSWORD=demo-password \
  postgres psql -U support -d support_lab
```
