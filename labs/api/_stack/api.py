#!/usr/bin/env python3
"""Deterministic HTTP API used as the subject of the API investigation track.

Error bodies follow RFC 9457 (application/problem+json) and every response
carries a correlation id, because correlating a client failure with a server
record is the skill the track is actually teaching.

Credentials are never logged. Only a short fingerprint is, which is what a
real service should do and what a support engineer should expect to find.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections import defaultdict, deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

# Synthetic credentials. Nothing here is real or reusable anywhere.
ACTIVE_API_KEY = "wk_live_active_3c95"
REVOKED_API_KEY = "wk_live_revoked_8f21"
ADMIN_TOKEN = "tok_admin_9b44"
VIEWER_TOKEN = "tok_viewer_5d10"

RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW_SECONDS = 10
MAX_BODY_BYTES = 4096

_rate_log: dict[str, deque[float]] = defaultdict(deque)


def fingerprint(secret: str) -> str:
    """Identify a credential in logs without ever revealing it."""
    if not secret:
        return "none"
    return hashlib.sha256(secret.encode()).hexdigest()[:8]


class Handler(BaseHTTPRequestHandler):
    server_version = "ProveItAPI/2.0"
    protocol_version = "HTTP/1.1"

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(5)
        self.request_id = uuid.uuid4().hex[:12]

    # ----------------------------------------------------------------- routes

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path

        if path == "/health":
            self.ok({"status": "healthy"})
        elif path.startswith("/v1/"):
            self.deprecated_version(path)
        elif path == "/v2/reports/incidents":
            self.reports()
        elif path == "/v2/usage":
            self.usage()
        elif path.startswith("/v2/customers/"):
            self.ok({"id": path.rsplit("/", 1)[-1], "company": "Northwind Freight",
                     "plan": "enterprise"})
        else:
            self.unknown_route(path)

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path.startswith("/v1/"):
            self.deprecated_version(path)
        elif path == "/v2/webhooks/events":
            self.webhook()
        else:
            self.unknown_route(path)

    # --------------------------------------------------------------- handlers

    def webhook(self) -> None:
        api_key = self.headers.get("X-API-Key", "")

        if not api_key:
            self.problem(HTTPStatus.UNAUTHORIZED, "api_key_missing",
                         "API key required",
                         "This endpoint requires an X-API-Key header.")
            return
        if api_key == REVOKED_API_KEY:
            self.problem(HTTPStatus.UNAUTHORIZED, "api_key_revoked",
                         "API key revoked",
                         "This API key was revoked on 2026-08-12 and can no "
                         "longer be used. Issue or retrieve an active key.",
                         key_fingerprint=fingerprint(api_key))
            return
        if api_key != ACTIVE_API_KEY:
            self.problem(HTTPStatus.UNAUTHORIZED, "api_key_invalid",
                         "API key not recognized",
                         "The supplied API key does not match any issued key.",
                         key_fingerprint=fingerprint(api_key))
            return

        body = self.read_json()
        if body is None:
            self.problem(HTTPStatus.BAD_REQUEST, "invalid_payload",
                         "Request body is not valid JSON",
                         "Send a JSON object with 'workspace' and 'event'.")
            return

        self.ok({"status": "accepted", "workspace": body.get("workspace"),
                 "event": body.get("event"),
                 "key_fingerprint": fingerprint(api_key)},
                status=HTTPStatus.ACCEPTED)

    def reports(self) -> None:
        scheme, _, token = self.headers.get("Authorization", "").partition(" ")

        if scheme != "Bearer" or not token:
            self.problem(HTTPStatus.UNAUTHORIZED, "authorization_missing",
                         "Bearer token required",
                         "Send Authorization: Bearer <token>.")
            return
        if token == VIEWER_TOKEN:
            self.problem(HTTPStatus.FORBIDDEN, "insufficient_scope",
                         "Token lacks the required scope",
                         "This token carries 'reports:read'. Exporting "
                         "incident reports requires 'reports:admin'.",
                         token_fingerprint=fingerprint(token),
                         required_scope="reports:admin")
            return
        if token != ADMIN_TOKEN:
            self.problem(HTTPStatus.UNAUTHORIZED, "token_invalid",
                         "Bearer token not recognized",
                         "The supplied token does not match any issued token.",
                         token_fingerprint=fingerprint(token))
            return

        self.ok({"status": "authorized",
                 "report": {"open_incidents": 3, "services_healthy": 12},
                 "token_fingerprint": fingerprint(token)})

    def usage(self) -> None:
        key = self.headers.get("X-API-Key", "anonymous")
        now = time.monotonic()
        window = _rate_log[key]

        while window and now - window[0] > RATE_LIMIT_WINDOW_SECONDS:
            window.popleft()

        if len(window) >= RATE_LIMIT_REQUESTS:
            retry_after = max(1, int(RATE_LIMIT_WINDOW_SECONDS - (now - window[0])) + 1)
            self.problem(HTTPStatus.TOO_MANY_REQUESTS, "rate_limit_exceeded",
                         "Too many requests",
                         f"This client is limited to {RATE_LIMIT_REQUESTS} requests "
                         f"per {RATE_LIMIT_WINDOW_SECONDS} seconds.",
                         extra_headers={
                             "Retry-After": str(retry_after),
                             "RateLimit-Limit": str(RATE_LIMIT_REQUESTS),
                             "RateLimit-Remaining": "0",
                             "RateLimit-Reset": str(retry_after),
                         })
            return

        window.append(now)
        self.ok({"status": "within_limit",
                 "records": 128,
                 "remaining": RATE_LIMIT_REQUESTS - len(window)},
                extra_headers={
                    "RateLimit-Limit": str(RATE_LIMIT_REQUESTS),
                    "RateLimit-Remaining": str(RATE_LIMIT_REQUESTS - len(window)),
                })

    def deprecated_version(self, path: str) -> None:
        self.problem(HTTPStatus.NOT_FOUND, "route_not_found",
                     "Route not found",
                     f"{path} is not served. The v1 API was withdrawn on "
                     f"2026-08-01. The current API is served under /v2.",
                     extra_headers={
                         "Sunset": "Sat, 01 Aug 2026 00:00:00 GMT",
                         "Link": '</v2>; rel="successor-version"',
                     })

    def unknown_route(self, path: str) -> None:
        self.problem(HTTPStatus.NOT_FOUND, "route_not_found",
                     "Route not found",
                     f"{path} does not match any route on this API.")

    # ---------------------------------------------------------------- helpers

    def read_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0 or length > MAX_BODY_BYTES:
            return None
        try:
            parsed = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        return parsed if isinstance(parsed, dict) else None

    def ok(self, body: dict, *, status: HTTPStatus = HTTPStatus.OK,
           extra_headers: dict[str, str] | None = None) -> None:
        body = {**body, "request_id": self.request_id}
        self.emit(status, "application/json", body, extra_headers)
        self.audit(status, body.get("status", ""))

    def problem(self, status: HTTPStatus, code: str, title: str, detail: str, *,
                extra_headers: dict[str, str] | None = None, **members: str) -> None:
        # RFC 9457 problem details. 'code' is an extension member, kept stable
        # so clients branch on it rather than on the human-readable title.
        body = {
            "type": f"https://proveit.invalid/errors/{code}",
            "title": title,
            "status": int(status),
            "detail": detail,
            "instance": urlsplit(self.path).path,
            "code": code,
            "request_id": self.request_id,
            **members,
        }
        self.emit(status, "application/problem+json", body, extra_headers)
        self.audit(status, code)

    def emit(self, status: HTTPStatus, content_type: str, body: dict,
             extra_headers: dict[str, str] | None) -> None:
        payload = json.dumps(body, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Request-Id", self.request_id)
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def audit(self, status: HTTPStatus, outcome: str) -> None:
        credential = self.headers.get("X-API-Key") or \
            self.headers.get("Authorization", "").partition(" ")[2]
        print(
            f"level=info request_id={self.request_id} "
            f"method={self.command} path={urlsplit(self.path).path} "
            f"status={int(status)} outcome={outcome} "
            f"credential={fingerprint(credential)}",
            flush=True,
        )

    def log_message(self, format: str, *args: object) -> None:
        return  # audit() is the log; suppress the default access line


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    server.daemon_threads = True
    print("level=info event=server_started port=8080", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
