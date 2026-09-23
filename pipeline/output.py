"""Stage 6 (OUTPUT) — return results for human review. Never posts, schedules, or publishes anything."""
from . import telegram_client


def send_voice_notice(fragment: dict) -> None:
    telegram_client.send_review_message(
        f"[voice note received — message_id {fragment['message_id']}]\n"
        "Transcription isn't wired up in this pipeline yet, so this fragment "
        "was logged but not triaged. Transcribe it manually or forward the text."
    )


def send_rejection(fragment: dict, verdict: dict) -> None:
    telegram_client.send_review_message(
        "NO DRAFT — didn't clear the bar\n\n"
        f"Fragment: {fragment['text']}\n\n"
        f"Score: {verdict['score']}/10\n"
        f"Reason: {verdict['reason']}"
    )


def send_draft(fragment: dict, claim: str, context: dict, draft: dict) -> int | None:
    """Returns the sent Telegram message id, so it can be linked to the
    drafts row for matching a later APPROVE/REJECT reply."""
    lines = [
        "DRAFT READY FOR REVIEW",
        "",
        f"Fragment: {fragment['text']}",
        f"Claim: {claim}",
    ]
    news = context.get("news")
    lines.append(f"News angle used: {news['headline']}" if news and draft.get("used_news") else "News angle used: none")
    if draft.get("tone_tension_flag"):
        lines.append("")
        lines.append(f"⚠ VOICE/CONTENT TENSION: {draft['tone_tension_note']}")
    lines.append("")
    lines.append("---")
    lines.append(draft["draft"])
    lines.append("")
    lines.append("Reply APPROVE or REJECT to this message to record your decision.")

    return telegram_client.send_review_message("\n".join(lines))
