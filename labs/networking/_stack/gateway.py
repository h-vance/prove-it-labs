"""The report gateway. Accepts the customer's nightly export over TLS.

Deliberately ordinary. Nothing in here is broken in any exercise: what changes
between them is which certificate the gateway was configured to present, and
the whole point of the track is that a correct, healthy, running service is
exactly what a TLS failure looks like from this side.

Logging follows the api stack: logfmt, no timestamps, no default access line.
A recorded log has to be comparable byte for byte in CI, and a clock is the
first thing that stops it being.
"""
from __future__ import annotations

import json
import os
import ssl
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8443


class Handler(BaseHTTPRequestHandler):
    server_version = "reports-gateway"
    sys_version = ""

    def do_GET(self) -> None:
        if self.path == "/health":
            self.respond(HTTPStatus.OK, {"status": "ok"})
        else:
            self.respond(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/v1/exports":
            self.respond(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        self.respond(
            HTTPStatus.ACCEPTED,
            {"status": "accepted", "bytes_received": length},
        )

    def respond(self, status: HTTPStatus, body: dict[str, object]) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        print(
            f"level=info method={self.command} path={self.path} "
            f"status={int(status)}",
            flush=True,
        )

    def log_message(self, format: str, *args: object) -> None:
        return  # respond() is the log; suppress the default access line


def main() -> None:
    certificate = os.environ.get("GATEWAY_CERT")
    if not certificate:
        sys.exit(
            "GATEWAY_CERT is not set, so there is no certificate to present.\n"
            "It is set in the exercise's compose.override.yaml; run `tse start`."
        )

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate)

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.daemon_threads = True
    server.socket = context.wrap_socket(server.socket, server_side=True)

    # The certificate is not named here on purpose. This line goes in the log a
    # learner reads, and which file was loaded is the answer rather than the
    # evidence. `openssl` against the running port shows what is being served,
    # which is the same fact obtained the way it is obtained in production.
    print(f"level=info event=server_started port={PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
