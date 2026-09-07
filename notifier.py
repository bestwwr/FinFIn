import os
import time
from typing import List, Optional

import requests

TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"
MAX_CHARS = 4096  # Telegram message limit


def _send_to_chat(token: str, chat_id: str, chunks: list, max_retries: int) -> bool:
    for chunk in chunks:
        for attempt in range(max_retries):
            resp = requests.post(
                TELEGRAM_URL.format(token=token),
                json={"chat_id": chat_id, "text": chunk},
            )
            if resp.status_code == 200:
                break

            wait = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
            print(f"[notifier] Telegram error {resp.status_code} for chat {chat_id}, retry {attempt + 1}/{max_retries} in {wait}s...")
            time.sleep(wait)
        else:
            print(f"[notifier] Failed to deliver to chat {chat_id} after {max_retries} retries.")
            return False

    return True


def send_notification(message: str, chat_ids: Optional[List[str]] = None, max_retries: int = 3) -> bool:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    if chat_ids is None:
        # Fallback for callers that don't sync subscribers: TELEGRAM_CHAT_ID may hold
        # one id or a comma-separated list (e.g. "123,456").
        chat_ids = [c.strip() for c in os.environ["TELEGRAM_CHAT_ID"].split(",") if c.strip()]
    chunks = [message[i: i + MAX_CHARS] for i in range(0, len(message), MAX_CHARS)]

    ok = True
    for chat_id in chat_ids:
        if not _send_to_chat(token, chat_id, chunks, max_retries):
            ok = False

    return ok
