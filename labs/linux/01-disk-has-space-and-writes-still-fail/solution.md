# Solution: the disk has space and the writes still fail

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| Running the export | It fails with `[Errno 28] No space left on device` | Nothing about which resource ran out |
| `df -h /var/spool/exports` | Blocks are at 0%, the customer was right | Nothing about files, only about their contents |
| `df -i /var/spool/exports` | Inodes are at 100%, 512 of 512 used | |
| The failure payload | `files_written: 511, files_expected: 5000` | |
| `EXPORT_ROWS_PER_FILE` | The job was told to put one row in each file | |

The two `df` invocations are the whole diagnosis, and neither means anything
without the other. Space is fine. Files are exhausted. Both are true, and only
the second matches the symptom.

Worth stating plainly, because it is what makes this expensive in practice: the
error message is not being unhelpful by accident. The kernel returns `ENOSPC`
when a filesystem cannot allocate a block *or* an inode, so "No space left on
device" is the correct wording for two entirely different problems. The message
names the failure. It never names the cause.

## Root cause

Last week's tuning work set `EXPORT_ROWS_PER_FILE` to `1`.

The export writes one file per chunk, so five thousand rows became five
thousand files. The spool directory has 512 inodes. The job got 511 files in
and then could not create another one, with the volume still empty because
each file holds twenty bytes.

The export is not too large. It is split into five thousand pieces.

## Scoped fix

In `labs/linux/_stack/compose.override.yaml`:

```yaml
services:
  worker:
    environment:
      EXPORT_ROWS_PER_FILE: "1000"
```

Then:

```bash
tse apply
tse check
```

Five files, six inodes used out of 512, and room to run again tomorrow.

**Not the fix:** raising the inode budget, or buying the storage the customer
offered to buy. Either would let tonight's run finish and leave a job that
creates one file per row in place, so the next larger export fails the same
way. The check asserts the directory is not left full for exactly this reason.

## Customer update

> Your export was failing because it ran out of file slots rather than
> out of space, which is why your team was right that the volume was nearly
> empty. A filesystem limits how many files it can hold separately from how
> much data it can hold, and the error message our job reported covers both
> cases without distinguishing them.
>
> The cause was a setting changed during last week's tuning work, which told
> the export to write one file per row. Your five thousand rows became five
> thousand files, and the directory allows five hundred and twelve. We have
> put the chunk size back, so the same data now writes as five files. Tonight's
> export will run normally.
>
> Please do not buy the additional storage. It would not have helped, and the
> setting was the whole problem. If you would like, I can send you the two
> commands that tell these apart, so your team can check both next time.

## Engineering escalation, if you needed one

> Impact: three consecutive nightly exports failed for Ardent Logistics, no
> data delivered, customer was about to purchase storage that would not have
> helped.
> Evidence: `[Errno 28] No space left on device` after 511 of 5000 files;
> `df -h` at 0% and `df -i` at 100% on the same directory.
> Confirmed: the volume has space, the job runs, the failure is reproducible.
> Ruled out: disk capacity, permissions, a data volume change.
> Suspected cause: `EXPORT_ROWS_PER_FILE` was set to 1 during tuning, making
> the job write one file per row.
> Request: the exporter reports ENOSPC without saying which resource was
> exhausted, which cost three nights and nearly cost the customer a storage
> purchase. Can it check free inodes before a run and say so in the failure.

That request is the durable part. The setting is fixed for this customer. The
next customer to hit this gets the same unhelpful message unless the job learns
to say which of the two things it ran out of.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
