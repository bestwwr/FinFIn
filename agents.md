# FinFin Agent Architecture

## Overview
FinFin เป็น Basic Agent ที่ดึงข่าวการลงทุน สรุปด้วย Gemini AI และส่งไปยัง Telegram ทุกเช้า
ต่างจาก pipeline ธรรมดาตรงที่แต่ละขั้นตอนมี **decision logic** และ **retry** เป็นของตัวเอง

---

## Agent Loop

```
START
  │
  ▼
[Fetcher Agent] ── fetcher.py
  ├─ ดึงข่าวจาก 5 primary RSS feeds
  ├─ [decision] ถ้าได้ข่าวน้อยกว่า 5 → ลอง 2 fallback feeds
  └─ ถ้ายังได้ 0 → ส่ง warning แล้วหยุด
  │
  ▼
[Summarizer Agent] ── summarizer.py
  ├─ ส่งข่าวให้ Gemini 2.5-flash วิเคราะห์เป็นภาษาไทย
  ├─ [decision] ถ้าสรุปสั้นกว่า 100 ตัวอักษร → retry ด้วย prompt ใหม่
  └─ retry ได้สูงสุด 2 ครั้ง
  │
  ▼
[Notifier Agent] ── notifier.py
  ├─ ส่งสรุปไปยัง Telegram
  ├─ [decision] ถ้าล้มเหลว → retry พร้อม exponential backoff (1s / 2s / 4s)
  └─ retry ได้สูงสุด 3 ครั้ง
  │
  ▼
END
```

---

## Agents

### 1. Fetcher Agent (`fetcher.py`)
| | |
|---|---|
| **Role** | ดึงข่าวการลงทุนจาก RSS feeds |
| **Input** | min_articles, max_per_feed, hours_back |
| **Output** | `List[Dict]` — list of articles |
| **Decision** | ถ้า articles < min_articles → ลอง FALLBACK_FEEDS |
| **Primary Sources** | Reuters, Yahoo Finance, CNBC, Bangkok Post, Investing.com |
| **Fallback Sources** | MarketWatch, Seeking Alpha |

### 2. Summarizer Agent (`summarizer.py`)
| | |
|---|---|
| **Role** | วิเคราะห์และสรุปข่าวเป็นภาษาไทยด้วย Gemini |
| **Input** | `List[Dict]` articles |
| **Output** | `str` — Thai-language digest |
| **Decision** | ถ้า response < 100 chars → retry ด้วย retry prompt |
| **Model** | gemini-2.5-flash |
| **Max Retries** | 2 |

### 3. Notifier Agent (`notifier.py`)
| | |
|---|---|
| **Role** | ส่งสรุปข่าวไปยัง Telegram |
| **Input** | `str` message |
| **Output** | `bool` success/failure |
| **Decision** | ถ้าส่งไม่สำเร็จ → retry พร้อม exponential backoff |
| **Platform** | Telegram Bot API |
| **Max Retries** | 3 (backoff: 1s / 2s / 4s) |

---

## Environment Variables
```
GEMINI_API_KEY=          # Google AI Studio API key
TELEGRAM_BOT_TOKEN=      # จาก @BotFather
TELEGRAM_CHAT_ID=        # User ID จาก @userinfobot
```

---

## วิธีรัน

**รันด้วยมือ:**
```bash
cd finfin
source venv/bin/activate
python main.py
```

**ตั้ง Cronjob ทุกเช้า 7:00 น.:**
```bash
crontab -e
# เพิ่มบรรทัด:
0 7 * * * cd /path/to/finfin && source venv/bin/activate && python main.py >> logs/finfin.log 2>&1
```

---

## ขั้นตอนถัดไป (Level 2)
- เพิ่ม **Tool-Use**: ให้ Gemini เรียก `get_stock_price()` และ `get_exchange_rate()` เองได้
- เพิ่ม **Memory**: จำข่าวเมื่อวานเพื่อ track trend
