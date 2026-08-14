## CUSTOMER TICKET: customer list is empty and will not load

**Account:** Beacon Analytics (growth)
**Impact:** all users, core workflow unusable
**Started:** after last night's maintenance window

> The app itself seems to come up fine now, but the customer list never
> loads. We just get an error box that says the service is unavailable. Other
> pages that do not show customer data seem OK. We had someone in doing
> maintenance last night, if that helps.

**Your job**

1. Prove which layer is actually failing before you name a cause.
2. Restore service with the smallest correct change.
3. Verify the customer's own workflow, not just that something responds.

**Working notes**

The service is expected on `http://127.0.0.1:8100`. The customer workflow is
`GET /customers`. Runtime configuration lives in
`labs/docker/_stack/compose.override.yaml`. After editing it, run `tse apply`
to recreate the services, then `tse check`.
