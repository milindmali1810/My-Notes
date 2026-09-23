# Telegram → LinkedIn draft pipeline

Staged pipeline: Telegram channel post → logged raw → filtered hard →
(only if it passes) drafted in your voice with a live data point → sent back
to you on Telegram for review. **Nothing is ever posted to LinkedIn
automatically.**

## Stages (see `pipeline/`)

1. **TRIGGER** (`telegram_client.fetch_new_channel_messages`) — poll Telegram for new posts in the source channel.
2. **INPUT** (`capture.py`) — log the raw fragment as-is with a timestamp, no cleanup.
3. **CONTEXT** (`context.py`) — read `skill.txt` + live web search for a current, relevant data point.
4. **PROCESSING** (`filter_stage.py`) — hard pass/fail filter. Most fragments fail; that's expected.
5. **AI drafting** (`draft_stage.py`) — only for fragments that passed.
6. **OUTPUT** (`output.py` / `telegram_client.send_review_message`) — DM you the draft or the rejection, for manual review.

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get your bot token** — you already registered a bot via @BotFather; grab
   its token from the chat with BotFather (`/mybots` → your bot → API Token).

3. **Add the bot as an admin of "My notes"** — Telegram only delivers
   `channel_post` updates to bots that are admins of the channel. Channel
   settings → Administrators → add your bot.

4. **Find the channel's numeric chat ID**
   - Post any message in "My notes".
   - Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser.
   - Look for `"channel_post": {"chat": {"id": -100XXXXXXXXXX, ...`. That
     negative number is `TELEGRAM_SOURCE_CHANNEL_ID`.

5. **Find your review chat ID** (where drafts get DMed to you)
   - Open a private chat with your bot and send it any message (e.g. `/start`).
   - Reload the same `getUpdates` URL.
   - Look for `"message": {"chat": {"id": XXXXXXXXX, ...` under your DM —
     that's `TELEGRAM_REVIEW_CHAT_ID`.

6. **Copy `.env.example` to `.env`** and fill in all values (bot token,
   channel ID, review chat ID, your `GEMINI_API_KEY`). `SKILL_PATH`
   already defaults to `D:\Mesa\AI WORKFLOWS\skill.txt`.

7. **Test one manual run**
   ```bash
   python main.py
   ```
   Post something in "My notes" first so there's something to fetch.

8. **Schedule it** — Windows Task Scheduler, action: run
   `python "C:\Users\Milind M\AI\telegram-linkedin-pipeline\main.py"` on
   whatever interval you want checked (e.g. every 15 minutes). Each run only
   processes messages newer than the last run (offset tracked in
   `state/telegram_offset.json`).

## State files (created on first run, not committed)

- `state/telegram_offset.json` — last processed Telegram update ID.
- `state/fragments_log.jsonl` — every raw fragment ever captured, one JSON object per line.

## Guardrails baked into this pipeline

- No LinkedIn API integration exists anywhere in this code — there is
  physically nothing that could auto-publish.
- The filter (stage 4) is intentionally strict. If you find yourself wanting
  to loosen it because "too many" fragments are getting rejected, don't —
  per the source case, most fragments genuinely aren't post-worthy, and a
  high rejection rate is the pipeline working, not failing.
- Voice/content tone tension (e.g. a raw rant against a measured skill.txt)
  is flagged in the review message, never silently smoothed away.
- Voice messages are logged but not transcribed (no transcription service is
  wired up) — you'll get a notice to handle those manually.
