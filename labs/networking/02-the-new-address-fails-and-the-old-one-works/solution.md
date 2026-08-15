# Solution: the new address fails and the old one works

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `/app/upload.sh` against `reports` | Exit 60, `no alternative certificate subject name matches target hostname` | Nothing about the dates, which is what the code alone suggests |
| The same upload against `gateway` | Accepted immediately, same client, same credentials, same payload | |
| `openssl x509 -dates` on what is served | Valid until 2035, so the customer was right | |
| `openssl x509 -ext subjectAltName` | The certificate covers `gateway` and nothing else | |
| The same read across `v1`, `v2` and `v3` | `v1` covered both names. `v2` covers one | |

The two uploads are the whole diagnosis and they have to be run together. One
address fails and one succeeds against **the same server**, so nothing about
the service can account for it. Whatever differs has to depend on which name
was asked for, and in a verified connection there is exactly one thing that
does.

The other piece is the error text. This is the second time this customer has
seen `curl: (60)` with the same four-line paragraph under it, and it is a
different fault both times. April's line said `certificate has expired`. This
one names a hostname. Reading the code and stopping is how the customer's own
theory ("it is that again") gets adopted without being tested.

## Root cause

The gateway presents `v2.pem`, whose subject alternative names list `gateway`
and nothing else. The customer was migrated onto `reports`, which reaches the
same process through a second name on the same service.

A certificate is a claim that a server owns particular names. Adding a name to
a service does not add it to the certificate, so the new address was
unverifiable from the moment it existed, and only became visible when somebody
was told to use it.

The reason it is `v2` and not something older is the part worth carrying
forward. `v1`, the certificate that expired in April, covered both names. The
reissue that replaced it covers one. That rotation fixed the incident in front
of it and narrowed the certificate at the same time, and nothing failed for a
week because nobody was calling the second name yet.

**April's fix caused this.** Not through carelessness about the thing being
fixed, but by changing something adjacent that nobody was watching.

## Scoped fix

In `labs/networking/_stack/compose.override.yaml`:

```yaml
services:
  gateway:
    environment:
      GATEWAY_CERT: /certs/v3.pem
```

Then:

```bash
tse apply
tse check
```

`v3.pem` was issued by the same internal CA, runs to the end of 2035, and
covers both names. Nothing changes for callers on either address.

**Not the fix:** reissuing for `reports` alone. It clears the customer's
failure and breaks every caller still on `gateway`, which is most of them. The
check tries both addresses because moving an outage is the most common way this
one gets closed as resolved.

**Also not the fix:** moving the customer back to the old address. It works, it
takes ten seconds, and it parks them on something you have told them you are
retiring. That is a ticket reopened in a month with less goodwill.

## Customer update

> You were right that it was not the same problem as April, and thank you for
> checking before you raised it. The certificate we serve is valid until 2035,
> exactly as we told you.
>
> What went wrong is different. A certificate lists the specific addresses a
> server is allowed to be called by, and the one we were serving listed only
> the old address. When you moved to the new one, your job did the correct
> thing and refused to continue, because we could not prove that address
> belonged to us. Your export, your credentials, and the service itself were
> all fine, which is why the old address kept working.
>
> This was ours. The certificate we issued in April to fix your previous
> incident was created without the second address on it, and that gap only
> became visible when we asked you to move. We have replaced it with one
> covering both, so the new address now works and the old one is unaffected.
>
> Please go ahead and move back to the new address when convenient. You do not
> need to change anything else, and we will confirm tonight's export landed.

## Engineering escalation, if you needed one

> Impact: one nightly export lost for Ardent Logistics after we asked them to
> migrate. The migration instruction was ours and the address we sent them to
> was unusable from the moment it was published.
> Evidence: `no alternative certificate subject name matches target hostname
> 'reports'` on the new address; the same upload accepted on the old one;
> the served certificate lists `DNS:gateway` only.
> Confirmed: one service behind both names, valid dates, healthy gateway.
> Ruled out: expiry, credentials, the customer's client, the payload.
> Suspected cause: the April reissue dropped `reports` from the alternative
> names. The gap existed for a week and was invisible until the migration.
> Request: two things. Nothing compared the names on the new certificate
> against the names on the one it replaced, and nothing checks that every
> address we publish is covered by what we serve on it. The first would have
> caught this at issue time, the second at migration time, and we currently
> have neither.

The rotation is a one-line fix. The durable part is that a reissue narrowed a
certificate and no check noticed, which will happen again on a different name
unless something compares the two.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
