import os
import time
import requests

TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"
MAX_CHARS = 4096  # Telegram message limit


def send_notification(message: str, max_retries: int = 3) -> bool:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    chunks = [message[i: i + MAX_CHARS] for i in range(0, len(message), MAX_CHARS)]

    for chunk in chunks:
        for attempt in range(max_retries):
            resp = requests.post(
                TELEGRAM_URL.format(token=token),
                json={"chat_id": chat_id, "text": chunk},
            )
            if resp.status_code == 200:
                break

            wait = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
            print(f"[notifier] Telegram error {resp.status_code}, retry {attempt + 1}/{max_retries} in {wait}s...")
            time.sleep(wait)
        else:
            print(f"[notifier] Failed after {max_retries} retries.")
            return False

    return True
