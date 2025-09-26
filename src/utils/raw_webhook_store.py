"""Utility helpers for capturing raw webhook events in-process.

Inspired by the standalone listener in ``scripts/raw_webhook_listener.py`` but wired
directly into the FastAPI handler so every Evolution event is persisted even when
no sidecar listener is running.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import Request


_DEFAULT_PATH = Path(os.environ.get("RAW_WEBHOOK_STORE", "data/raw_webhook_events.jsonl"))


def _store_path() -> Path:
    path = _DEFAULT_PATH
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def append_event(body: Dict[str, Any], headers: Dict[str, Any]) -> None:
    """Append a single captured webhook event to the JSONL store."""

    entry = {
        "received_at": datetime.now(tz=timezone.utc).isoformat(),
        "headers": headers,
        "body": body,
    }

    path = _store_path()
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def capture_from_request(request: Request, body: Dict[str, Any]) -> None:
    """Collect the raw headers from ``request`` and persist alongside ``body``."""

    headers = dict(request.headers)
    append_event(body, headers)

