import os
import time
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from typing import List, Dict

# ──────────────────────────────────────────────────────────────────────────────
# System instruction: separates "role" from "task".
# The model weighs system_instruction more heavily than the main prompt,
# and it keeps the main prompt short, clean, and easy to adjust.
# ──────────────────────────────────────────────────────────────────────────────
SYSTEM_INSTRUCTION = """You are a professional investment news analyst. Write a morning digest that an investor can read in under 1 minute.

Writing principles you must always follow:
- Only include news that "affects investment decisions" — drop noise.
- Group related news together instead of listing items one by one.
- Each bullet is at most 1 line and leads with the "impact", not the headline.
- Include numbers/percentages/direction (▲▼) whenever the data is available.
- Be concise and to the point — no filler words.
- Never recommend buying/selling — analyze facts only."""

PROMPT_TEMPLATE = """Summarize the investment news for {date} from the following data:

{news_block}

Required format (max 900 characters):

🌅 FinFin Morning Digest — {date}

📌 Portfolio-impacting headlines:
- ...

📈 Market signals:
- ...

⚠️ Risks to watch:
- ...

💡 Overview:
..."""


def _build_news_block(articles: List[Dict]) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. [{a['source']}] {a['title']}")
        if a.get("published"):
            lines.append(f"   Time: {a['published']}")
        if a.get("summary"):
            lines.append(f"   Content: {a['summary'][:400]}")
    return "\n".join(lines)


def summarize_news(
    articles: List[Dict],
    digest_date: str = "",
    max_retries: int = 2,
) -> str:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    news_block = _build_news_block(articles)

    # ──────────────────────────────────────────────────────────────────────────
    # Generation config: thinking_budget ให้โมเดลคิดก่อนตอบ
    # temperature ต่ำ → output สม่ำเสมอ ไม่เพ้อ เหมาะกับงานข่าว
    # ──────────────────────────────────────────────────────────────────────────
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        thinking_config=types.ThinkingConfig(thinking_budget=2048),
        temperature=0.3,
        max_output_tokens=4096,
    )

    text = ""
    for attempt in range(max_retries + 1):
        try:
            prompt = PROMPT_TEMPLATE.format(
                news_block=news_block,
                date=digest_date or "today",
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config,
            )
            text = response.text or ""

            # เกณฑ์ผ่าน: ยาวพอ + มีหัวข้อหลักครบ
            if len(text) >= 100 and "📌" in text:
                return text

            print(
                f"[summarizer] Response too short or incomplete ({len(text)} chars), "
                f"retry ({attempt + 1}/{max_retries})..."
            )

        except genai_errors.ServerError as e:
            wait = 10 * (attempt + 1)  # 10s, 20s, 30s
            print(
                f"[summarizer] Server error ({e}), "
                f"รอ {wait}s แล้ว retry ({attempt + 1}/{max_retries})..."
            )
            if attempt < max_retries:
                time.sleep(wait)

    return text  # best effort
