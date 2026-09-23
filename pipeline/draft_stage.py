"""Stage 5 (AI drafting) — only runs for fragments that passed the stage 4 filter.

Drafts a LinkedIn post that:
  (a) matches skill.txt's voice (structure + lexical tics, per skill.txt itself)
  (b) is built around the fragment's specific claim, not a generic restatement
  (c) weaves in the stage-3 data point as supporting context, not a bolted-on
      intro line — and is skipped entirely if stage 3 found nothing relevant

Also checks for tension between skill.txt's voice and the fragment's actual
register (e.g. a rough unfiltered rant vs. a clinical/measured skill.txt) and
flags it instead of silently smoothing it away.
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
- If a current data point is supplied, weave it in as supporting context for
  the claim — not as a bolted-on "Did you know..." intro line.
- If no data point is supplied, do not invent one. Write the post on the
  fragment's claim alone.
- Never invent numbers, statistics, or specifics not present in the fragment
  or the supplied data point.
- Separately: compare the fragment's raw tone/register against skill.txt's
  voice. If the fragment is markedly rougher, angrier, or more unfiltered
  than skill.txt's typical register (e.g. a rant vs. a clinical/measured
  voice), do NOT silently sand it down to fit. Draft it as best you can and
  flag the tension explicitly instead.

Reply with ONLY a JSON object, no other text:
{{"draft": "the full LinkedIn post text", "tone_tension_flag": true|false, "tone_tension_note": "explanation if flagged, else null"}}
"""


def write_draft(fragment_text: str, claim: str, context: dict) -> dict:
    system = _SYSTEM_PROMPT.format(skill_text=context["skill_reference"])
    data_point = context.get("data_point")

    user_content = f"Fragment:\n{fragment_text}\n\nSpecific claim to build around:\n{claim}\n\n"
    user_content += (
        f"Current data point/news angle to weave in as support:\n{data_point}"
        if data_point
        else "No relevant current data point was found — write on the claim alone."
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
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"draft": raw, "tone_tension_flag": False, "tone_tension_note": "draft output was not valid JSON, showing raw text"}
