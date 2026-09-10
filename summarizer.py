import os
import time
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from pydantic import BaseModel
from typing import List, Dict

# ──────────────────────────────────────────────────────────────────────────────
# System instruction: separates "role" from "task".
# The model weighs system_instruction more heavily than the main prompt,
# and it keeps the main prompt short, clean, and easy to adjust.
# ──────────────────────────────────────────────────────────────────────────────
SYSTEM_INSTRUCTION = """You are a professional investment news analyst. Classify each news item and write two separate morning digests, each readable in under 1 minute:

1. THAILAND DIGEST — only news that directly affects Thai-market investors: SET index movers, Thai baht (THB), Bank of Thailand policy, Thai-listed companies, Thai economic data, government/BOI policy affecting Thai business.
2. GLOBAL DIGEST — news relevant to a globally diversified portfolio: US Fed policy, major global indices, commodities, currencies other than THB, major economies (US/EU/China/etc.), global macro events. Do not repeat Thailand-specific items here.

If an article doesn't clearly belong to either category, drop it. If a category genuinely has no relevant news today, say so in one line instead of padding with unrelated items.

Writing principles for both digests:
- Only include news that "affects investment decisions" — drop noise.
- Group related news together instead of listing items one by one.
- Each bullet is at most 1 line and leads with the "impact", not the headline.
- Include numbers/percentages/direction (▲▼) whenever the data is available.
- Be concise and to the point — no filler words.
- Never recommend buying/selling — analyze facts only."""

PROMPT_TEMPLATE = """Classify and summarize the investment news for {date} from the following data:

{news_block}

Return both digests as JSON matching the response schema. Each digest (max 900 characters) must follow this format:

🌅 FinFin [Thailand/Global] Digest — {date}

📌 Portfolio-impacting headlines:
- ...

📈 Market signals:
- ...

⚠️ Risks to watch:
- ...

💡 Overview:
..."""


class DigestOutput(BaseModel):
    thailand: str
    global_markets: str


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
) -> Dict[str, str]:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    news_block = _build_news_block(articles)

    # ──────────────────────────────────────────────────────────────────────────
    # Generation config: thinking_budget ให้โมเดลคิดก่อนตอบ
    # temperature ต่ำ → output สม่ำเสมอ ไม่เพ้อ เหมาะกับงานข่าว
    # response_schema บังคับให้โมเดลแยก Thailand กับ Global ออกจากกันชัดเจน
    # ──────────────────────────────────────────────────────────────────────────
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        thinking_config=types.ThinkingConfig(thinking_budget=2048),
        temperature=0.3,
        max_output_tokens=4096,
        response_mime_type="application/json",
        response_schema=DigestOutput,
    )

    digest = {"thailand": "", "global": ""}
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
            parsed = response.parsed or DigestOutput.model_validate_json(response.text)
            thailand = (parsed.thailand or "").strip()
            global_markets = (parsed.global_markets or "").strip()

            # เกณฑ์ผ่าน: รวมกันยาวพอ (ยอมให้ฝั่งใดฝั่งหนึ่งว่างได้ถ้าวันนั้นไม่มีข่าว)
            if len(thailand) + len(global_markets) >= 100:
                return {"thailand": thailand, "global": global_markets}

            digest = {"thailand": thailand, "global": global_markets}
            print(
                f"[summarizer] Response too short or incomplete "
                f"(TH {len(thailand)} chars, Global {len(global_markets)} chars), "
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

    return digest  # best effort
