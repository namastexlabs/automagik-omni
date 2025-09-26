"""Build `message_table_draft.csv` from captured raw webhook events.

The generator reads `data/raw_webhook_events.jsonl` and emits rows aligned to the
legacy message table schema, with a handful of new columns for context flags so
we can track forwards and other metadata the raw payload exposes.

Run manually with:

    uv run python scripts/generate_message_table_from_raw.py

This will overwrite `message_table_draft.csv` in the project root.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


RAW_EVENTS_PATH = Path("data/raw_webhook_events.jsonl")
OUTPUT_PATH = Path("message_table_draft.csv")


HEADER = [
    "id (UUIDv7)",
    "channel",
    "channel_message_id (current whatsapp_message_id this needs to be uniniversalized)",
    "instance_configs_id",
    "sender_id",
    "sender_name",
    "recipient_id",
    "conversation_id",
    "message_type",
    "text_content",
    "media_url",
    "media_type",
    "media_mime_type",
    "media_size_bytes",
    "media_duration_seconds",
    "media_base64",
    "ai_transcription",
    "ai_description",
    "ai_summary",
    "reaction_emoji",
    "reaction_to_message_id",
    "location_lat",
    "location_lng",
    "contact_info",
    "is_from_me",
    "is_edited",
    "is_deleted",
    "created_at",
    "updated_at",
    "context_is_forwarded",
    "context_forwarding_score",
    "context_mentions",
    "context_disappearing_mode",
    "context_paired_media_type",
]


def load_raw_events(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"No raw events found at {path!s}")

    events: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            if not line.strip():
                continue
            events.append(json.loads(line))
    return events


def epoch_to_iso(timestamp: Any) -> str:
    if timestamp in (None, "", 0):
        return ""
    try:
        ts_int = int(timestamp)
        return datetime.fromtimestamp(ts_int, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, TypeError):
        return ""


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def derive_message_type(message: Dict[str, Any], default: str | None) -> str:
    if "audioMessage" in message:
        return "audio"
    if "videoMessage" in message:
        return "video"
    if "imageMessage" in message:
        return "image"
    if "documentMessage" in message:
        return "document"
    if "contactMessage" in message:
        return "contact"
    if "locationMessage" in message:
        return "location"
    if "reactionMessage" in message:
        return "reaction"
    return (default or "text").lower()


def extract_media_fields(message: Dict[str, Any], message_type: str) -> Dict[str, str]:
    if message_type not in {"audio", "video", "image", "document"}:
        return {
            "media_type": "",
            "media_url": "",
            "media_mime_type": "",
            "media_size_bytes": "",
            "media_duration_seconds": "",
            "media_base64": "",
        }

    key_map = {
        "audio": "audioMessage",
        "video": "videoMessage",
        "image": "imageMessage",
        "document": "documentMessage",
    }
    payload = message.get(key_map[message_type], {})
    media_url = stringify(payload.get("url"))
    media_mime = stringify(payload.get("mimetype"))
    media_size = stringify(payload.get("fileLength"))
    media_duration = stringify(payload.get("seconds")) if message_type in {"audio", "video"} else ""

    base64_value: Any = message.get("base64")
    if not base64_value and message_type in {"image", "video"}:
        base64_value = payload.get("jpegThumbnail")

    return {
        "media_type": message_type,
        "media_url": media_url,
        "media_mime_type": media_mime,
        "media_size_bytes": media_size,
        "media_duration_seconds": media_duration,
        "media_base64": stringify(base64_value),
    }


def extract_context_fields(context: Dict[str, Any]) -> Dict[str, str]:
    mentions_payload: Dict[str, Any] = {}
    if "mentionedJid" in context and context["mentionedJid"]:
        mentions_payload["mentionedJid"] = context["mentionedJid"]
    if "groupMentions" in context and context["groupMentions"]:
        mentions_payload["groupMentions"] = context["groupMentions"]

    disappearing = context.get("disappearingMode")

    return {
        "context_is_forwarded": "TRUE" if context.get("isForwarded") else "FALSE",
        "context_forwarding_score": stringify(context.get("forwardingScore")),
        "context_mentions": stringify(mentions_payload) if mentions_payload else "",
        "context_disappearing_mode": stringify(disappearing),
        "context_paired_media_type": stringify(context.get("pairedMediaType")),
    }


def build_rows(events: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    for event in events:
        body = event.get("body", {})
        data = body.get("data", {})
        message = data.get("message", {})
        context = data.get("contextInfo") or {}

        trace_id = event.get("trace_id") or data.get("trace_id") or body.get("trace_id")
        unique_id = trace_id or data.get("key", {}).get("id")

        message_type = derive_message_type(message, data.get("messageType"))
        media_fields = extract_media_fields(message, message_type)
        context_fields = extract_context_fields(context)

        reaction = message.get("reactionMessage", {}) if message_type == "reaction" else {}
        location = message.get("locationMessage", {}) if message_type == "location" else {}
        contact = message.get("contactMessage", {}) if message_type == "contact" else {}

        from_me = data.get("key", {}).get("fromMe", False)
        remote_jid = data.get("key", {}).get("remoteJid") or ""
        push_name = data.get("pushName") or ""
        sender = body.get("sender") or remote_jid

        created_at = body.get("date_time") or epoch_to_iso(data.get("messageTimestamp"))

        row: Dict[str, str] = {column: "" for column in HEADER}
        row["id (UUIDv7)"] = stringify(unique_id)
        row["channel"] = "whatsapp"
        row["channel_message_id (current whatsapp_message_id this needs to be uniniversalized)"] = stringify(data.get("key", {}).get("id"))
        row["instance_configs_id"] = body.get("instance") or data.get("instance") or ""
        row["sender_id"] = stringify(sender)
        row["sender_name"] = stringify(push_name)
        row["recipient_id"] = stringify(remote_jid)
        row["conversation_id"] = stringify(remote_jid)
        row["message_type"] = message_type
        row["text_content"] = stringify(
            message.get("conversation")
            or message.get("caption")
            or contact.get("displayName")
        )
        row.update(media_fields)
        row["reaction_emoji"] = stringify(reaction.get("text"))
        row["reaction_to_message_id"] = stringify(reaction.get("key", {}).get("id"))
        row["location_lat"] = stringify(location.get("degreesLatitude"))
        row["location_lng"] = stringify(location.get("degreesLongitude"))
        row["contact_info"] = stringify(contact.get("vcard"))
        row["is_from_me"] = "TRUE" if from_me else "FALSE"
        row["is_edited"] = "FALSE"
        row["is_deleted"] = "FALSE"
        row["created_at"] = stringify(created_at)
        row["updated_at"] = stringify(created_at)
        row.update(context_fields)

        rows.append(row)

    return rows


def main() -> None:
    events = load_raw_events(RAW_EVENTS_PATH)
    rows = build_rows(events)

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Wrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
