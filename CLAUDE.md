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
- `summarizer.py` uses `gemini-2.5-flash`. It retries up to 2 times if the response is under 100 chars, and handles `503 ServerError` with a 10s/20s/30s backoff.
- `notifier.py` sends to Telegram (function is named `send_notification`) for each chat ID passed to it. Retries 3 times with exponential backoff (1s/2s/4s) per chat on failure.
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

Runs automatically every day at **08:00 Bangkok time (01:00 UTC)** via `.github/workflows/morning-digest.yml`. Can also be triggered manually from the Actions tab or via `gh workflow run`.

Local cronjob (backup) is set at `0 8 * * *` using the venv Python binary directly.

## Roadmap (Level 2)

Next planned upgrade: Tool-Use Agent — let Gemini call `get_stock_price()` and `get_exchange_rate()` via Function Calling before generating the summary.
