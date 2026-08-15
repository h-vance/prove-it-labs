## CUSTOMER TICKET: nightly export failing, but you say the disk is fine

**Account:** Ardent Logistics (enterprise)
**Impact:** no exports delivered for three nights
**Started:** since the tuning work last week

> Our export has failed three nights running. The message in your job output
> says there is no space left, so we asked our own team to check and they say
> the volume is almost empty, under one percent used. We have looked twice.
>
> Someone suggested we buy more storage, which we are happy to do, but we would
> rather not spend the money on something that is apparently already empty.
> Please tell us what is actually full.

**Your job**

1. Prove which resource ran out. The error names the failure, not the cause.
2. Do not resize anything until you can say what would fill up again.
3. Restore the export with the smallest correct change, then confirm it can
   run again tomorrow rather than only once.

**Working notes**

The job runs in the `worker` service. You can run it on demand:

```bash
docker compose -f labs/linux/_stack/compose.yaml \
               -f labs/linux/_stack/compose.override.yaml \
               exec worker python3 /app/exporter.py
```

Its configuration is in `labs/linux/_stack/compose.override.yaml`. After
editing, run `tse apply`, then `tse check`.
