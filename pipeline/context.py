"""Stage 3 (CONTEXT) — pull skill.txt voice guidance and a live news angle.

Two independent lookups, both gathered before any drafting is attempted:
  a) skill.txt — read fresh every run, never cached, so edits take effect immediately.
  b) a relevant, current news item related to the note's topic: Gemini extracts
     3-5 search keywords, those keywords hit Google News' public RSS search
     (no account or API key needed), and the top result is returned as a
     structured item. If nothing comes back, that's recorded explicitly
     rather than forcing a connection in the draft stage.
"""
import xml.etree.ElementTree as ET

import requests
from google import genai
from google.genai import types

import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)

_KEYWORD_SYSTEM_PROMPT = """Given a note fragment, extract 3-5 search keywords that would
find a relevant, current news article on the same topic. Reply with ONLY a
short search phrase (the keywords separated by spaces), no other text, no
quotes, no explanation.
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


def fetch_top_news(search_phrase: str) -> dict | None:
    if not search_phrase:
        return None
    resp = requests.get(
        _NEWS_RSS_URL,
        params={"q": search_phrase, "hl": "en-US", "gl": "US", "ceid": "US:en"},
        timeout=15,
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    item = root.find("./channel/item")
    if item is None:
        return None

    raw_title = (item.findtext("title") or "").strip()
    # Google News RSS titles are formatted "Headline - Source Name"
    if " - " in raw_title:
        headline, source = raw_title.rsplit(" - ", 1)
    else:
        headline, source = raw_title, "Google News"

    return {
        "headline": headline.strip(),
        "source": source.strip(),
        "date": (item.findtext("pubDate") or "").strip(),
        "url": (item.findtext("link") or "").strip(),
    }


def gather_context(fragment_text: str) -> dict:
    keywords = extract_keywords(fragment_text)
    return {
        "skill_reference": read_skill_file(),
        "news": fetch_top_news(keywords),
    }
