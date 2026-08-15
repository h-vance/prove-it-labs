## CUSTOMER TICKET: every report we run is slow and you keep telling us the service is fine

**Account:** Northwind Traders (enterprise)
**Impact:** every report request slow, all of their users
**Started:** noticed over the past week, possibly longer

> Every report we run takes well over a second before anything comes back. It
> has been like this for at least a week and it is now holding up our month
> end close.
>
> We have raised this twice. Both times we were told the service is healthy
> and that response times are comfortably within target, and both times we
> were sent a link to your dashboard showing exactly that.
>
> We are not disputing your dashboard. We are telling you that on our side,
> every single request is slow. Not some of them, not the big ones. Every one.
>
> Somebody there must be able to tell the difference between "the service is
> fine" and "the service is fine for you".

**Your job**

1. Prove what this one account is experiencing, separately from what the
   service reports across everybody.
2. Explain how both readings can be honest at the same time. Your colleagues
   who closed the previous two tickets were not being lazy.
3. Make their requests as fast as everyone else's, without changing what those
   requests return.

**Working notes**

The service is on `127.0.0.1:8102` and reports what it has served since it
started:

```bash
curl -s http://127.0.0.1:8102/metrics | jq
```

A sample workload runs once when the stack comes up, so there is real traffic
to read. The `traffic` container showing `Exited (0)` means that finished.

The customer's account is `northwind`. Their configuration lives in
`labs/observability/_stack/tenants.json`. After editing, run `tse apply`, then
`tse check`.

Giving them the right speed with the wrong data is not a fix. The grader
checks both.
