"""Runs one fragment through stages 2-6. Shared by main.py (polling) and
api/webhook.py (Telegram webhook) so the staged logic exists in exactly one place.
"""
from . import capture, context, draft_stage, filter_stage, output


def process_fragment(message: dict) -> None:
    # Stage 2 — INPUT: log raw, no interpretation
    fragment = capture.log_fragment(message)

    if fragment["is_voice"]:
        output.send_voice_notice(fragment)
        return

    # Stage 4 — PROCESSING: hard filter before any drafting is attempted
    verdict = filter_stage.score_fragment(fragment["text"])
    if not verdict["passed"]:
        output.send_rejection(fragment, verdict)
        print(f"[reject] message_id={fragment['message_id']}: {verdict['reason']}")
        return

    # Stage 3 — CONTEXT: skill.txt + live search, only once we know it's worth drafting
    ctx = context.gather_context(fragment["text"])

    # Stage 5 — AI drafting
    draft = draft_stage.write_draft(fragment["text"], verdict["claim"], ctx)

    # Stage 6 — OUTPUT: hand back for review, nothing auto-published
    output.send_draft(fragment, verdict["claim"], ctx, draft)
    print(f"[draft] message_id={fragment['message_id']}: sent for review")
