import json
import os
from typing import List

import requests

SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), "subscribers.json")
GET_UPDATES_URL = "https://api.telegram.org/bot{token}/getUpdates"


def _load_state() -> dict:
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"chat_ids": [], "last_update_id": 0}


def _save_state(state: dict) -> None:
    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


def sync_subscribers() -> List[str]:
    """Poll Telegram for anyone who has messaged the bot (e.g. pressed Start)
    and add their chat to subscribers.json. Also merges in TELEGRAM_CHAT_ID
    so the original owner keeps receiving digests even before syncing.
    """
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    state = _load_state()
    known = set(state["chat_ids"])

    owner_ids = [c.strip() for c in os.environ.get("TELEGRAM_CHAT_ID", "").split(",") if c.strip()]
    known.update(owner_ids)

    try:
        resp = requests.get(
            GET_UPDATES_URL.format(token=token),
            params={"offset": state["last_update_id"] + 1, "timeout": 0},
            timeout=15,
        )
        resp.raise_for_status()
        updates = resp.json().get("result", [])
    except requests.RequestException as e:
        print(f"[subscribers] Failed to poll Telegram updates: {e}")
        updates = []

    added = []
    for update in updates:
        state["last_update_id"] = max(state["last_update_id"], update["update_id"])
        message = update.get("message") or update.get("my_chat_member")
        chat = (message or {}).get("chat")
        if chat and chat.get("id") is not None:
            chat_id = str(chat["id"])
            if chat_id not in known:
                known.add(chat_id)
                added.append(chat_id)

    state["chat_ids"] = sorted(known)
    _save_state(state)

    if added:
        print(f"[subscribers] New subscriber(s) added: {added}")

    return state["chat_ids"]
