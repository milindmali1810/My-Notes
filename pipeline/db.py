"""Stage 6b (MEMORY) — thin wrapper over Supabase's REST API (PostgREST).

No supabase-py dependency; these are just tables, so plain REST calls with
the anon key keep the dependency list small. RLS is disabled on these three
tables (see the migration) since this pipeline is the only writer/reader and
is never exposed to a browser.
"""
import requests

import config

_HEADERS = {
    "apikey": config.SUPABASE_KEY,
    "Authorization": f"Bearer {config.SUPABASE_KEY}",
    "Content-Type": "application/json",
}
_REST_BASE = f"{config.SUPABASE_URL}/rest/v1"


def insert_note(fragment: dict) -> int:
    resp = requests.post(
        f"{_REST_BASE}/notes",
        headers={**_HEADERS, "Prefer": "return=representation"},
        json={
            "telegram_message_id": fragment["message_id"],
            "text": fragment["text"],
            "is_voice": fragment["is_voice"],
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()[0]["id"]


def update_note_scored(note_id: int, verdict: dict) -> None:
    decision = "passed" if verdict["passed"] else "rejected"
    resp = requests.patch(
        f"{_REST_BASE}/notes?id=eq.{note_id}",
        headers=_HEADERS,
        json={
            "score": verdict["score"],
            "reason": verdict["reason"],
            "claim": verdict.get("claim"),
            "decision": decision,
        },
        timeout=15,
    )
    resp.raise_for_status()


def insert_draft(note_id: int, draft: dict, news: dict | None) -> int:
    resp = requests.post(
        f"{_REST_BASE}/drafts",
        headers={**_HEADERS, "Prefer": "return=representation"},
        json={
            "note_id": note_id,
            "draft_text": draft["draft"],
            "used_news": bool(news),
            "news_headline": news["headline"] if news else None,
            "news_source": news["source"] if news else None,
            "news_date": news["date"] if news else None,
            "news_url": news["url"] if news else None,
            "tone_tension_flag": draft.get("tone_tension_flag", False),
            "tone_tension_note": draft.get("tone_tension_note"),
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()[0]["id"]


def set_draft_telegram_message_id(draft_id: int, telegram_message_id: int) -> None:
    resp = requests.patch(
        f"{_REST_BASE}/drafts?id=eq.{draft_id}",
        headers=_HEADERS,
        json={"telegram_sent_message_id": telegram_message_id},
        timeout=15,
    )
    resp.raise_for_status()


def get_draft_by_telegram_message_id(telegram_message_id: int) -> dict | None:
    resp = requests.get(
        f"{_REST_BASE}/drafts",
        headers=_HEADERS,
        params={"telegram_sent_message_id": f"eq.{telegram_message_id}", "limit": 1},
        timeout=15,
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def update_draft_status(draft_id: int, status: str) -> None:
    """updated_at is set by the drafts_set_updated_at trigger, not here."""
    resp = requests.patch(
        f"{_REST_BASE}/drafts?id=eq.{draft_id}",
        headers=_HEADERS,
        json={"status": status},
        timeout=15,
    )
    resp.raise_for_status()


def record_voice_skill_snapshot(content: str) -> None:
    resp = requests.post(
        f"{_REST_BASE}/voice_skill",
        headers=_HEADERS,
        json={"content": content},
        timeout=15,
    )
    resp.raise_for_status()
