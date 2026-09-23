"""Stage 1 (TRIGGER), deployed variant. Telegram calls this URL directly
(POST) with each new update — see README.md for how the webhook gets
registered. Runs stages 2-6 via pipeline/orchestrator.py, same logic as the
local polling entry point (main.py).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request  # noqa: E402

from pipeline import telegram_client  # noqa: E402
from pipeline.orchestrator import process_fragment  # noqa: E402

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
    if not post:
        return "", 200  # not a channel post (e.g. edited_channel_post, other chat types) — ignore

    message = telegram_client.parse_channel_post(post)
    if not message:
        return "", 200  # different chat, or unsupported content type — ignore

    process_fragment(message)
    return "", 200
