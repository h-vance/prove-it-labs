# Solution: the release never went live

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `kubectl get pods` | Pods exist and are stuck in `ImagePullBackOff` | Nothing about why the pull failed |
| `kubectl get events` | The registry rejected the reference by name | Nothing about who set it |
| `describe pod` | The container has never started, so there are no logs to read | |
| `get deployment -o jsonpath` | The image tag is `3.12-alpne` rather than `3.12-alpine` | |

Two things worth stating explicitly, because both are useful in the write-up:
the desired state was accepted and pods were scheduled, so this was never a
permissions or capacity problem. And the pipeline was honest: it reported that
it submitted the change, which it did.

## Root cause

The release set the container image to a tag that does not exist, a
single-character typo in `3.12-alpine`. Kubernetes accepted the Deployment
because the spec is valid, created the pods, and then could not pull the image,
so the containers never started. The previous version's pods were replaced as
part of the rollout, which is why the outage is total rather than partial.

## Scoped fix

```bash
kubectl -n tse-training set image deployment/orders-api app=python:3.12-alpine
kubectl -n tse-training rollout status deployment/orders-api
```

Nothing else needs touching. The Service, the configuration, and the
application were all proven fine by the evidence above.

## Customer update

> The release was accepted but never started. The deployment referenced a
> container image tag that does not exist, so the platform created the new
> instances and then could not retrieve the image for them. That is why your
> pipeline reported success: it submitted the change correctly, and the failure
> happened afterwards when the image was requested. We have corrected the
> reference and the service is serving order lookups again.
>
> Worth raising with whoever owns your pipeline: a deploy that cannot pull its
> image will report success and take the service down. Adding a rollout status
> check after the deploy step would have caught this in the pipeline instead of
> in production.

## Engineering escalation, if you needed one

> Impact: total outage of order lookups from 08:40.
> Evidence: pods in `ImagePullBackOff`; events show the registry rejecting
> `python:3.12-alpne`; deployment spec confirms the tag.
> Confirmed: scheduling, permissions, configuration, and the Service.
> Ruled out: application fault, resource pressure, networking.
> Suspected cause: a typo in the image tag in the release.
> Request: confirm whether the deploy pipeline waits on rollout status, since
> it currently reports success for a release that never became live.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
