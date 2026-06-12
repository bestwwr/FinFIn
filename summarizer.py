import os
from google import genai
from typing import List, Dict

PROMPT_TEMPLATE = """คุณคือ Financial News Analyst ผู้เชี่ยวชาญด้านการลงทุน

วิเคราะห์และสรุปข่าวการลงทุนต่อไปนี้เป็นภาษาไทย สำหรับนักลงทุนที่ต้องการอ่านตอนเช้า:

{news_block}

สรุปในรูปแบบนี้ (กระชับ ไม่เกิน 900 ตัวอักษร):

🌅 FinFin Morning Digest

📌 ประเด็นสำคัญ:
- ...

📈 สัญญาณตลาด:
- ...

⚠️ ความเสี่ยงที่ควรติดตาม:
- ...

💡 สรุปภาพรวม:
..."""

RETRY_PROMPT_TEMPLATE = """สรุปข่าวการเงินต่อไปนี้เป็นภาษาไทย ให้ครบถ้วนและมีรายละเอียดมากขึ้น:

{news_block}

ต้องมีอย่างน้อย 3 ประเด็นสำคัญและการวิเคราะห์แนวโน้มตลาด"""


def _build_news_block(articles: List[Dict]) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. [{a['source']}] {a['title']}")
        if a["summary"]:
            lines.append(f"   {a['summary']}")
    return "\n".join(lines)


def summarize_news(articles: List[Dict], max_retries: int = 2) -> str:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    news_block = _build_news_block(articles)

    for attempt in range(max_retries + 1):
        # ใช้ retry prompt ถ้าเป็นการลองซ้ำ
        template = RETRY_PROMPT_TEMPLATE if attempt > 0 else PROMPT_TEMPLATE
        prompt = template.format(news_block=news_block)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = response.text or ""

        # Decision: ถ้าสรุปยาวพอ → ใช้ได้
        if len(text) >= 100:
            return text

        print(f"[summarizer] Response too short ({len(text)} chars), retrying ({attempt + 1}/{max_retries})...")

    return text  # return best effort
