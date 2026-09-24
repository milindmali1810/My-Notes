"""Stage 1 (TRIGGER) and Stage 6 (OUTPUT) — talking to Telegram.

Polling-based, not webhook-based: each run asks Telegram for updates since
the last saved offset, so this can be invoked on a schedule (e.g. Windows
Task Scheduler) instead of needing a always-on server.
"""
import json

import requests

import config

API_BASE = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def _load_offset() -> int:
    if config.OFFSET_FILE.exists():
        return json.loads(config.OFFSET_FILE.read_text())["offset"]
    return 0


def _save_offset(offset: int) -> None:
    config.OFFSET_FILE.write_text(json.dumps({"offset": offset}))


def parse_channel_post(post: dict) -> dict | None:
    """Shared by the polling path (main.py) and the webhook path (api/webhook.py).

    Returns None for posts outside the source channel or of an unsupported
    content type (only text and voice are handled).
    """
    if str(post["chat"]["id"]) != str(config.TELEGRAM_SOURCE_CHANNEL_ID):
        return None
    if "text" in post:
        return {"text": post["text"], "message_id": post["message_id"], "date": post["date"]}
    if "voice" in post:
        return {"voice": True, "message_id": post["message_id"], "date": post["date"]}
    return None


def fetch_new_channel_messages() -> list[dict]:
    """Poll getUpdates and return new posts from the source channel only.

    Local/polling path only (main.py). The deployed webhook does not call
    this — Telegram pushes each update directly to api/webhook.py instead.
    """
    offset = _load_offset()
    resp = requests.get(
        f"{API_BASE}/getUpdates",
        params={"offset": offset, "timeout": 0, "allowed_updates": json.dumps(["channel_post"])},
        timeout=30,
    )
    resp.raise_for_status()
    updates = resp.json()["result"]

    messages = []
    max_update_id = offset - 1
    for update in updates:
        max_update_id = max(max_update_id, update["update_id"])
        post = update.get("channel_post")
        if not post:
            continue
        message = parse_channel_post(post)
        if message:
            messages.append(message)

    if updates:
        _save_offset(max_update_id + 1)

    return messages


def _split_for_telegram(text: str, limit: int = 4000) -> list[str]:
    """Telegram rejects messages over 4096 characters, which would fail the
    webhook and make Telegram retry the update. Split on line breaks instead."""
    chunks, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if current and len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


def send_review_message(text: str) -> int | None:
    """Stage 6 (OUTPUT) — DM the review chat. Never touches LinkedIn or the source channel.

    Sent as plain text (no parse_mode): drafts can contain characters like
    * _ [ ] that would otherwise trip Telegram's Markdown parser and fail
    the send. Returns the id of the last message sent (needed to match a later
    APPROVE/REJECT reply back to this draft; the reply instruction sits at the
    end of the text, so it lands in that last message), or None if nothing
    was sent.
    """
    if not config.TELEGRAM_REVIEW_CHAT_ID:
        print(f"[TELEGRAM_REVIEW_CHAT_ID not set, would have sent]\n{text}")
        return None
    message_id = None
    for chunk in _split_for_telegram(text):
        resp = requests.post(
            f"{API_BASE}/sendMessage",
            json={"chat_id": config.TELEGRAM_REVIEW_CHAT_ID, "text": chunk},
            timeout=30,
        )
        resp.raise_for_status()
        message_id = resp.json()["result"]["message_id"]
    return message_id
