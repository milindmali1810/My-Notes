"""Stage 1 (TRIGGER), deployed variant. Telegram calls this URL directly
(POST) with each new update — see README.md for how the webhook gets
registered. Runs stages 2-6 via pipeline/orchestrator.py, same logic as the
local polling entry point (main.py). Also handles APPROVE/REJECT replies in
the review chat (stage 6b, MEMORY).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request  # noqa: E402

import config  # noqa: E402
from pipeline import telegram_client  # noqa: E402
from pipeline.orchestrator import process_fragment, process_review_reply  # noqa: E402

app = Flask(__name__)

WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET")


@app.route("/api/webhook", methods=["GET"])
def health():
    return "Telegram -> LinkedIn draft pipeline webhook is live.", 200


@app.route("/api/webhook", methods=["POST"])
def telegram_webhook():
    if WEBHOOK_SECRET and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return "forbidden", 403

    update = request.get_json(silent=True) or {}

    post = update.get("channel_post")
    if post:
        message = telegram_client.parse_channel_post(post)
        if message:
            process_fragment(message)
        return "", 200

    msg = update.get("message")
    if msg and str(msg.get("chat", {}).get("id")) == str(config.TELEGRAM_REVIEW_CHAT_ID):
        reply_to = msg.get("reply_to_message")
        if reply_to and "text" in msg:
            process_review_reply(reply_to["message_id"], msg["text"])
        return "", 200

    return "", 200  # anything else (edited posts, other chats, etc.) — ignore
