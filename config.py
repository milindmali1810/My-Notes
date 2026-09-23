import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

IS_SERVERLESS = bool(os.environ.get("VERCEL"))

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_SOURCE_CHANNEL_ID = os.environ["TELEGRAM_SOURCE_CHANNEL_ID"]
# Optional: without it, output.py logs instead of DMing (lets the webhook boot
# even before this is configured, rather than crash-looping on every update).
TELEGRAM_REVIEW_CHAT_ID = os.environ.get("TELEGRAM_REVIEW_CHAT_ID")

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
FILTER_MODEL = os.environ.get("FILTER_MODEL", "gemini-flash-latest")
DRAFTING_MODEL = os.environ.get("DRAFTING_MODEL", "gemini-pro-latest")

PROJECT_DIR = Path(__file__).parent

# Local runs read the live external file so edits take effect immediately.
# On Vercel there is no such filesystem to read, so the deployed function
# reads its own bundled copy instead (kept in sync manually when you edit
# your local skill.txt).
_BUNDLED_SKILL_PATH = PROJECT_DIR / "skill.txt"
_LOCAL_DEFAULT_SKILL_PATH = r"D:\Mesa\AI WORKFLOWS\skill.txt"
SKILL_PATH = Path(os.environ.get("SKILL_PATH", str(_BUNDLED_SKILL_PATH if IS_SERVERLESS else _LOCAL_DEFAULT_SKILL_PATH)))

STATE_DIR = PROJECT_DIR / "state"
OFFSET_FILE = STATE_DIR / "telegram_offset.json"
FRAGMENTS_LOG = STATE_DIR / "fragments_log.jsonl"

if not IS_SERVERLESS:
    STATE_DIR.mkdir(exist_ok=True)
