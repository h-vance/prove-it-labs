# Solution: down with no logs

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `kubectl logs` | Refuses with `container "app" ... is waiting to start: CreateContainerConfigError`, so the code was never reached | Nothing about the application itself |
| `describe pod` | Container state is `CreateContainerConfigError` | Which value was missing |
| `get events` | The named key could not be found | Who removed or renamed it |
| `get deployment -o jsonpath` | The workload asks for `APP_SECRET_V2` | |
| `get configmap` | The configuration holds `APP_SECRET`, not `APP_SECRET_V2` | |

The missing log was the most valuable evidence in the ticket, and the customer
had already found it and discarded it. Asking for logs does not return nothing:
it returns a refusal that names the container state outright, so the answer is
handed over by the very command that appeared to be a dead end. No output at
all means the process never ran, which eliminates the entire application as a
suspect and leaves only what the platform does on its behalf: pull the image,
resolve values, mount volumes, apply security settings.

## Root cause

Last night's config change updated the Deployment to read `APP_SECRET` from a
ConfigMap key named `APP_SECRET_V2`, but that key was never created. Kubernetes
cannot assemble a container whose environment references a key that does not
exist, so it stops before starting the process and reports
`CreateContainerConfigError`.

The image was fine, the ConfigMap existed, and the application was never at
fault. Only the specific key was wrong, which is why nothing looked obviously
broken at a glance.

## Scoped fix

Point the workload back at the key that exists:

```bash
kubectl -n tse-training edit deployment/orders-api
# change configMapKeyRef.key from APP_SECRET_V2 back to APP_SECRET
kubectl -n tse-training rollout status deployment/orders-api
```

The other correct fix is to add the `APP_SECRET_V2` key to the ConfigMap, and
which one is right depends on what the config change was trying to achieve. Ask
before choosing. Here the ConfigMap is the source of truth, so the workload
moves.

## Customer update

> Your engineer's observation about the missing logs was the key to this. There
> were no logs because the application never started: the change made last night
> pointed the service at a configuration key named `APP_SECRET_V2`, and that key
> does not exist in the configuration it reads from. The platform will not start
> a container whose configuration it cannot fully resolve, so it stopped before
> your code ran, which is exactly why there was nothing to log.
>
> We have pointed the service back at the existing key and order lookups are
> working again. If the intention last night was to move to a new key name, the
> key needs creating first and then the service can be switched over. Happy to
> walk through that sequence with your team so the same gap does not reopen.

## Engineering escalation, if you needed one

> Impact: total outage of order lookups since the overnight config change.
> Evidence: container state `CreateContainerConfigError`; events name
> `APP_SECRET_V2` as not found; the ConfigMap contains `APP_SECRET` only.
> Confirmed: image, scheduling, the ConfigMap object itself.
> Ruled out: application fault, image availability, resource pressure.
> Suspected cause: a rename applied to the consumer without being applied to
> the provider.
> Request: confirm whether the rename was intended, and whether other workloads
> took the same edit.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
