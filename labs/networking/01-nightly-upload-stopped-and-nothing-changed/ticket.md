## CUSTOMER TICKET: nightly export has not uploaded for two nights

**Account:** Ardent Logistics (enterprise)
**Impact:** two nightly exports not delivered
**Started:** overnight, with no release on either side

> Our nightly export has not gone through for two nights running. Nothing was
> deployed on our side, nothing was deployed on yours as far as we can tell,
> and your status page has been green the whole time.
>
> The job says it could not establish a secure connection and gives up. We
> have not changed the address, the credentials, or the schedule. This has run
> untouched every night since March.
>
> One of our engineers opened the address in a browser and it loaded fine. It
> did ask whether he wanted to continue first, but he clicked through and the
> page came up, so the service is clearly running.
>
> We are two nights behind on reporting now. What changed on your side?

**Your job**

1. Prove what the gateway is presenting to callers, rather than proving it is
   running. Those are different claims and only one of them is in question.
2. Answer the customer's question honestly. Nothing changed, and it broke
   anyway. Be able to say why that is possible.
3. Restore the upload without weakening what the client checks.

**Working notes**

The customer's integration runs in the `client` service. You can run it on
demand:

```bash
docker compose -f labs/networking/_stack/compose.yaml \
               -f labs/networking/_stack/compose.override.yaml \
               exec client /app/upload.sh
```

The gateway's configuration is in `labs/networking/_stack/compose.override.yaml`.
After editing, run `tse apply`, then `tse check`.

Everything runs inside these containers rather than from your own shell, so
what you see is what the customer's integration sees.

Making the client stop checking would clear the error. Do not. The grader
inspects what the gateway serves, so it would not pass, and it is the wrong
answer anyway.
