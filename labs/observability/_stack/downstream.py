"""The second hop. Renders reports, and answers directory lookups slowly.

Two things live here and they belong to different exercises.

`/internal/directory` is deliberately slow. It stands in for the kind of
lookup a service falls back to when its local copy of something does not have
the answer: correct, authoritative, and far too expensive to do per request.
The slowness is a fixed sleep rather than real work, so the number is the same
on a laptop and on a runner.

`/v1/render` is where a report actually fails, and it logs that failure against
whichever request id it was given. Which id that is turns out to be the whole
of the second exercise.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

PORT = 8080

# How long the authoritative directory takes to answer. Fixed, because a
# percentile measured off real contention is a coin flip on a shared runner and
# a lab that fails one run in ten gets switched off.
DIRECTORY_LATENCY_S = 1.5

# The authoritative record. A tenant missing from the api's local copy is not
# missing here, which is why the fallback returns the right answer and only
# costs time.
DIRECTORY = {
    "northwind": {"plan": "enterprise", "row_limit": 50000},
    "contoso": {"plan": "growth", "row_limit": 10000},
    "fabrikam": {"plan": "growth", "row_limit": 10000},
    "tailspin": {"plan": "starter", "row_limit": 2000},
    "wingtip": {"plan": "starter", "row_limit": 2000},
    "proseware": {"plan": "growth", "row_limit": 10000},
    "litware": {"plan": "starter", "row_limit": 2000},
    "adventure": {"plan": "growth", "row_limit": 10000},
    "wideworld": {"plan": "starter", "row_limit": 2000},
    "lucerne": {"plan": "growth", "row_limit": 10000},
    "coho": {"plan": "starter", "row_limit": 2000},
    "alpine": {"plan": "growth", "row_limit": 10000},
    "trey": {"plan": "starter", "row_limit": 2000},
    "relecloud": {"plan": "growth", "row_limit": 10000},
    "vanarsdel": {"plan": "starter", "row_limit": 2000},
    "fourthcoffee": {"plan": "growth", "row_limit": 10000},
    "graphicdesign": {"plan": "starter", "row_limit": 2000},
    "humongous": {"plan": "enterprise", "row_limit": 50000},
    "consolidated": {"plan": "growth", "row_limit": 10000},
    "blueyonder": {"plan": "starter", "row_limit": 2000},
}

# The render budget. A report asking for more rows than this fails, every time,
# for the same tenant. Deterministic on purpose: the second exercise is about
# finding the failure in the logs, not about catching it while it happens.
RENDER_BUDGET_ROWS = 25000


class Handler(BaseHTTPRequestHandler):
    server_version = "report-renderer"
    sys_version = ""

    @property
    def request_id(self) -> str:
        """Whatever the caller passed, or a fresh one if it passed nothing.

        Minting one when the header is absent is correct and is exactly what
        makes the second exercise hard: the logs are never empty and never
        obviously wrong. They are full of ids that belong to nobody.
        """
        return self.headers.get("X-Request-Id") or f"gen-{uuid.uuid4().hex[:12]}"

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query)
        tenant = (query.get("tenant") or [""])[0]

        if parsed.path == "/health":
            self.respond(HTTPStatus.OK, {"status": "ok"}, log=False)

        elif parsed.path == "/internal/directory":
            time.sleep(DIRECTORY_LATENCY_S)
            record = DIRECTORY.get(tenant)
            if record is None:
                self.log("warn", "directory_miss", tenant=tenant)
                self.respond(HTTPStatus.NOT_FOUND, {"error": "unknown_tenant"})
                return
            self.log("info", "directory_lookup", tenant=tenant)
            self.respond(HTTPStatus.OK, dict(record, tenant=tenant))

        elif parsed.path == "/v1/render":
            rows = int((query.get("rows") or ["0"])[0])
            if rows > RENDER_BUDGET_ROWS:
                self.log(
                    "error", "render_failed", tenant=tenant,
                    rows=rows, budget=RENDER_BUDGET_ROWS,
                    detail="report exceeds the render budget",
                )
                self.respond(
                    HTTPStatus.INSUFFICIENT_STORAGE,
                    {"error": "render_budget_exceeded", "rows": rows,
                     "budget": RENDER_BUDGET_ROWS},
                )
                return
            self.log("info", "render_ok", tenant=tenant, rows=rows)
            self.respond(HTTPStatus.OK, {"status": "rendered", "rows": rows})

        else:
            self.respond(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def log(self, level: str, event: str, **fields: object) -> None:
        pairs = " ".join(f"{key}={value}" for key, value in fields.items())
        print(
            f"level={level} service=downstream request_id={self.request_id} "
            f"event={event} {pairs}".rstrip(),
            flush=True,
        )

    def respond(self, status: HTTPStatus, body: dict[str, object],
                *, log: bool = True) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Request-Id", self.request_id)
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return  # log() is the log; suppress the default access line


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.daemon_threads = True
    print(f"level=info service=downstream event=server_started port={PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
