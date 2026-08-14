## CUSTOMER TICKET: one of our analysts cannot export the incident report

**Account:** Beacon Analytics (growth)
**Impact:** one user blocked, workaround exists
**Started:** since she joined last week

> Our new analyst cannot export the incident report. She gets an error every
> time. Our team lead can export it fine from the same page on the same
> network, so it is not the browser and it is not us being offline. Her login
> definitely works because she is using the rest of the product all day.

**Your job**

1. Reproduce the failure before you theorize.
2. Prove whether this is an authentication problem or a permissions problem,
   because they go to different people.
3. Get the export succeeding, then write the update.

**Working notes**

The API is at `http://127.0.0.1:8101`. The customer's own request lives in
`labs/api/_stack/request.sh`. Run it to reproduce, edit it until it succeeds,
then run `tse check`. Credentials you have access to are listed in
`labs/api/_stack/credentials.md`.
