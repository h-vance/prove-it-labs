# Solution: same two addresses, and the certificate is fine

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `/app/upload.sh` against `reports` | Exit 7, `Failed to connect`, in about a millisecond | Nothing about trust. Nothing was presented to distrust |
| The same upload against `gateway` | Accepted immediately, same client, same credentials, same payload | |
| `getent hosts reports` | The name resolves, and it resolves to `127.0.0.1` | |
| `getent hosts gateway` | The same read against the name that works, returning the gateway | |
| `nslookup reports` | The answer came from the resolver, which is healthy and answered at once | Nothing was wrong with the caller's own configuration |

The exit code is the diagnosis and it arrived before any evidence was
gathered. Exit 60 in both previous tickets meant a connection was established
and the caller then refused what it was shown. Exit 7 means nothing accepted
the connection, so nothing was ever presented, so no question about trust can
arise. The customer reasoned their way to that from the timing alone and they
were right.

It also proves the name resolved. A failure to connect names a port and an
address, which the caller can only have because the name became one. That
places the fault between resolution and connection, and there is exactly one
thing in that gap: what the name resolved to.

The two `getent` reads are the whole finding, and they have to be run together.
One name reaches the service and one does not, against the same client, on the
same machine, at the same moment.

## Root cause

The internal resolver held `reports` pointing at `127.0.0.1`. The record
resolved, instantly and successfully, to the caller's own loopback address. The
customer's job connected to itself, found nothing listening on 8443, and
stopped.

`127.0.0.1` is not an address that goes anywhere. It means "this machine" on
every machine that reads it, so a record carrying it is correct only for
whoever is standing on the box at the time. That is the fingerprint of this
fault: somebody testing the endpoint on the gateway itself pointed the record
at their own loopback, it worked from where they were standing, and it was
wrong from everywhere else in the world including where the customer is.

Nothing was down. The resolver was healthy and fast, the gateway was healthy,
the certificate was valid until 2035 and covered both names, and the customer's
integration was correct. Every component reported itself fine because every
component was fine. The only thing wrong was the content of an answer, and
nothing checks the content of an answer.

That is why this took two nights and why the previous two tickets did not.

## Scoped fix

In `labs/networking/_stack/compose.override.yaml`:

```yaml
services:
  resolver:
    environment:
      LAB_RECORDS: "reports=gateway"
```

Then:

```bash
tse apply
tse check
```

The record names the service rather than an address, and that is the part to
carry forward. The gateway is given a new address every time the stack is
recreated, so a record holding today's address is a record that goes wrong on
its own, later, with nobody having touched it. Pointing a name at a name is
what keeps it correct through a rebuild.

**Not the fix:** moving the customer to the other address. It works, it takes
ten seconds, and they have now told you twice they will not accept it. The
check tries both addresses.

**Also not the fix:** deleting the record. The failure stops printing that
particular error and the customer still cannot upload, which is why the check
reads what the name resolves to rather than only whether the old message went
away.

## Customer update

> You were right on both counts, and the reasoning you did before raising this
> saved us the first hour. It was not the same problem as either previous
> ticket, and the speed of the failure was the evidence that proved it.
>
> What went wrong is that the address book entry for the address you use was
> pointing at the wrong place. Your job looked up the address correctly, got an
> answer immediately, and the answer sent it back to your own machine instead
> of to us. That is why it failed in a fraction of a second and why it never
> got far enough to complain about anything else. Your job, your credentials,
> your export and our service were all working the entire time.
>
> This was ours, and it was ours in a way that none of our monitoring could
> see, because every part of the system was healthy and one of them was simply
> answering with the wrong value. We have corrected the entry and pointed it at
> the service by name, so it stays correct the next time the service moves.
>
> Nothing needs to change on your side. We will confirm tonight's export
> landed.

## Engineering escalation, if you needed one

> Impact: two nightly exports lost for Ardent Logistics. Third incident on the
> same endpoint this year and the first that no monitoring could have caught.
> Evidence: `curl: (7) Failed to connect` in about a millisecond on `reports`;
> the same upload accepted on `gateway`; `getent hosts reports` returns
> `127.0.0.1` while `getent hosts gateway` returns the gateway.
> Confirmed: resolver healthy and answering, gateway healthy, certificate valid
> to 2035 and covering both names, customer integration unchanged.
> Ruled out: expiry, the names on the certificate, credentials, the payload,
> and the customer's client. The exit code rules out everything above the
> connection before any of it is tested.
> Suspected cause: the record was pointed at loopback during testing on the
> gateway itself and never pointed back.
> Request: two things. Nothing verifies that a record we publish resolves to
> the service it names from anywhere other than the machine it was created on,
> and nothing refuses a loopback address in a record that is meant to be
> reachable by somebody else. Either one would have caught this at the moment
> it was made rather than two nights later.

The record is a one-line fix. The durable part is that every health check in
the path was green throughout, because none of them ask whether an answer is
correct, only whether one arrived.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
