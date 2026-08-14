# Solution: healthy everywhere, routing nowhere

## What the evidence proved

| Command | What it proved | What it did not prove |
|---|---|---|
| `kubectl get pods` | Pods are Running and Ready | Nothing about routing |
| `get endpointslices` | The Service has no endpoints at all | Why the selection is empty |
| `get service -o jsonpath` | The selector asks for `app.kubernetes.io/name: orders` | |
| `get pods --show-labels` | The pods carry `app.kubernetes.io/name: orders-api` | |

Empty endpoints is the fact that turns this ticket. It proves the break is in
the selection rather than in the workload, the application, or the network, and
it is invisible from everything the customer had already checked.

## Root cause

A Service does not link to a Deployment. It runs a label query continuously and
routes to whatever currently matches. Yesterday's platform work changed the
Service's selector to `orders` while the pods kept the label `orders-api`, so
the query matches nothing and the Service routes to nothing.

Every health check the customer ran was accurate. The pods really were healthy,
the Service really did exist, and DNS really did resolve. A Service with no
endpoints still resolves and still accepts connections. It simply has nowhere
to send them, which is why the client gets nothing back rather than an error.

## Scoped fix

The pods are running correctly and should not be disturbed, so the Service
moves:

```bash
kubectl -n tse-training edit service orders-api
# spec.selector: app.kubernetes.io/name: orders -> orders-api
kubectl -n tse-training get endpointslices -l kubernetes.io/service-name=orders-api
```

Confirm endpoints appear before declaring it fixed. Endpoints appearing is the
proof, not the Service looking healthy again, which it did throughout.

## Customer update

> Your team was right that everything reports healthy, and that was genuinely
> true rather than a false reading. The problem was in between: the internal
> address for the order service selects the instances it should route to by
> label, and yesterday's platform work changed the label it looks for without
> changing the label the instances carry. The result is an address that resolves
> and accepts connections but has nothing behind it, which is why requests
> returned nothing instead of failing outright.
>
> We have corrected the selection and confirmed the order service is now
> receiving traffic and returning results. Nothing was wrong with the
> application or its instances at any point.
>
> If the same platform work touched other services, they are worth checking, as
> the same edit would produce the same silent failure.

## Engineering escalation, if you needed one

> Impact: order lookups returning empty for all users since yesterday's
> platform work.
> Evidence: EndpointSlice for `orders-api` has no addresses; Service selector
> is `app.kubernetes.io/name=orders`; pods carry
> `app.kubernetes.io/name=orders-api`; pods Running and Ready throughout.
> Confirmed: pod health, application health, DNS resolution.
> Ruled out: application fault, image, resource pressure, readiness.
> Suspected cause: a selector edit during platform work not matched by a label
> change on the workload.
> Request: identify which other Services were edited in the same change, since
> this failure mode reports healthy everywhere.

## Check your understanding

Three questions on what the evidence here proved, and what it pointedly did
not. Wrong answers explain themselves, and so do right ones.

```
tse quiz
```
