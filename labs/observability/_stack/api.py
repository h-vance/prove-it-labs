"""The customer-facing report service.

Resolves a tenant's configuration, asks the renderer for the report, and keeps
enough of a latency record to answer the question a dashboard asks. It also
answers the question a dashboard usually cannot, which is what any one customer
is seeing, and that gap is the first exercise on this stack.

Metrics are reported against an objective rather than as an average, which is
both what a real service-level dashboard does and the only version of this that
is reproducible. Whether a request beat one second is the same answer on a
laptop and on a busy runner. What its mean was, to the millisecond, is not, and
a lab whose evidence moves between machines cannot be checked against anything.

That constraint turned out to improve the exercise. "Ninety-five percent of
requests met the objective" is a truthful, healthy-looking number, and the fact
that it can sit beside "zero percent of this customer's did" is the entire
point of the first exercise here.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import defaultdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

PORT = 8080
DOWNSTREAM = os.environ.get("DOWNSTREAM_URL", "http://downstream:8080")
TENANTS_FILE = os.environ.get("TENANTS_FILE", "/etc/api/tenants.json")
DEFAULT_ROWS = 1000

# Which of the caller's headers are passed on to the renderer.
#
# An allowlist rather than forwarding everything, which is the right shape: a
# service should not relay arbitrary headers it does not understand. What goes
# in the list is a decision somebody makes once and rarely revisits.
FORWARD_HEADERS = [
    name.strip().lower()
    for name in os.environ.get("FORWARD_HEADERS", "").split(",")
    if name.strip()
]

# The service level objective every request is measured against.
#
# One second, against a fast path of a few milliseconds and a fallback of one
# and a half seconds. The margin either side is what makes the counts identical
# on every machine: a request has to be three hundred times slower than usual,
# or a third faster than a fixed sleep, before it lands on the other side.
SLOW_THRESHOLD_MS = 1000

_lock = threading.Lock()
_counts: dict[str, int] = defaultdict(int)
_slow: dict[str, int] = defaultdict(int)


def observe(tenant: str, elapsed_ms: float) -> None:
    """Record one request against the whole service and against its tenant."""
    with _lock:
        for key in ("__all__", tenant):
            _counts[key] += 1
            if elapsed_ms >= SLOW_THRESHOLD_MS:
                _slow[key] += 1


def snapshot(tenant: str | None) -> dict[str, object]:
    key = tenant or "__all__"
    with _lock:
        count = _counts[key]
        slow = _slow[key]

    body: dict[str, object] = {
        "requests": count,
        "slow_requests": slow,
        "slow_threshold_ms": SLOW_THRESHOLD_MS,
        "within_objective_pct": round((count - slow) / count * 100, 1) if count else 0.0,
    }
    if tenant:
        body = {"tenant": tenant, **body}
    return body


class Handler(BaseHTTPRequestHandler):
    server_version = "reports-api"
    sys_version = ""

    @property
    def request_id(self) -> str:
        return self.headers.get("X-Request-Id") or f"req-{uuid.uuid4().hex[:12]}"

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/health":
            self.respond(HTTPStatus.OK, {"status": "ok"})
            return

        if parsed.path == "/metrics":
            tenant = (query.get("tenant") or [""])[0]
            self.respond(HTTPStatus.OK, snapshot(tenant or None))
            return

        if parsed.path != "/v1/reports":
            self.respond(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        tenant = (query.get("tenant") or [""])[0]
        rows = int((query.get("rows") or [str(DEFAULT_ROWS)])[0])
        started = time.monotonic()
        try:
            self.report(tenant, rows)
        finally:
            observe(tenant, (time.monotonic() - started) * 1000)

    def report(self, tenant: str, rows: int) -> None:
        config, source = self.resolve(tenant)
        if config is None:
            self.log("warn", "unknown_tenant", tenant=tenant)
            self.respond(HTTPStatus.NOT_FOUND, {"error": "unknown_tenant"})
            return

        rendered, status = self.render(tenant, rows)
        if status != HTTPStatus.OK:
            self.log("error", "report_failed", tenant=tenant, rows=rows,
                     config_source=source)
            self.respond(status, {"error": "report_failed", "tenant": tenant,
                                  "request_id": self.request_id, **rendered})
            return

        self.log("info", "report_ok", tenant=tenant, rows=rows,
                 config_source=source)
        self.respond(HTTPStatus.OK, {
            "tenant": tenant,
            "plan": config["plan"],
            "row_limit": config["row_limit"],
            "rows": rows,
            "config_source": source,
        })

    def resolve(self, tenant: str) -> tuple[dict[str, object] | None, str]:
        """The tenant's plan and limits, from the local copy if it is there.

        The fallback is authoritative and slow. Nothing here is wrong: a
        service that did not fall back would simply be broken for any tenant
        onboarded since the local copy was written.
        """
        try:
            with open(TENANTS_FILE) as handle:
                local = json.load(handle)
        except (OSError, ValueError):
            local = {}

        if tenant in local:
            return local[tenant], "local"

        try:
            with self.call(f"/internal/directory?tenant={tenant}") as response:
                return json.loads(response.read()), "directory"
        except urllib.error.HTTPError:
            return None, "directory"

    def render(self, tenant: str, rows: int) -> tuple[dict[str, object], HTTPStatus]:
        path = "/v1/render?" + urlencode({"tenant": tenant, "rows": rows})
        try:
            with self.call(path) as response:
                return json.loads(response.read()), HTTPStatus.OK
        except urllib.error.HTTPError as error:
            return json.loads(error.read()), HTTPStatus(error.code)

    def call(self, path: str):
        request = urllib.request.Request(DOWNSTREAM + path)
        for name in FORWARD_HEADERS:
            value = self.headers.get(name)
            if value is not None:
                request.add_header(name, value)
        return urllib.request.urlopen(request, timeout=30)

    def log(self, level: str, event: str, **fields: object) -> None:
        pairs = " ".join(f"{key}={value}" for key, value in fields.items())
        print(
            f"level={level} service=api request_id={self.request_id} "
            f"event={event} {pairs}".rstrip(),
            flush=True,
        )

    def respond(self, status: HTTPStatus, body: dict[str, object]) -> None:
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
    print(
        f"level=info service=api event=server_started port={PORT} "
        f"forward_headers={','.join(FORWARD_HEADERS) or 'none'}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
