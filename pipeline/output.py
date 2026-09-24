"""Stage 6 (OUTPUT) — return results for human review. Never posts, schedules, or publishes anything."""
from . import telegram_client


def send_voice_notice(fragment: dict) -> None:
    telegram_client.send_review_message(
        f"[voice note received — message_id {fragment['message_id']}]\n"
        "Transcription isn't wired up in this pipeline yet, so this fragment "
        "was logged but not triaged. Transcribe it manually or forward the text."
    )


def _sources_message(news: dict, used: dict | None, unused_note: str) -> str:
    items = news.get("news_items") or []
    read_of_note = []
    if news.get("crux"):
        searched = " | ".join(f'"{q}"' for q in news.get("search_queries", []))
        read_of_note = [f"Crux: {news['crux']}", f"Searched: {searched}"]

    if not items:
        checked = news.get("candidates_checked", 0)
        if checked:
            return "\n".join(
                ["SOURCES: none relevant enough."] + read_of_note
                + [f"{checked} results were checked and all were dropped as off-topic for the crux."]
            )
        return "\n".join(["SOURCES: none found."] + read_of_note)

    lines = ["SOURCES CONSIDERED (Google News)"] + read_of_note + [""]
    for i, item in enumerate(items, 1):
        tag = "  [USED IN DRAFT]" if item is used else ""
        lines += [
            f"{i}. {item['headline']}",
            f"   {item['source']}, {item['date']}  (relevance {item['relevance']}/10){tag}",
            f"   {item['url']}",
            "",
        ]
    if not used:
        lines.append(unused_note)
    return "\n".join(lines).rstrip()


def send_rejection(fragment: dict, verdict: dict, news: dict) -> None:
    telegram_client.send_review_message(
        "NO DRAFT — didn't clear the bar\n\n"
        f"Fragment: {fragment['text']}\n\n"
        f"Score: {verdict['score']}/10\n"
        f"Reason: {verdict['reason']}"
    )
    telegram_client.send_review_message(_sources_message(news, None, "No draft was made, so none of these were cited."))


def send_draft(fragment: dict, claim: str, context: dict, draft: dict) -> int | None:
    """Sends the sources message first, then the draft. Returns the draft
    message's Telegram id, so it can be linked to the drafts row for matching
    a later APPROVE/REJECT reply. Sources go in their own message because
    Telegram caps a message at 4096 characters."""
    telegram_client.send_review_message(
        _sources_message(context, draft.get("news_item"), "None of these fit naturally, so the draft doesn't cite any.")
    )

    lines = [
        "DRAFT READY FOR REVIEW",
        "",
        f"Fragment: {fragment['text']}",
        f"Claim: {claim}",
    ]
    news = draft.get("news_item")
    lines.append(f"News angle used: {news['headline']} (sources listed above)" if news else "News angle used: none (sources listed above)")
    if draft.get("tone_tension_flag"):
        lines.append("")
        lines.append(f"⚠ VOICE/CONTENT TENSION: {draft['tone_tension_note']}")
    lines.append("")
    lines.append("---")
    lines.append(draft["draft"])
    lines.append("")
    lines.append("Reply APPROVE or REJECT to this message to record your decision.")

    return telegram_client.send_review_message("\n".join(lines))
