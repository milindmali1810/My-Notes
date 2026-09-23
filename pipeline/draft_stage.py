"""Stage 5 (AI drafting) — only runs for fragments that passed the stage 4 filter.

Drafts a LinkedIn post that:
  (a) matches skill.txt's voice (structure + lexical tics, per skill.txt itself)
  (b) is built around the fragment's specific claim, not a generic restatement
  (c) uses the stage-3 news item as supporting context ONLY if it's genuinely
      relevant — the model decides and reports whether it used it

Also checks for tension between skill.txt's voice and the fragment's actual
register (e.g. a rough unfiltered rant vs. a clinical/measured skill.txt) and
flags it instead of silently smoothing it away.

Whenever a news item is used, a verify-flag footer is appended in code (not
by the model) using the source's actual headline/date/link, so nothing about
the citation can be hallucinated.
"""
import json

from google import genai
from google.genai import types

import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)

_SYSTEM_PROMPT = """You write a single LinkedIn post by transferring a founder's voice
(defined below in skill.txt) onto new material (a note fragment + its specific claim).

skill.txt — voice/style reference, follow it exactly, including its own
instructions about which parts of a corpus constitute "voice" vs "content":
---
{skill_text}
---

Ground rules:
- The post must be built AROUND the fragment's specific claim/number/observation,
  not a vague restatement of it.
- A candidate news item may be supplied below. If it is genuinely relevant, use
  it to make the post timely, woven in as supporting context — not as a
  bolted-on "Did you know..." intro line. If it doesn't fit naturally, ignore
  it entirely. Report which you did via used_news.
- Never invent numbers, statistics, or specifics not present in the fragment
  or the supplied news item.
- Separately: compare the fragment's raw tone/register against skill.txt's
  voice. If the fragment is markedly rougher, angrier, or more unfiltered
  than skill.txt's typical register (e.g. a rant vs. a clinical/measured
  voice), do NOT silently sand it down to fit. Draft it as best you can and
  flag the tension explicitly instead.

Reply with ONLY a JSON object, no other text:
{{"draft": "the full LinkedIn post text", "used_news": true|false, "tone_tension_flag": true|false, "tone_tension_note": "explanation if flagged, else null"}}
"""

_VERIFY_FOOTER = """
---
NEWS SOURCE: {headline}
FROM: {source} · {date}
LINK: {url}
⚠ Check this before publishing — you are the author of this claim
---"""


def write_draft(fragment_text: str, claim: str, context: dict) -> dict:
    system = _SYSTEM_PROMPT.format(skill_text=context["skill_reference"])
    news = context.get("news")

    user_content = f"Fragment:\n{fragment_text}\n\nSpecific claim to build around:\n{claim}\n\n"
    user_content += (
        f"Candidate news item:\nHeadline: {news['headline']}\nSource: {news['source']} ({news['date']})\n"
        if news
        else "No relevant news item was found — write on the claim alone."
    )

    response = _client.models.generate_content(
        model=config.DRAFTING_MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
        ),
    )
    raw = (response.text or "").strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"draft": raw, "used_news": False, "tone_tension_flag": False, "tone_tension_note": "draft output was not valid JSON, showing raw text"}

    # This footer is mandatory whenever news was used, per the case's
    # requirement that nothing gets published in Meera's name unverified —
    # built here from the real fetched data, never from the model's own text.
    if result.get("used_news") and news:
        result["draft"] = result["draft"].rstrip() + _VERIFY_FOOTER.format(**news)
    else:
        result["used_news"] = False

    return result
