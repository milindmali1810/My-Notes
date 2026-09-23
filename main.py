"""Entry point for LOCAL polling runs. Run this on a schedule (e.g. Windows
Task Scheduler, every few minutes). Each run: poll for new channel posts,
run each through the staged pipeline, exit. No long-running process required.

The deployed version (api/webhook.py) does the same per-fragment work via
pipeline/orchestrator.py but is triggered by a Telegram webhook instead of
polling — see README.md.
"""
from pipeline import telegram_client
from pipeline.orchestrator import process_fragment


def main() -> None:
    # Stage 1 — TRIGGER: poll for new posts since the last run
    messages = telegram_client.fetch_new_channel_messages()
    print(f"{len(messages)} new fragment(s) found")
    for message in messages:
        process_fragment(message)


if __name__ == "__main__":
    main()
