# Solution: correct labels, still no traffic

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `get service` and `get pods --show-labels` | The labels genuinely match. The customer was right | Nothing about routing |
| `get endpointslices` | Still no ready endpoints | Why, given the labels match |
| `kubectl get pods` | STATUS is `Running` and READY is `0/1` | |
| `describe pod` | The readiness probe targets port 8081 and fails | |
| `-o jsonpath` on ports | The container serves 8080 only | |

The distinction that resolves this: matching the selector is necessary for
routing but not sufficient. A pod also has to be **ready**, and readiness is a
separate condition that the Service enforces silently.

## Root cause

This morning's health check adjustment pointed the readiness probe at port
8081. The application listens only on 8080, so every readiness check is refused
and the probe never passes. A pod that is not ready is deliberately excluded
from its Service's endpoints, so the Service has nothing to route to.

Nothing failed. The container is alive, the application is serving correctly on
its real port, the logs are clean, and the labels match. The platform is doing
precisely what it was configured to do, which is why this is so quiet.

## Why the previous fix did not apply

The customer's engineer checked the labels because of the earlier write-up,
found them correct, and stopped. That was good instinct and an incomplete
model. Both tickets end in an empty endpoint list, and there are two separate
routes to that state:

| Cause | Pod STATUS | Pod READY | Labels |
|---|---|---|---|
| Selector mismatch | Running | 1/1 | do not match |
| Readiness failing | Running | 0/1 | match |

The READY column is what separates them, and it is one column away from the
one everybody reads.

## Scoped fix

```bash
kubectl -n tse-training edit deployment/orders-api
# readinessProbe.httpGet.port: 8081 -> 8080
kubectl -n tse-training rollout status deployment/orders-api
kubectl -n tse-training get endpointslices -l kubernetes.io/service-name=orders-api
```

## Customer update

> Your engineer was right that the labels match, and that check was worth doing.
> This is a different cause with the same symptom.
>
> The health check change this morning pointed the readiness check at port 8081,
> and the order service listens on 8080. Readiness checks do more than report
> status: an instance that is not ready is deliberately kept out of the load
> balancing pool, so the check failing meant every instance was excluded even
> though all of them were running and serving correctly. That is why nothing
> errored and nothing appeared in the logs.
>
> We have pointed the readiness check back at the port the service listens on
> and traffic is flowing again. Worth knowing for the future: health check
> settings are not monitoring-only, they actively control whether an instance
> receives traffic.

## Engineering escalation, if you needed one

> Impact: order lookups returning empty for all users since the morning health
> check change.
> Evidence: pods `Running` with READY `0/1`; readiness probe targets 8081;
> container exposes 8080 only; probe failures with connection refused in
> events; EndpointSlice empty; Service selector and pod labels match.
> Confirmed: labels, application health, image, configuration.
> Ruled out: the selector mismatch seen previously, application fault.
> Suspected cause: a probe port edit applied without checking the container's
> exposed port.
> Request: confirm whether the same change was applied to other workloads, and
> whether probe ports can be validated against container ports at admission.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
