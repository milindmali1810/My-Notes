"""Stage 3 (CONTEXT) — pull skill.txt voice guidance and a live news angle.

Two independent lookups, both gathered before any drafting is attempted:
  a) skill.txt — read fresh every run, never cached, so edits take effect immediately.
  b) a relevant, current news item related to the note's topic: Gemini writes a
     specific 3-6 word search query, which hits Google News' public RSS search
     (no account or API key needed). Gemini then scores each headline against
     the note and drops the off-topic ones; the survivors (at most 5) go to the
     reviewer with their relevance score. If none survive, that's stated
     explicitly rather than forcing a connection in the draft stage.
"""
import json
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests
from google import genai
from google.genai import types

import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)

_KEYWORD_SYSTEM_PROMPT = """Write a Google News search query that would find recent news about the specific subject of the note you are given.

Rules:
- 3 to 6 words. Name the concrete subject: the industry or product category, company or platform names, and the place if the note signals one (a rupee amount means India).
- Never use abstract filler words: trends, behavior, behaviour, impact, shift, insights, growth, market, consumer, future, importance.
- Reply with ONLY the query. No quotes, no explanation.

Examples:
Note about moving a software product from monthly to annual-only pricing -> SaaS annual-only pricing subscription conversion
Note about a bakery's oven breaking down before a big order -> commercial bakery equipment breakdown small business
"""

_RELEVANCE_SYSTEM_PROMPT = """You check whether news headlines are relevant to a note.

For each numbered headline, score 0-10 how directly it covers the specific subject of the note (the same industry, product category, platform or place).
- 8-10: about exactly this subject.
- 6-7: same industry or topic, useful background for a post on it.
- 0-5: a different topic, a generic report on a different product category, or it only shares a keyword with the note.
Be strict.

Reply with ONLY a JSON object with one entry per headline: {"scores": [{"n": 1, "score": 7}, {"n": 2, "score": 2}]}
"""

_NEWS_RSS_URL = "https://news.google.com/rss/search"


def read_skill_file() -> str:
    return config.SKILL_PATH.read_text(encoding="utf-8")


def extract_keywords(fragment_text: str) -> str:
    response = _client.models.generate_content(
        model=config.FILTER_MODEL,
        contents=fragment_text,
        config=types.GenerateContentConfig(system_instruction=_KEYWORD_SYSTEM_PROMPT),
    )
    return (response.text or "").strip()


def _format_date(raw: str) -> str:
    try:
        return parsedate_to_datetime(raw).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return raw


def fetch_news(search_phrase: str, limit: int = 5) -> list[dict]:
    if not search_phrase:
        return []
    resp = requests.get(
        _NEWS_RSS_URL,
        params={"q": search_phrase, "hl": "en-US", "gl": "US", "ceid": "US:en"},
        timeout=15,
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    items = []
    for item in root.findall("./channel/item")[:limit]:
        raw_title = (item.findtext("title") or "").strip()
        # Google News RSS titles are formatted "Headline - Source Name"
        if " - " in raw_title:
            headline, source = raw_title.rsplit(" - ", 1)
        else:
            headline, source = raw_title, "Google News"
        items.append({
            "headline": headline.strip(),
            "source": source.strip(),
            "date": _format_date((item.findtext("pubDate") or "").strip()),
            "url": (item.findtext("link") or "").strip(),
        })
    return items


def _score_headlines(fragment_text: str, items: list[dict]) -> dict[int, int]:
    headlines = "\n".join(f"{i}. {n['headline']} ({n['source']}, {n['date']})" for i, n in enumerate(items, 1))
    response = _client.models.generate_content(
        model=config.FILTER_MODEL,
        contents=f"Note:\n{fragment_text}\n\nHeadlines:\n{headlines}",
        config=types.GenerateContentConfig(
            system_instruction=_RELEVANCE_SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    return {s["n"]: s["score"] for s in json.loads(response.text)["scores"]}


def filter_relevant(fragment_text: str, items: list[dict], limit: int = 5) -> list[dict]:
    if not items:
        return []
    scores = _score_headlines(fragment_text, items)
    kept = [
        {**item, "relevance": scores.get(i, 0)}
        for i, item in enumerate(items, 1)
        if scores.get(i, 0) >= config.NEWS_RELEVANCE_THRESHOLD
    ]
    return sorted(kept, key=lambda item: -item["relevance"])[:limit]


def find_news(fragment_text: str) -> dict:
    keywords = extract_keywords(fragment_text)
    candidates = fetch_news(keywords, limit=10)
    return {
        "search_phrase": keywords,
        "candidates_checked": len(candidates),
        "news_items": filter_relevant(fragment_text, candidates),
    }


def gather_context(news: dict) -> dict:
    return {"skill_reference": read_skill_file(), **news}
