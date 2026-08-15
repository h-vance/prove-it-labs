# Solution: the nightly upload stopped and nothing changed

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `/app/upload.sh` | The client stops with exit 60 before sending anything | Nothing about why it refused |
| `getent hosts gateway` | The name resolves | Nothing about what answers on it |
| `nc -z gateway 8443` | The port accepts connections | Nothing about what it serves |
| `docker compose logs gateway` | The server has no record of either failed upload | |
| `openssl s_client` piped to `x509 -dates` | It presents a certificate that expired on 1 April 2025 | |

The empty gateway log is the piece worth dwelling on, because it is the one
that reads as a dead end and is not. Two uploads failed and the server logged
nothing about either. That is not a logging gap. A request that reached the
application would have been logged, so no request was ever sent. The client
opened the connection, looked at what came back, and hung up before asking for
anything.

Which is also why every signal the customer had was green, and why they were
right about all of them. The service is running. The port is open. The status
page is honest. Nothing is wrong with the server, and the server is not the
thing that failed.

## Root cause

The gateway was configured to present `v1.pem`, which the internal CA issued
with a validity window of 1 January 2025 to 1 April 2025. That window closed.

A server does not check its own certificate. It presents whatever file it was
pointed at, on every connection, forever. The check happens at the other end,
which is why the failure appeared at the customer with no change at either
site, and why it appeared overnight rather than at a deploy.

The browser test their engineer ran is the same fact from the other side. The
browser also refused, then offered him the choice of continuing anyway, and he
took it. An unattended client has no one to ask.

## Scoped fix

In `labs/networking/_stack/compose.override.yaml`:

```yaml
services:
  gateway:
    environment:
      GATEWAY_CERT: /certs/v2.pem
```

Then:

```bash
tse apply
tse check
```

`v2.pem` was issued by the same internal CA in April 2025 to replace `v1`, and
runs to the end of 2035. The client already trusts that CA, so nothing changes
on the customer's side at all.

**Not the fix:** making the client skip the check. It clears the error
immediately and permanently, and it removes the only thing standing between the
customer and uploading their data to whatever happens to answer on that address
in future. The check did its job. It is the thing that noticed.

**Also not the fix:** picking the highest version number without reading it.
`v3.pem` is also valid here and would also have worked, which is exactly the
habit that causes the next exercise.

## Customer update

> Your uploads were failing because the certificate our gateway presents had
> reached its expiry date. Your integration checks that certificate before it
> sends anything, which is correct and is why it stopped rather than uploading
> to something it could not verify.
>
> You were right that nothing changed. Certificates are issued with a fixed
> end date, and this one passed its date overnight, so the same configuration
> that worked in the evening did not work in the morning. That is also why our
> status page stayed green: the service itself was healthy throughout, and the
> failure happened at your end of the connection before any request reached us.
>
> Your engineer's browser test tells the same story. The browser refused too,
> then offered him the option to continue anyway and he accepted it. Your
> nightly job has nobody to ask, so it stops, which is the behavior you want.
>
> We have rotated the gateway onto a current certificate issued by the same
> authority, so nothing needs to change on your side. Tonight's export will run
> normally. We can also send the two exports you are missing.

## Engineering escalation, if you needed one

> Impact: two nightly exports not delivered for Ardent Logistics. The customer
> holds no data and had no failing signal on either side to look at.
> Evidence: the client exits 60 with `certificate has expired`; the gateway
> serves a certificate with `notAfter=Apr 1 00:00:00 2025 GMT`; the gateway
> logged nothing for either attempt.
> Confirmed: the name resolves, the port accepts, the service is healthy.
> Ruled out: a deployment on either side, credentials, the schedule.
> Suspected cause: the gateway was left pointed at `v1.pem` when it was
> replaced, so the rotation was issued but never picked up.
> Request: nothing monitors the expiry of what the gateway serves, and nothing
> alerts on a handshake that fails before a request. Both were silent for two
> nights. Can we get an expiry check on what is actually being presented, not
> on what we believe is configured.

The rotation is a one-line fix and it is not the durable part. A certificate
that was issued and never deployed will happen again, and the reason nobody
noticed for two nights is that every dashboard was measuring the server.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
