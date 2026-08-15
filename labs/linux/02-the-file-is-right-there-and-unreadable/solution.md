# Solution: the file is right there and unreadable

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| Running the report | `[Errno 13] Permission denied` on a path that exists | Nothing about who was denied |
| `ls -l` on the file | Owned `root:reporting`, mode `0640`, unchanged | Nothing about the reader |
| `id` inside the container | `uid=1000(app) gid=1000(app) groups=1000(app)` | |
| The hardening change | `user: "1000:1000"`, the same two numbers as before | |

The customer's three claims were all true. The file is there, it is unchanged,
and they can open it. None of them was ever evidence about this process, which
is the distinction the exercise exists to build.

The engineer's claim was also true, and more interestingly so. `user:
"1000:1000"` really does name the user and group the service already had. It
looks like writing down what was already the case, and for those two numbers it
is.

## Root cause

Naming a user and a group explicitly replaces the process's entire group
membership with exactly those, which drops every supplementary group the image
had configured.

The image puts `app` into `reporting` on purpose, because `reporting` owns the
credentials file at mode `0640`. After the hardening pass the process ran as the
same user, with the same primary group, and with that membership gone:

```
before  uid=1000(app) gid=1000(app) groups=1000(app),2000(reporting)
after   uid=1000(app) gid=1000(app) groups=1000(app)
```

Two of the three parts of the identity were preserved. The third was silently
discarded, and it was the one granting access.

## Scoped fix

In `labs/linux/_stack/compose.override.yaml`, keep the hardening and restore
what it removed:

```yaml
services:
  worker:
    user: "1000:1000"
    group_add:
      - "2000"
```

Then:

```bash
tse apply
tse check
```

**Not the fix:** running the service as root. It makes the error go away, and
it undoes a security change in order to solve a group membership problem. The
check asserts the process is still uid 1000 for exactly that reason.

Also not the fix: loosening the file to `0644`. That grants every account on
the machine read access to a credential in order to grant one account the
access it was already supposed to have.

## Customer update

> Your daily report stopped submitting because the service lost its membership
> of the group that owns its configuration file. You were right that the file
> is untouched, and our engineer was right that the change looked like a no-op:
> it pinned the service to the same account it was already using. What it also
> did, which is not obvious, is reset the list of additional groups that account
> belongs to, and one of those was what allowed it to read the file.
>
> We have restored that group membership and kept the security change in place.
> Your report submitted successfully on the next run. Nothing about the file or
> its contents was altered at any point, and no other account gained access to
> it as part of the fix.
>
> I will check whether the same hardening was applied to any other service that
> depends on group membership, and come back to you by Wednesday either way.

## Engineering escalation, if you needed one

> Impact: daily report submission failed for Ardent Logistics from the morning
> after the hardening pass, no reports delivered since.
> Evidence: `[Errno 13] Permission denied` on `/etc/reporting/credentials.conf`,
> which is `root:reporting` mode `0640`; `id` in the container reports
> `groups=1000(app)` where the image configures `1000(app),2000(reporting)`.
> Confirmed: the file is present and unchanged, the service runs, the account
> and primary group are what the hardening intended.
> Ruled out: a change to the file, a change to its ownership, a missing file,
> a bad path.
> Suspected cause: `user: "1000:1000"` replaces the full group set, dropping
> supplementary groups configured in the image.
> Request: the hardening pass was applied across several services in the same
> change. Can we identify every service whose image adds a supplementary group,
> because each of those is either already broken or one restart away from it.

That last line is why this is worth escalating rather than just fixing. One
service failing is a ticket. A hardening pass applied uniformly to services
that relied on group membership is a queue of identical tickets arriving over
the next few weeks, each looking unrelated.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
