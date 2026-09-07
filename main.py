import os
from datetime import datetime
from dotenv import load_dotenv

from fetcher import fetch_news
from summarizer import summarize_news
from notifier import send_notification
from subscribers import sync_subscribers

load_dotenv()


def run_morning_digest() -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] FinFin Morning Digest starting...")

    print("  [0/3] Syncing subscribers...")
    chat_ids = sync_subscribers()

    if not chat_ids:
        print("  [decision] No subscribers yet → nothing to send. Message the bot to subscribe.")
        return

    print(f"  [decision] {len(chat_ids)} subscriber(s) → proceeding to fetch news.")

    # --- Fetcher Agent ---
    print("  [1/3] Fetching news...")
    articles = fetch_news(min_articles=5, max_per_feed=5, hours_back=18)

    if not articles:
        print("  [decision] No articles found → sending warning.")
        send_notification("⚠️ FinFin: ไม่พบข่าวการลงทุนในช่วง 18 ชั่วโมงที่ผ่านมา", chat_ids=chat_ids)
        return

    print(f"  [decision] Got {len(articles)} articles → proceeding to summarize.")

    # --- Summarizer Agent ---
    print("  [2/3] Summarizing with Gemini...")
    digest_date = datetime.now().strftime("%d %b %Y")
    summary = summarize_news(articles, digest_date=digest_date)

    if not summary:
        print("  [decision] Summary empty → aborting.")
        return

    print(f"  [decision] Summary ready ({len(summary)} chars) → sending.")

    # --- Notifier Agent ---
    print("  [3/3] Sending to Telegram...")
    ok = send_notification(summary, chat_ids=chat_ids)

    if ok:
        print("  Done! Digest sent successfully.")
    else:
        print("  Failed to deliver digest.")


if __name__ == "__main__":
    run_morning_digest()
