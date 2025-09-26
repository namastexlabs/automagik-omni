"""Minimal FastAPI listener that captures raw webhook payloads for debugging.

Usage:
    uv run uvicorn scripts.raw_webhook_listener:app --host 0.0.0.0 --port 28890

Incoming POST requests to `/webhook/raw` are appended to a JSONL file. This
keeps the webhook runner unchanged while giving us an exact copy of payloads
that include edits/deletes (`protocolMessage`) for later replay.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request


def _default_store_path() -> Path:
    """Resolve the capture file path, creating the directory if needed."""

    raw_path = os.environ.get("RAW_WEBHOOK_STORE", "data/raw_webhook_events.jsonl")
    path = Path(raw_path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


STORE_PATH = _default_store_path()

app = FastAPI(title="Raw Webhook Listener", version="1.0.0")


def _serialize_entry(body: Dict[str, Any], headers: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize the payload before writing to disk."""

    return {
        "received_at": datetime.now(tz=timezone.utc).isoformat(),
        "headers": headers,
        "body": body,
    }


def _append_to_store(entry: Dict[str, Any]) -> None:
    """Append the serialized entry to the JSONL store."""

    with STORE_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")


@app.post("/webhook/raw")
async def capture_webhook(request: Request) -> Dict[str, str]:
    """Capture the raw webhook payload and persist it for later inspection."""

    body = await request.json()
    headers = dict(request.headers)
    entry = _serialize_entry(body, headers)
    _append_to_store(entry)
    return {"status": "ok"}


@app.get("/webhook/raw/latest")
async def latest_events(limit: int = 10) -> Dict[str, Any]:
    """Return the last `limit` captured events for quick inspection."""

    events = []
    if STORE_PATH.exists():
        with STORE_PATH.open("r", encoding="utf-8") as fp:
            for line in fp.readlines()[-limit:]:
                events.append(json.loads(line))
    return {"events": events}


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy"}

