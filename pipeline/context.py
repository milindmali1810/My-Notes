"""Stage 3 (CONTEXT) — pull skill.txt voice guidance and a live news angle.

Two independent lookups, both gathered before any drafting is attempted:
  a) skill.txt — read fresh every run, never cached, so edits take effect immediately.
  b) news that bears on the crux of the note: Gemini first distills the note's
     central idea, then writes three Google News queries from it (specific,
     broader theme, news hook). Those hit Google News' public RSS search (no
     account or API key needed) and the results are merged. Gemini then scores
     each headline against the crux and drops the off-topic ones; the survivors
     (at most 5) go to the reviewer with their relevance score. If none
     survive, that's stated explicitly rather than forcing a connection in the
     draft stage.
"""
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests
from google import genai
from google.genai import types

import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)

_CRUX_SYSTEM_PROMPT = """You read a founder's raw note and prepare a Google News search for it.

Step 1, find the crux: the single central idea or insight the note is really about, in one sentence. Look past incidental detail (supplier names, exact figures, scene-setting) unless the point depends on it.

Step 2, write 3 Google News search queries, 3 to 6 words each, that would find recent articles bearing on the crux:
1. specific: the concrete subject and the issue.
2. broader: the wider industry theme or debate the crux belongs to.
3. news hook: a recent event, regulation, lawsuit, report or company move the crux connects to.

Rules for the queries:
- Name concrete things: the industry or product category, company or platform names, and the place if the note signals one (a rupee amount means India).
- Never use abstract filler words: trends, behavior, behaviour, impact, shift, insights, growth, market, consumer, future, importance.
- No quotes.

Reply with ONLY a JSON object: {"crux": "one sentence", "queries": ["specific query", "broader query", "news hook query"]}
"""

_RELEVANCE_SYSTEM_PROMPT = """You check whether news headlines are relevant to a note.

You are given the note and its crux (the central idea it is really about). For each numbered headline, score 0-10 how directly it bears on the crux, not just on the note's general topic.
- 8-10: directly supports, illustrates or challenges the crux.
- 6-7: same industry and a closely related issue, useful context for a post on the crux.
- 0-5: a different issue, a generic report on a different product category, or it only shares keywords or the industry with the note.
Be strict.

Reply with ONLY a JSON object with one entry per headline: {"scores": [{"n": 1, "score": 7}, {"n": 2, "score": 2}]}
"""

_NEWS_RSS_URL = "https://news.google.com/rss/search"


def read_skill_file() -> str:
    return config.SKILL_PATH.read_text(encoding="utf-8")


def find_crux(fragment_text: str) -> dict:
    response = _client.models.generate_content(
        model=config.FILTER_MODEL,
        contents=fragment_text,
        config=types.GenerateContentConfig(
            system_instruction=_CRUX_SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    result = json.loads(response.text)
    return {"crux": result["crux"].strip(), "queries": [q.strip() for q in result["queries"] if q.strip()]}


def _parse_date(raw: str) -> datetime | None:
    try:
        published = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    return published if published.tzinfo else published.replace(tzinfo=timezone.utc)


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

    cutoff = datetime.now(timezone.utc) - timedelta(days=config.NEWS_MAX_AGE_DAYS)
    items = []
    for item in root.findall("./channel/item"):
        raw_date = (item.findtext("pubDate") or "").strip()
        published = _parse_date(raw_date)
        if published and published < cutoff:
            continue
        raw_title = (item.findtext("title") or "").strip()
        # Google News RSS titles are formatted "Headline - Source Name"
        if " - " in raw_title:
            headline, source = raw_title.rsplit(" - ", 1)
        else:
            headline, source = raw_title, "Google News"
        items.append({
            "headline": headline.strip(),
            "source": source.strip(),
            "date": published.strftime("%d %b %Y") if published else raw_date,
            "url": (item.findtext("link") or "").strip(),
        })
        if len(items) == limit:
            break
    return items


def _score_headlines(fragment_text: str, crux: str, items: list[dict]) -> dict[int, int]:
    headlines = "\n".join(f"{i}. {n['headline']} ({n['source']}, {n['date']})" for i, n in enumerate(items, 1))
    response = _client.models.generate_content(
        model=config.FILTER_MODEL,
        contents=f"Note:\n{fragment_text}\n\nCrux: {crux}\n\nHeadlines:\n{headlines}",
        config=types.GenerateContentConfig(
            system_instruction=_RELEVANCE_SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    return {s["n"]: s["score"] for s in json.loads(response.text)["scores"]}


def filter_relevant(fragment_text: str, crux: str, items: list[dict], limit: int = 5) -> list[dict]:
    if not items:
        return []
    scores = _score_headlines(fragment_text, crux, items)
    kept = [
        {**item, "relevance": scores.get(i, 0)}
        for i, item in enumerate(items, 1)
        if scores.get(i, 0) >= config.NEWS_RELEVANCE_THRESHOLD
    ]
    return sorted(kept, key=lambda item: -item["relevance"])[:limit]


def find_news(fragment_text: str) -> dict:
    understanding = find_crux(fragment_text)

    candidates, seen = [], set()
    for query in understanding["queries"]:
        try:
            results = fetch_news(query, limit=10)
        except (requests.RequestException, ET.ParseError) as exc:
            print(f"[news search failed for {query!r}] {exc}")
            continue
        for item in results:
            if item["url"] not in seen:
                seen.add(item["url"])
                candidates.append(item)

    return {
        "crux": understanding["crux"],
        "search_queries": understanding["queries"],
        "candidates_checked": len(candidates),
        "news_items": filter_relevant(fragment_text, understanding["crux"], candidates),
    }


def gather_context(news: dict) -> dict:
    return {"skill_reference": read_skill_file(), **news}
