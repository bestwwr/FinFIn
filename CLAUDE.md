# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Setup:**
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in real values
```

**Run:**
```bash
source venv/bin/activate
python main.py
```

**Trigger manually on GitHub Actions:**
```bash
gh workflow run "FinFin Morning Digest" --repo bestwwr/FinFIn
gh run watch --repo bestwwr/FinFIn  # watch live output
```

**Check logs (local):**
```bash
cat logs/finfin.log
```

## Architecture

FinFin is a **Basic Agent** (not a simple pipeline) — each step has its own decision logic and retry behavior before passing control to the next step.

```
main.py (orchestrator)
  → subscribers.py sync_subscribers()  → List[str]
  → fetcher.py     fetch_news()        → List[Dict]
  → summarizer.py  summarize_news()    → str
  → notifier.py    send_notification() → bool
```

**Key design decisions:**
- `subscribers.py` polls Telegram's `getUpdates` for anyone who has messaged the bot (e.g. pressed Start) and auto-adds their chat ID to `subscribers.json`. `TELEGRAM_CHAT_ID` (the owner) is always merged in too, so the original recipient never depends on the file. The digest is sent to every chat in the resulting list — no manual chat-ID collection needed.
- `fetcher.py` has 5 primary RSS feeds and 2 fallback feeds. If primary feeds return fewer than `min_articles`, fallback feeds are tried automatically.
- `summarizer.py` uses `gemini-2.5-flash` with structured JSON output (`response_schema=DigestOutput`) to classify articles and produce **two separate digests in one call**: Thailand-specific (SET, THB, BOT policy, Thai-listed companies) and Global (everything else relevant to a diversified portfolio). It retries up to 2 times if the combined response is under 100 chars, and handles `503 ServerError` with a 10s/20s/30s backoff.
- `notifier.py` sends to Telegram (function is named `send_notification`) for each chat ID passed to it. Retries 3 times with exponential backoff (1s/2s/4s) per chat on failure. `main.py` calls it once per digest section, so each subscriber gets **2 separate Telegram messages/bubbles** — Thailand first, then Global (a section is skipped if empty that day).
- Decision points are logged with `[decision]` prefix for easy tracing.

## Environment Variables

```
GEMINI_API_KEY=        # Google AI Studio — must be from a project with free tier quota
TELEGRAM_BOT_TOKEN=    # from @BotFather
TELEGRAM_CHAT_ID=      # from @userinfobot — owner's id(s); comma-separated for more than one, e.g. 111111,222222
```

In GitHub Actions these are stored as repository secrets (Settings → Secrets → Actions).

## Subscribers (`subscribers.json`)

Tracks who receives the digest: `{"chat_ids": [...], "last_update_id": <int>}`. Anyone who messages the bot in Telegram gets auto-added on the next run via `sync_subscribers()`. The GitHub Actions workflow commits this file back to the repo after each run (`Persist subscriber list` step) so new subscribers stick — this requires `permissions: contents: write` on the workflow.

## Deployment

Runs automatically every morning via `.github/workflows/morning-digest.yml`. GitHub delays scheduled runs by hours, so the workflow triggers hourly from 02:23 to 08:23 Bangkok, and the `Check send window` step lets only the first run at or after **07:30 Bangkok** send. `last_sent.txt` (committed back by the workflow) records the Bangkok date of the last send so later runs that day skip. Manual runs (Actions tab or `gh workflow run`) always send.

## Roadmap (Level 2)

Next planned upgrade: Tool-Use Agent — let Gemini call `get_stock_price()` and `get_exchange_rate()` via Function Calling before generating the summary.
