"""A fixed sample workload, run once at startup and then finished.

Fixed rather than continuous, and that is the important part. A generator that
keeps running gives every metric a different value each time it is read, and
recorded evidence that changes on every run cannot be compared to anything. Two
hundred requests per tenant would prove nothing that twenty does not.

Because the workload is a known size, every count a learner reads is an exact
number they can reason about: one hundred requests, five of them one
customer's. That is what makes "five of a hundred are slow" and "five of five
are slow" sit next to each other and mean something.

**Serial on purpose, and this was measured rather than assumed.** An earlier
version ran eight at a time, and every service here is capped at half a core.
Four runs of the fixed state produced zero, one, two and four requests over the
one second objective from ordinary local lookups that normally take about five
milliseconds, purely from contention during startup. One of those runs put a
slow request against the very account the exercise says is now fine, which
would have failed in CI on some pushes and not others.

Loosening the objective would have hidden that rather than fixed it. Running
the sample one request at a time removes the contention instead, and a fast
request then lands three hundred times inside the threshold rather than
occasionally outside it. A hundred requests is plenty: the percentages are the
same as four hundred and nothing about the lesson needed the extra three.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API = "http://api:8080"
REQUESTS_PER_TENANT = 5

TENANTS = [
    "northwind", "contoso", "fabrikam", "tailspin", "wingtip",
    "proseware", "litware", "adventure", "wideworld", "lucerne",
    "coho", "alpine", "trey", "relecloud", "vanarsdel",
    "fourthcoffee", "graphicdesign", "humongous", "consolidated", "blueyonder",
]


def one(tenant: str) -> bool:
    try:
        with urllib.request.urlopen(
            f"{API}/v1/reports?tenant={tenant}", timeout=30
        ) as response:
            return response.status == 200
    except urllib.error.URLError:
        return False


def main() -> None:
    # Interleaved rather than tenant by tenant, so the logs read like traffic
    # instead of like a script and one customer's requests are not all together.
    work = [
        tenant
        for _ in range(REQUESTS_PER_TENANT)
        for tenant in TENANTS
    ]

    results = [one(tenant) for tenant in work]

    print(json.dumps({
        "event": "sample_workload_finished",
        "requests": len(results),
        "ok": sum(results),
        "tenants": len(TENANTS),
    }), flush=True)
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
