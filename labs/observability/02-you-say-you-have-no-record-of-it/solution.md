# Solution: they keep sending you the reference and you have no record of it

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| Reproducing with a chosen reference | The failure is real and reproducible on demand | |
| The response body | The reference comes back to the caller, so the screenshot was accurate | Nothing about what was recorded |
| `logs api \| grep <ref>` | One line, from the service that did not fail | |
| `logs downstream \| grep <ref>` | Nothing at all | That the request never reached it, which is the wrong conclusion |
| `logs downstream \| grep render_failed` | The failure, in full, under a reference nobody has ever seen | |

The pair of searches is the diagnosis. One service knows the customer's
reference and the other has never heard of it, and the one that has never heard
of it is where the report actually failed.

Worth being precise about the mistake three colleagues made, because it is an
easy one and it is not laziness. They searched, found nothing, and reported that
the reference did not exist. **An empty result is a claim about the search.** It
says the string was not in the place you looked. Here there was independent
evidence the request happened, in the form of a customer whose report failed and
who had a screenshot, and that evidence should have outweighed the absence.

The other thing that makes this hard is that nothing looks broken. No log is
empty, no error is unhandled, and every single line has a perfectly well formed
reference on it. The logs are healthy and unjoinable, which is a much quieter
failure than a log that stops being written.

## Root cause

The api passes an explicit allowlist of headers when it calls the renderer:

```yaml
FORWARD_HEADERS: "authorization,x-tenant"
```

`x-request-id` is not in it, so the reference stops at the service boundary. The
renderer receives a request with no reference on it, generates its own, and logs
the failure against that. Both services behave correctly in isolation. An
allowlist is the right design, generating a reference when none arrives is also
right, and between them they produce a request that cannot be followed.

The customer's reference was real, was shown to them accurately, and only ever
existed in the log of the one service that did not fail.

## Scoped fix

In `labs/observability/_stack/compose.override.yaml`:

```yaml
services:
  api:
    environment:
      FORWARD_HEADERS: "authorization,x-tenant,x-request-id"
```

Then:

```bash
tse apply
tse check
```

Reproduce the failure again and the same reference now appears in both logs.

**Not the fix:** correlating by timestamp instead. It works on a quiet service
and stops working exactly when you need it, because two customers failing in the
same second are indistinguishable, and it does not scale past one person doing
it by hand. It also does not give the customer anything.

**Also not the fix:** making the report succeed. It is a real bug and deserves
its own ticket, but this ticket is that a reference cannot be followed. Making
the failure go away removes the evidence rather than making it findable, and the
next customer to hit a different failure is in exactly the same position. The
grader checks the failure is still being recorded.

## Customer update

> You copied the reference correctly, our product was right to show it to you,
> and we were wrong to tell you it did not exist. I am sorry it took three
> attempts and nine days to establish that.
>
> Here is what was happening. A report passes through two of our services. The
> reference you were shown was created by the first one and was not being passed
> to the second, and the second is where your report was actually failing. So
> when we searched for your reference we were searching in the only place it
> could never appear, and the failure was sitting in the other log the whole
> time under an internal reference nobody had given you.
>
> That is fixed. References now follow a request all the way through, so the one
> you are shown will find the failure directly.
>
> On the report itself: it is failing because it exceeds an internal size limit
> for rendering, which I now have the detail on and have raised separately. I
> will come back to you on that specifically rather than leaving it inside this
> thread, and I will give you the reference for it.

## Engineering escalation, if you needed one

> Impact: an enterprise customer's month end report has failed for nine days.
> Three support attempts closed as unreproducible because the reference they
> were given cannot be found in the service that fails.
> Evidence: a request carrying `X-Request-Id` appears once in `api` and zero
> times in `downstream`; the corresponding `render_failed` in `downstream`
> carries a generated reference instead.
> Confirmed: reproducible on demand, both services healthy, nothing erroring.
> Ruled out: the customer copying it wrongly, log retention, the reference being
> invented by the product.
> Suspected cause: `FORWARD_HEADERS` on the api does not include
> `x-request-id`, so the reference stops at the boundary and the renderer
> generates its own.
> Request: the one line is fixed. The durable ask is that nothing detects this.
> Every log was full, every line well formed, and the only symptom was three
> support engineers failing to find something. A check that a reference entering
> at the edge appears in every service that handled the request would have caught
> it on the day it shipped, and would catch the next service added without it.

The header is a one line fix and it is not the interesting part. What will
recur is the next service added to this path, because nothing about adding one
forces anybody to think about propagation, and the failure it produces looks
like support being careless rather than like a defect.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
