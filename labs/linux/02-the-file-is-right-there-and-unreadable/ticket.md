## CUSTOMER TICKET: daily report stopped submitting and the config is untouched

**Account:** Ardent Logistics (enterprise)
**Impact:** no daily report submitted since the security work
**Started:** the morning after your hardening pass

> Our daily report has not gone out since your team did the security work last
> week. The job says it cannot read its own configuration.
>
> We checked, and the file is exactly where it has always been, with the same
> contents it has always had. Nobody has touched it. We can open it ourselves
> without any trouble.
>
> The only thing that changed is the security work, and your engineer told us
> that change was a no-op, that it just wrote down explicitly what was already
> the case. So either that is not true, or something else is going on.

**Your job**

1. Prove which account the process is running as, rather than which one you
   expect it to be running as.
2. Work out what the change actually changed. The engineer was not lying.
3. Restore the report with the smallest correct change, and keep the hardening.

**Working notes**

The job runs in the `worker` service. You can run it on demand:

```bash
docker compose -f labs/linux/_stack/compose.yaml \
               -f labs/linux/_stack/compose.override.yaml \
               exec worker python3 /app/reporter.py
```

The security change is in `labs/linux/_stack/compose.override.yaml`. After
editing, run `tse apply`, then `tse check`.

Running the service as a more powerful account would make the error go away.
Do not. The grader checks for it, and so would a reviewer.
