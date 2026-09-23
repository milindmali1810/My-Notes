"""Stage 4 (PROCESSING) — score the fragment before attempting to draft anything.

Hard filter: does the fragment contain a specific claim, observation, or
number a post can be built around — not just a mood or vague reaction?
Most fragments should fail this. A high rejection rate is correct behavior,
not a bug — do not loosen this prompt to make more fragments pass.
"""
import json

from google import genai
from google.genai import types

import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)

_SYSTEM_PROMPT = """You triage raw voice-memo/text fragments for a founder's LinkedIn backlog.

Apply a HARD FILTER. A fragment is post-worthy ONLY if it contains a specific,
concrete claim, observation, or number that a post could be built around —
something with a testable edge to it.

A fragment is NOT post-worthy if it is only:
- a mood, feeling, or vague reaction ("today was rough", "feeling inspired")
- a generic truism with no specific claim ("consistency matters")
- a to-do or reminder with no idea in it
- too underdeveloped to identify what the actual claim even is

Most fragments (the large majority) should fail this filter. Do not be
generous. When genuinely unsure, fail it — a false negative costs nothing,
a false positive wastes a draft on weak material.

Reply with ONLY a JSON object, no other text:
{"passed": true|false, "reason": "one sentence why", "claim": "the specific claim/number/observation if passed, else null"}
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
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"passed": False, "reason": f"filter output was not parseable JSON: {raw!r}", "claim": None}
