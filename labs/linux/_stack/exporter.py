#!/usr/bin/env python3
"""The nightly export, reduced to the part that fails.

Writes the day's rows to the spool directory in chunks. How many chunks that
is depends entirely on how many rows go in each one, which is the setting this
exercise is about.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

SPOOL = Path("/var/spool/exports")


def main() -> int:
    rows = int(os.environ.get("EXPORT_ROWS", "5000"))
    per_file = int(os.environ.get("EXPORT_ROWS_PER_FILE", "1000"))

    if per_file < 1:
        print(json.dumps({
            "status": "error",
            "event": "export_failed",
            "detail": "EXPORT_ROWS_PER_FILE must be at least 1",
        }), flush=True)
        return 1

    # A real exporter clears last night's chunks before writing tonight's, so
    # a failed run leaves the directory in the state the failure produced
    # rather than accumulating across attempts.
    for stale in SPOOL.glob("chunk-*.csv"):
        stale.unlink(missing_ok=True)

    wanted = math.ceil(rows / per_file)
    written = 0
    try:
        for index in range(wanted):
            chunk = SPOOL / f"chunk-{index:05d}.csv"
            chunk.write_text(f"row,value\n{index},{index * 7}\n")
            written += 1
    except OSError as error:
        # errno is kept because the message alone is what makes this exercise
        # hard: "No space left on device" is the kernel's wording for running
        # out of either blocks or inodes, and it does not say which.
        print(json.dumps({
            "status": "error",
            "event": "export_failed",
            "detail": str(error),
            "errno": error.errno,
            "files_written": written,
            "files_expected": wanted,
        }), flush=True)
        return 1

    print(json.dumps({
        "status": "ok",
        "event": "export_complete",
        "files_written": written,
        "rows": rows,
    }), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
