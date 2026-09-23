"""Stage 3 (CONTEXT) — pull skill.txt voice guidance and a live, current data point.

Two independent lookups, both gathered before any drafting is attempted:
  a) skill.txt — read fresh every run, never cached, so edits take effect immediately.
  b) A live web search for a current data point or news angle related to the
     fragment's topic, using Gemini's built-in Google Search grounding. If
     nothing relevant and recent turns up, that is recorded explicitly rather
     than forcing a connection in the draft stage.
"""
from google import genai
from google.genai import types

import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)

_SEARCH_SYSTEM_PROMPT = """You are a research assistant supporting a LinkedIn ghostwriter.
Given a raw note fragment, decide if there is a genuinely relevant, CURRENT
(recent) data point, statistic, or news item that connects to its topic.

Rules:
- Only report something if it is specifically relevant, not a generic tie-in.
- Prefer recent (last few months) sources; cite where it came from.
- If nothing relevant and recent turns up after searching, say so plainly:
  reply with exactly "NO_RELEVANT_CONTEXT_FOUND" and nothing else.
- Otherwise reply with 2-4 sentences: the data point/angle plus its source,
  no fluff, no "in today's fast-paced world" framing.
"""


def read_skill_file() -> str:
    return config.SKILL_PATH.read_text(encoding="utf-8")


def find_current_data_point(fragment_text: str) -> str | None:
    response = _client.models.generate_content(
        model=config.DRAFTING_MODEL,
        contents=f"Note fragment:\n\n{fragment_text}",
        config=types.GenerateContentConfig(
            system_instruction=_SEARCH_SYSTEM_PROMPT,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    result = (response.text or "").strip()

    if not result or "NO_RELEVANT_CONTEXT_FOUND" in result:
        return None
    return result


def gather_context(fragment_text: str) -> dict:
    return {
        "skill_reference": read_skill_file(),
        "data_point": find_current_data_point(fragment_text),
    }
