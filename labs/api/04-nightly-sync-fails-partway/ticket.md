## CUSTOMER TICKET: nightly usage sync keeps failing halfway through

**Account:** Tidewater Health (enterprise)
**Impact:** usage reporting incomplete, billing review blocked
**Started:** since they increased their record volume last week

> Our nightly usage sync pulls all our usage records from your API. It used to
> finish fine. Since we grew, it now gets partway through and then starts
> erroring, and we end up with an incomplete file every night. The first few
> pages always come back fine, so it cannot be authentication. We think you have
> corrupt records somewhere in the middle of our data.

**Your job**

1. Reproduce the failure and look at **where** in the run it starts.
2. Prove whether the failures track the data or something else.
3. Get the full sync completing, then write the update.

**Working notes**

The API is at `http://127.0.0.1:8101`. The customer's own request lives in
`labs/api/_stack/request.sh`. Run it to reproduce, edit it until it succeeds,
then run `tse check`. Credentials you have access to are listed in
`labs/api/_stack/credentials.md`.
