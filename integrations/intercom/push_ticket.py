#!/usr/bin/env python3
"""File one real api-stack failure as an Intercom Inbox conversation.

Makes a single call to the course's api stack with the revoked key, takes the
401 it returns, and opens a conversation from a fake customer in a trial
Intercom workspace with that evidence in the message. Stdlib only, like the
rest of this repository: nothing to install.

    tools/tse start api/01-webhook-integration-rejected
    python3 integrations/intercom/push_ticket.py --dry-run
    INTERCOM_TOKEN=... python3 integrations/intercom/push_ticket.py
"""
import argparse
import getpass
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

INTERCOM_API = "https://api.intercom.io"
INTERCOM_VERSION = "2.16"

# Synthetic, and revoked on purpose. See labs/api/_stack/credentials.md.
REVOKED_API_KEY = "wk_live_revoked_8f21"

# One fixed customer so a second run finds the contact instead of making
# another. example.com is reserved for exactly this kind of use.
CUSTOMER = {
    "role": "user",
    "email": "northwind-freight@example.com",
    "name": "Northwind Freight (Prove It demo)",
    "external_id": "proveit-northwind",
}


def request(url: str, *, method: str = "GET", headers: dict | None = None,
            payload: dict | None = None) -> tuple[int, dict]:
    """Return (status, decoded JSON body).

    A non-2xx status is returned rather than raised: the api stack's 401 is
    the whole point of this script, not an error.
    """
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            return err.code, json.loads(raw)
        except ValueError:
            return err.code, {"raw": raw.decode(errors="replace")}


def gather_evidence(base_url: str) -> dict:
    """Make the failing call and keep what a support engineer would quote."""
    url = f"{base_url}/v2/webhooks/events"
    # Right after `tse start`, Docker's port proxy accepts the connection a
    # moment before the app inside is listening and then drops it. Ten
    # seconds of retries covers that without hiding a stack that is down.
    for attempt in range(10):
        try:
            status, body = request(
                url, method="POST",
                headers={"X-API-Key": REVOKED_API_KEY, "Content-Type": "application/json"},
                payload={"event": "order.created", "id": "evt_demo_1"})
            break
        except (urllib.error.URLError, http.client.RemoteDisconnected) as err:
            if attempt == 9:
                sys.exit(f"cannot reach {base_url} ({err}); "
                         "run tools/tse start api/01-webhook-integration-rejected first")
            time.sleep(1)
    if status != 401:
        sys.exit(f"expected 401 from {url}, got {status}: {json.dumps(body)}")
    return {
        "endpoint": f"POST {url}",
        "status": status,
        "code": body.get("code"),
        "detail": body.get("detail"),
        "request_id": body.get("request_id"),
        "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


def build_body(evidence: dict) -> str:
    """The customer's message: a sentence of prose, then the evidence block."""
    return (
        "Hi, our webhook integration started failing this morning and nothing "
        "changed on our side. Every event we send is rejected. Can you take a look?\n"
        "\n"
        f"Endpoint: {evidence['endpoint']}\n"
        f"HTTP status: {evidence['status']}\n"
        f"Error code: {evidence['code']}\n"
        f"Server said: {evidence['detail']}\n"
        f"Request id: {evidence['request_id']}\n"
        f"Observed at: {evidence['observed_at']}\n"
    )


def intercom(token: str, method: str, path: str, payload: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Intercom-Version": INTERCOM_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    status, body = request(INTERCOM_API + path, method=method, headers=headers, payload=payload)
    if status // 100 != 2:
        # The token lives in a header, never in a body, so this is safe to show.
        sys.exit(f"Intercom {method} {path} returned {status}: {json.dumps(body)}")
    return body


def find_or_create_contact(token: str) -> str:
    found = intercom(token, "POST", "/contacts/search", {
        "query": {"field": "email", "operator": "=", "value": CUSTOMER["email"]},
    })
    if found.get("data"):
        return found["data"][0]["id"]
    return intercom(token, "POST", "/contacts", CUSTOMER)["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="print the message that would be sent, do not call Intercom")
    parser.add_argument("--base-url", default="http://127.0.0.1:8101",
                        help="where the api stack is listening")
    args = parser.parse_args()

    token = os.environ.get("INTERCOM_TOKEN")
    if not token and not args.dry_run:
        if not sys.stdin.isatty():
            sys.exit("INTERCOM_TOKEN is not set; create an app in the Intercom "
                     "Developer Hub, copy its access token, and export it")
        # Asked for rather than pasted on the command line, so the token
        # stays out of shell history. Nothing is echoed.
        token = getpass.getpass("Intercom access token: ").strip()
        if not token:
            sys.exit("no token given")

    body = build_body(gather_evidence(args.base_url))
    if args.dry_run:
        print(body, end="")
        return

    contact_id = find_or_create_contact(token)
    message = intercom(token, "POST", "/conversations",
                       {"from": {"type": "user", "id": contact_id}, "body": body})
    print(f"conversation {message['conversation_id']} opened for contact {contact_id}")
    print("open your Intercom Inbox to see it")


if __name__ == "__main__":
    main()
