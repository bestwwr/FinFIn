import os
import time
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from typing import List, Dict

# ──────────────────────────────────────────────────────────────────────────────
# System instruction: แยก "บทบาท" ออกจาก "งาน"
# โมเดลให้น้ำหนัก system_instruction มากกว่าข้อความปกติ
# และทำให้ prompt หลักสั้น สะอาด ปรับง่าย
# ──────────────────────────────────────────────────────────────────────────────
SYSTEM_INSTRUCTION = """คุณคือนักวิเคราะห์ข่าวการลงทุนมืออาชีพ เขียนสรุปข่าวเช้าให้นักลงทุนไทยอ่านภายใน 1 นาที

หลักการเขียนที่ต้องทำตามเสมอ:
- คัดเฉพาะข่าวที่ "มีผลต่อการตัดสินใจลงทุน" ทิ้งข่าวที่เป็น noise
- จัดกลุ่มข่าวที่เกี่ยวข้องกันเข้าด้วยกัน อย่าแยกเป็นรายข่าว
- แต่ละ bullet ยาวไม่เกิน 1 บรรทัด ขึ้นต้นด้วย "ผลกระทบ" ไม่ใช่ชื่อข่าว
- ใส่ตัวเลข/เปอร์เซ็นต์/ทิศทาง (▲▼) เมื่อมีข้อมูล
- ภาษากระชับ ตรงประเด็น ไม่ใช้คำฟุ่มเฟือย
- ห้ามแนะนำซื้อ/ขาย แค่วิเคราะห์ข้อเท็จจริง"""

PROMPT_TEMPLATE = """สรุปข่าวการลงทุนประจำ{date} จากข้อมูลต่อไปนี้:

{news_block}

รูปแบบที่ต้องการ (ไม่เกิน 900 ตัวอักษร):

🌅 FinFin Morning Digest — {date}

📌 ประเด็นที่กระทบพอร์ต:
- ...

📈 สัญญาณตลาด:
- ...

⚠️ ความเสี่ยงที่ต้องจับตา:
- ...

💡 ภาพรวม:
..."""


def _build_news_block(articles: List[Dict]) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. [{a['source']}] {a['title']}")
        if a.get("published"):
            lines.append(f"   เวลา: {a['published']}")
        if a.get("summary"):
            lines.append(f"   เนื้อหา: {a['summary'][:400]}")
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
                date=digest_date or "วันนี้",
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
