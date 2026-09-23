"""Stage 2 (INPUT) — capture the raw fragment as-is, no cleaning or interpretation."""
import json
from datetime import datetime, timezone

import config


def log_fragment(message: dict) -> dict:
    """Record the raw fragment, untouched, with a capture timestamp.

    Locally this appends to state/fragments_log.jsonl. On Vercel the
    filesystem is ephemeral and wiped after each invocation, so instead this
    just prints the entry (captured in Vercel's function logs) — no
    persistent fragment log in the deployed version.
    """
    entry = {
        "message_id": message["message_id"],
        "telegram_date": message["date"],
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "text": message.get("text"),
        "is_voice": message.get("voice", False),
    }
    line = json.dumps(entry, ensure_ascii=False)
    if config.IS_SERVERLESS:
        print(line)
    else:
        with open(config.FRAGMENTS_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    return entry
