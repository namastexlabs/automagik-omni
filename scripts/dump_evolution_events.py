"""Connect to the Omni SQLite database and list unique Evolution webhook events.

This is a quick observational script intended to highlight message patterns the
current system has stored (or missed). It can run against either `data/raw_webhook_events.jsonl`
or the `trace_payloads` table via filters.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable


def analyze_jsonl(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"No capture file found at {path!s}")

    key_counts: Counter[str] = Counter()
    message_types: Counter[str | None] = Counter()

    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            if not line.strip():
                continue
            body = json.loads(line)["body"]
            data = body.get("data", {})
            message = data.get("message", {})
            for key in message:
                key_counts[key] += 1
            message_types[data.get("messageType")] += 1

    print("Message payload keys (JSONL):")
    for key, count in key_counts.items():
        print(f"  {key}: {count}")
    print("\nmessageType field values:")
    for msg_type, count in message_types.items():
        print(f"  {msg_type}: {count}")


def analyze_trace_payloads(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    key_counts: Counter[str] = Counter()
    payload_types: Counter[str | None] = Counter()

    for row in cur.execute("SELECT stage, payload_type, payload_compressed FROM trace_payloads"):
        payload_types[row["payload_type"]] += 1
        compressed = row["payload_compressed"]
        if not compressed:
            continue
        try:
            data = json.loads(compressed)
        except Exception:
            continue
        message = data.get("data", {}).get("message", {})
        for key in message:
            key_counts[key] += 1

    conn.close()

    print("\nPayload types from trace_payloads:")
    for type_, count in payload_types.items():
        print(f"  {type_}: {count}")
    print("\nMessage payload keys stored in trace_payloads:")
    for key, count in key_counts.items():
        print(f"  {key}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarise Evolution webhook events")
    parser.add_argument("--jsonl", type=Path, default=Path("data/raw_webhook_events.jsonl"))
    parser.add_argument("--db", type=Path, default=Path("data/automagik-omni.db"))
    args = parser.parse_args()

    analyze_jsonl(args.jsonl)
    analyze_trace_payloads(args.db)


if __name__ == "__main__":
    main()

