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
[Subscriber Sync] ── subscribers.py
  ├─ poll Telegram getUpdates() หา chat ที่เคยทักบอท
  ├─ [decision] chat ใหม่ → เพิ่มเข้า subscribers.json อัตโนมัติ
  └─ ถ้าไม่มี subscriber เลย → หยุด (ไม่มีคนรับข่าว)
  │
  ▼
[Fetcher Agent] ── fetcher.py
  ├─ ดึงข่าวจาก 5 primary RSS feeds
  ├─ [decision] ถ้าได้ข่าวน้อยกว่า 5 → ลอง 2 fallback feeds
  └─ ถ้ายังได้ 0 → ส่ง warning แล้วหยุด
  │
  ▼
[Summarizer Agent] ── summarizer.py
  ├─ คิดก่อนตอบด้วย thinking_budget=2048
  ├─ ส่งข่าวให้ Gemini 2.5-flash วิเคราะห์เป็นภาษาอังกฤษ
  ├─ [decision] ถ้าสรุปสั้นกว่า 100 ตัวอักษร หรือไม่มี 📌 → retry
  └─ retry ได้สูงสุด 2 ครั้ง (server error: backoff 10s/20s/30s)
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

### 0. Subscriber Sync (`subscribers.py`)
| | |
|---|---|
| **Role** | ดูว่าใครทักบอทมาบ้าง แล้วเพิ่มเป็นผู้รับข่าวอัตโนมัติ |
| **Input** | Telegram `getUpdates` (offset จาก `last_update_id` เดิม) + `TELEGRAM_CHAT_ID` (owner) |
| **Output** | `List[str]` — chat_ids ทั้งหมดที่จะส่งข่าวให้ |
| **Decision** | chat_id ใหม่ที่ยังไม่มีใน `subscribers.json` → เพิ่มเข้าไป |
| **Storage** | `subscribers.json` — commit กลับเข้า repo ทุกครั้งที่รันผ่าน GitHub Actions (`Persist subscriber list` step) |

### 1. Fetcher Agent (`fetcher.py`)
| | |
|---|---|
| **Role** | ดึงข่าวการลงทุนจาก RSS feeds |
| **Input** | min_articles=5, max_per_feed=5, hours_back=18 |
| **Output** | `List[Dict]` — list of articles |
| **Decision** | ถ้า articles < min_articles → ลอง FALLBACK_FEEDS |
| **Primary Sources** | Reuters, Yahoo Finance, CNBC, Bangkok Post, Investing.com |
| **Fallback Sources** | MarketWatch, Seeking Alpha |

### 2. Summarizer Agent (`summarizer.py`)
| | |
|---|---|
| **Role** | วิเคราะห์และสรุปข่าวเป็นภาษาอังกฤษด้วย Gemini |
| **Input** | `List[Dict]` articles, `str` digest_date |
| **Output** | `str` — English-language digest พร้อมวันที่ |
| **Model** | gemini-2.5-flash |
| **System Instruction** | แยก "บทบาทนักวิเคราะห์" ออกจาก prompt หลัก |
| **Thinking Budget** | 2048 tokens — โมเดลคิดก่อนตอบ |
| **Temperature** | 0.3 — output สม่ำเสมอ เหมาะกับงานข่าว |
| **Max Output Tokens** | 4096 |
| **Decision (quality)** | ถ้า response < 100 chars หรือไม่มี `📌` → retry |
| **Decision (server error)** | 503 ServerError → backoff 10s/20s/30s แล้ว retry |
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
GEMINI_API_KEY=          # Google AI Studio API key (free tier — project ต้องไม่มี billing)
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

**Cronjob (ทุกเช้า 8:00 น.):**
```bash
0 8 * * * /path/to/finfin/venv/bin/python /path/to/finfin/main.py >> /path/to/finfin/logs/finfin.log 2>&1
```

**GitHub Actions (อัตโนมัติ 08:00 Bangkok / 01:00 UTC):**
```bash
gh workflow run "FinFin Morning Digest" --repo bestwwr/FinFIn
```

---

## ขั้นตอนถัดไป (Level 2)
- เพิ่ม **Tool-Use**: ให้ Gemini เรียก `get_stock_price()` และ `get_exchange_rate()` เองได้
- เพิ่ม **Memory**: จำข่าวเมื่อวานเพื่อ track trend
- เพิ่ม **Social Sources**: Reddit (r/investing, r/stocks) และ YouTube RSS
