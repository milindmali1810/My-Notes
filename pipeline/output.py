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
        "NOT POST-WORTHY\n\n"
        f"Fragment: {fragment['text']}\n\n"
        f"Reason: {verdict['reason']}"
    )


def send_draft(fragment: dict, claim: str, context: dict, draft: dict) -> None:
    lines = [
        "DRAFT READY FOR REVIEW",
        "",
        f"Fragment: {fragment['text']}",
        f"Claim: {claim}",
    ]
    if context.get("data_point"):
        lines.append(f"Context used: {context['data_point']}")
    else:
        lines.append("Context used: none found")
    if draft.get("tone_tension_flag"):
        lines.append("")
        lines.append(f"⚠ VOICE/CONTENT TENSION: {draft['tone_tension_note']}")
    lines.append("")
    lines.append("---")
    lines.append(draft["draft"])

    telegram_client.send_review_message("\n".join(lines))
