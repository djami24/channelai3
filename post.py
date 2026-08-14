import json
import os
import html

import requests

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]  # masalan: @mening_kanalim yoki -1001234567890
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LESSONS_PATH = os.path.join(BASE_DIR, "data", "lessons.json")
STATE_PATH = os.path.join(BASE_DIR, "data", "state.json")

FOOTER = "📤 Ulashing: @djami_teacher"

# Faqat AI ishlamay qolgan holatlar uchun zaxira (fallback) formatlash —
# hech qanday tarmoq xatosida ham post yuborilmay qolmasligi uchun.
EMOJI_REPLACEMENTS = [
    ("Meaning:", "💡 Meaning:"),
    ("Example:", "📝 Example:"),
    ("Structure:", "🧩 Structure:"),
    ("Speaking Part", "🗣 Speaking Part"),
    ("A short real-life story", "📖 A short real-life story"),
    ("Short real-life story", "📖 Short real-life story"),
    ("#Exercise:", "✍️ #Exercise:"),
]


def load_lessons():
    with open(LESSONS_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"next_index": 0}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _strip_dashes(text: str) -> str:
    """Uzun tire (em dash, —) va ikkita defis (--) belgilarini matndan olib
    tashlaydi. Bo'sh joyga almashtiriladi (so'zlar bir-biriga yopishib
    qolmasligi uchun), so'ng har bir qatordagi ortiqcha bo'shliqlar va
    qator boshidagi/oxiridagi bo'shliqlar tozalanadi."""
    text = text.replace("—", " ").replace("--", " ")
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return "\n".join(lines)


def _fallback_message(lesson: dict) -> str:
    def add_emojis(text: str) -> str:
        for phrase, replacement in EMOJI_REPLACEMENTS:
            text = text.replace(phrase, replacement)
        return text

    header = html.escape(lesson["header"])
    meaning = add_emojis(_strip_dashes(html.escape(lesson["meaning"]).strip()))
    content = add_emojis(_strip_dashes(html.escape(lesson["content"]).strip()))

    parts = [f"📘 <b>{header}</b>"]
    if meaning:
        parts.append(meaning)
    parts.append(content)
    parts.append(FOOTER)
    return "\n\n".join(parts)


def build_message_with_ai(lesson: dict) -> str:
    """AI yordamida dars matnini Telegram uchun chiroyli, tartibli va
    o'qishga qulay qilib qayta formatlaydi. Asl ingliz va o'zbek matn
    mazmuni o'zgartirilmaydi — faqat joylashuvi, sarlavhalari va
    emojilari yaxshilanadi."""

    raw = json.dumps(
        {
            "lesson_number": lesson["n"],
            "header": lesson["header"],
            "meaning": lesson["meaning"],
            "content": lesson["content"],
        },
        ensure_ascii=False,
    )

    prompt = f"""Quyida IELTS Speaking uchun C1 darajali ingliz tili darsining xomaki matni JSON
formatida berilgan. Sen bu matnni Telegram kanal posti uchun CHIROYLI, TARTIBLI va
O'QISHGA QULAY qilib qayta formatlashing kerak.

QOIDALAR (juda muhim):
1. Asl mazmunni (ingliz gaplar, o'zbek tarjimalar, misollar, savol-javoblar, hikoya,
   mashqlar) TO'LIQ saqlab qol — hech narsani qisqartirma, o'zgartirma yoki o'chirma.
2. Faqat Telegram HTML teglaridan foydalan: <b>qalin</b>, <i>kursiv</i> — boshqa teglar
   ishlamaydi (masalan <ul>, <table>, markdown ** ishlatma).
3. Har bir bo'limga (Meaning, Example, Speaking Part, hikoya, Exercise) mos va chiroyli
   emoji qo'sh, bo'limlar orasida bo'sh qator qoldirib, ko'zga yoqimli tarzda joylashtir.
4. Xomaki matnda gap boshida uchraydigan uzun tire ("—") belgilarini BUTUNLAY olib
   tashla — na sarlavhada, na matn ichida, hech qayerda uzun tire ishlatma. Masalan
   "— Honestly, I..." o'rniga shunchaki "Honestly, I..." deb yoz.
5. Eng tepada dars raqami YOZILMASIN ("Dars 1", "Dars 2" kabi hech narsa yo'q) —
   faqat mavzu nomi bilan boshlansin: "📘 <b><mavzu nomi></b>"
6. Matn oxirida ALBATTA aynan shu qatorni qo'sh (o'zgartirmasdan): "{FOOTER}"
7. Faqat tayyor Telegram post matnini qaytar — boshqa hech qanday izoh, preambula yoki
   qo'shtirnoq ishlatma.

Xomaki matn (JSON):
{raw}"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    text = data["content"][0]["text"].strip()

    # Footer har doim borligiga ishonch hosil qilamiz
    if FOOTER not in text:
        text = text.rstrip() + f"\n\n{FOOTER}"
    return text


def send_to_telegram(text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    if not resp.ok:
        print("Telegram javobi:", resp.status_code, resp.text)
    resp.raise_for_status()


def main():
    lessons = load_lessons()
    state = load_state()

    index = state.get("next_index", 0) % len(lessons)
    lesson = lessons[index]

    try:
        message = build_message_with_ai(lesson)
    except Exception as e:  # noqa: BLE001
        print("AI formatlashda xatolik, zaxira formatga o'tildi:", e)
        message = _fallback_message(lesson)

    send_to_telegram(message)
    print(f"Dars {lesson['n']} yuborildi ({index + 1}/{len(lessons)}).")

    state["next_index"] = (index + 1) % len(lessons)
    save_state(state)


if __name__ == "__main__":
    main()
