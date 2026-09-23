"""Stage 4 (PROCESSING) — score the fragment before attempting to draft anything.

Gemini scores the note 0-10 with a one-line reason. Below the pass threshold,
no draft is attempted and a short rejection goes back to Telegram instead.
Most fragments should score low. A high rejection rate is correct behavior,
not a bug — do not loosen this prompt to make more fragments pass.
"""
import json

from google import genai
from google.genai import types

import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)

_SYSTEM_PROMPT = """You score raw voice-memo/text fragments for a founder's LinkedIn backlog,
on a 0-10 scale of how post-worthy they are.

A fragment scores HIGH (6-10) only if it contains a specific, concrete claim,
observation, or number that a post could be built around — something with a
testable edge to it. Score higher the more specific and substantive it is.

A fragment scores LOW (0-5) if it is only:
- a mood, feeling, or vague reaction ("today was rough", "feeling inspired")
- a generic truism with no specific claim ("consistency matters")
- a to-do, reminder, or logistics note with no idea in it
- too underdeveloped to identify what the actual claim even is

Most fragments (the large majority) should score low. Do not be generous.
When genuinely unsure, score it low — a false negative costs nothing, a
false positive wastes a draft on weak material.

Reply with ONLY a JSON object, no other text:
{"score": 0-10, "reason": "one sentence why", "claim": "the specific claim/number/observation if score >= 6, else null"}
"""


def score_fragment(fragment_text: str) -> dict:
    response = _client.models.generate_content(
        model=config.FILTER_MODEL,
        contents=fragment_text,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    raw = (response.text or "").strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"passed": False, "score": 0, "reason": f"filter output was not parseable JSON: {raw!r}", "claim": None}

    result["passed"] = result.get("score", 0) >= config.SCORE_PASS_THRESHOLD
    return result
