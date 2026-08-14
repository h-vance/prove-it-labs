# Solution: the service keeps restarting

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `kubectl get pods` | Restart count is climbing steadily | Whether it crashed or was stopped |
| `describe pod`, Last State | `Reason: OOMKilled`, `Exit Code: 137` | Nothing about the application's own logic |
| `logs --previous` | Output stops mid-run with no error | |
| `-o jsonpath` on resources | The memory limit is 128Mi | |
| `-o jsonpath` on env | `ALLOCATE_MB` is set to 200 | |

The decisive distinction: exit code 137 and a reason of `OOMKilled` mean the
kernel stopped the process for exceeding its allowance. The application did not
fail. It was killed, which is why the logs simply stop rather than ending in an
error, and why there is nothing in the code to fix.

## Root cause

Tuesday's cache tuning raised the amount of memory the service allocates at
startup to roughly 200MB, while its container memory limit remained at 128Mi.
The process exceeds the limit shortly after starting, the kernel terminates it,
the platform restarts it, and the cycle repeats. That is exactly the "fails for
thirty seconds, recovers, fails again" pattern the customer described.

The customer's reasoning that a config value cannot cause this was
understandable and wrong. A config value that controls memory allocation is
every bit as capable of stopping a process as a code change.

## Scoped fix

Either raise the allowance to fit the workload, or reduce what the workload
asks for. Which is correct depends on whether the larger cache is wanted, so it
is a decision to make with the customer rather than for them. Here the tuning
was deliberate, so the limit moves:

```bash
kubectl -n tse-training edit deployment/orders-api
# limits.memory: 128Mi -> 512Mi
kubectl -n tse-training rollout status deployment/orders-api
```

Watch the restart count settle rather than assuming. A crash loop on a timer
looks resolved for the first minute regardless of what you changed.

## Customer update

> The service was not crashing. It was being stopped by the platform for using
> more memory than it is allowed, which is why you saw a clean restart cycle
> rather than errors in the logs. The cache setting changed on Tuesday raised
> how much memory the service reserves at startup to around 200MB, and its
> memory allowance was still 128MB, so it exceeded the limit within seconds of
> starting every time.
>
> That is why the timing lined up with a change you reasonably thought was
> unrelated: the setting is a configuration value, but what it configures is
> memory use. We have raised the allowance to accommodate the new cache size and
> the restarts have stopped.
>
> Worth deciding on your side whether the larger cache is worth the extra
> memory, since the alternative fix is to reduce the cache back down. Either is
> fine, and I would rather you choose than have us pick for you.

## Engineering escalation, if you needed one

> Impact: intermittent failures on order lookups every few minutes since Tuesday.
> Evidence: `Last State: Terminated`, `Reason: OOMKilled`, `Exit Code: 137`;
> previous-instance logs end mid-run without an error; `ALLOCATE_MB=200`
> against `limits.memory: 128Mi`.
> Confirmed: image, configuration, scheduling, Service routing.
> Ruled out: application defect, recent deploys, dependency failure.
> Suspected cause: a cache tuning change raised allocation without a
> corresponding limit change.
> Request: confirm the intended cache size so the limit can be set once
> deliberately rather than raised reactively.

## Say it out loud (90 seconds)

> The customer has ruled out their config change on the grounds that it is not
> code, and that is the assumption I want to test, because plenty of things stop
> a process that are not code. First I want to prove whether the application
> failed or something stopped it, because those have different fixes. A
> restarting container has two histories, and the useful one belongs to the
> instance that already died, so I would read the previous logs and the last
> terminated state. The logs stop mid-run with no error, and the terminated
> state says OOMKilled with exit code 137, which means the kernel stopped it for
> exceeding its memory allowance. Then I compare what it is allowed against what
> it now uses, and the cache setting changed on Tuesday raised the allocation
> well past the limit. So the fix is either a bigger allowance or a smaller
> cache, and I would ask the customer which they want rather than deciding for
> them.
