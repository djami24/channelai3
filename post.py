import json
import os
import html

import requests

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]  # masalan: @mening_kanalim yoki -1001234567890

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LESSONS_PATH = os.path.join(BASE_DIR, "data", "lessons.json")
STATE_PATH = os.path.join(BASE_DIR, "data", "state.json")


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


# Ma'lum bo'limlarga mos emoji qo'shish uchun (tartib muhim: uzunroq
# iboralar avval tekshiriladi, aks holda "Speaking Part" o'rniga oddiy
# "Speaking" ga ham moslashib qolishi mumkin)
EMOJI_REPLACEMENTS = [
    ("Meaning:", "💡 Meaning:"),
    ("Example:", "📝 Example:"),
    ("Structure:", "🧩 Structure:"),
    ("Speaking Part", "🗣 Speaking Part"),
    ("A short real-life story", "📖 A short real-life story"),
    ("Short real-life story", "📖 Short real-life story"),
    ("#Exercise:", "✍️ #Exercise:"),
]

FOOTER = "📤 Ulashing: @djami_teacher"


def _add_emojis(text: str) -> str:
    for phrase, replacement in EMOJI_REPLACEMENTS:
        text = text.replace(phrase, replacement)
    return text


def build_message(lesson: dict) -> str:
    header = html.escape(lesson["header"])
    meaning = _add_emojis(html.escape(lesson["meaning"]).strip())
    content = _add_emojis(html.escape(lesson["content"]).strip())

    parts = [f"📘 <b>Dars {lesson['n']}: {header}</b>"]
    if meaning:
        parts.append(meaning)
    parts.append(content)
    parts.append(FOOTER)
    return "\n\n".join(parts)


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

    message = build_message(lesson)
    send_to_telegram(message)
    print(f"Dars {lesson['n']} yuborildi ({index + 1}/{len(lessons)}).")

    state["next_index"] = (index + 1) % len(lessons)
    save_state(state)


if __name__ == "__main__":
    main()
