"""Runs one fragment through stages 2-6. Shared by main.py (polling) and
api/webhook.py (Telegram webhook) so the staged logic exists in exactly one place.
"""
from . import capture, context, db, draft_stage, filter_stage, output, telegram_client


def process_fragment(message: dict) -> None:
    # Stage 2 — INPUT: log raw, no interpretation
    fragment = capture.log_fragment(message)
    note_id = db.insert_note(fragment)

    if fragment["is_voice"]:
        output.send_voice_notice(fragment)
        return

    # Stage 4 — PROCESSING: score before any drafting is attempted
    verdict = filter_stage.score_fragment(fragment["text"])
    db.update_note_scored(note_id, verdict)

    # Stage 3 — CONTEXT (news): runs for every note, so even a rejection shows what was found
    try:
        news = context.find_news(fragment["text"])
    except Exception as exc:
        print(f"[news lookup failed] {exc}")
        news = {"search_phrase": "", "news_items": []}

    if not verdict["passed"]:
        output.send_rejection(fragment, verdict, news)
        print(f"[reject] message_id={fragment['message_id']}: score={verdict['score']} {verdict['reason']}")
        return

    # Stage 3 — CONTEXT (voice): skill.txt, only once we know it's worth drafting
    ctx = context.gather_context(news)
    db.record_voice_skill_snapshot(ctx["skill_reference"])

    # Stage 5 — AI drafting
    draft = draft_stage.write_draft(fragment["text"], verdict["claim"], ctx)

    # Stage 6 — OUTPUT + MEMORY: hand back for review, record as pending, nothing auto-published
    draft_id = db.insert_draft(note_id, draft, draft.get("news_item"))
    sent_message_id = output.send_draft(fragment, verdict["claim"], ctx, draft)
    if sent_message_id:
        db.set_draft_telegram_message_id(draft_id, sent_message_id)
    print(f"[draft] message_id={fragment['message_id']}: sent for review (draft_id={draft_id})")


def process_review_reply(reply_to_message_id: int, reply_text: str) -> bool:
    """Handles a Meera reply of APPROVE/REJECT to a draft message. Returns
    True if it matched a known draft and was recorded."""
    decision = reply_text.strip().upper()
    if decision not in ("APPROVE", "REJECT"):
        return False

    draft = db.get_draft_by_telegram_message_id(reply_to_message_id)
    if not draft:
        return False

    status = "approved" if decision == "APPROVE" else "rejected"
    db.update_draft_status(draft["id"], status)
    telegram_client.send_review_message(f"Recorded: draft {draft['id']} marked {status}.")
    return True
