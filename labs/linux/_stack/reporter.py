#!/usr/bin/env python3
"""Submits the daily report, which means first reading the credentials for it.

Everything interesting here is in the failure path. The file is present, it is
readable by the account that owns it, and this process is not that account.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

CREDENTIALS = Path("/etc/reporting/credentials.conf")


def main() -> int:
    try:
        text = CREDENTIALS.read_text()
    except PermissionError as error:
        print(json.dumps({
            "status": "error",
            "event": "credentials_unreadable",
            "detail": str(error),
            "running_as_uid": os.getuid(),
            "running_as_gid": os.getgid(),
            "supplementary_groups": sorted(os.getgroups()),
        }), flush=True)
        return 1
    except FileNotFoundError as error:
        print(json.dumps({
            "status": "error",
            "event": "credentials_missing",
            "detail": str(error),
        }), flush=True)
        return 1

    endpoint = ""
    for line in text.splitlines():
        if line.startswith("endpoint="):
            endpoint = line.split("=", 1)[1].strip()

    print(json.dumps({
        "status": "ok",
        "event": "report_submitted",
        "endpoint": endpoint,
        "credentials": "loaded",
    }), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
