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


def _strip_exercise_section(text: str) -> str:
    """'#Exercise:' (yoki 'Exercise:') dan boshlab matn oxirigacha bo'lgan
    tarjima-mashq qismini olib tashlaydi (AI ishlamay qolgan holatlar uchun
    zaxira tozalash)."""
    for marker in ("#Exercise:", "Exercise:"):
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx].rstrip()
    return text


def _fallback_message(lesson: dict) -> str:
    def add_emojis(text: str) -> str:
        for phrase, replacement in EMOJI_REPLACEMENTS:
            text = text.replace(phrase, replacement)
        return text

    header = html.escape(lesson["header"]).upper()
    meaning = add_emojis(_strip_dashes(html.escape(lesson["meaning"]).strip()))
    content = _strip_exercise_section(lesson["content"])
    content = add_emojis(_strip_dashes(html.escape(content).strip()))

    parts = [f"📘 <b>{header}</b>"]
    if meaning:
        parts.append(meaning)
    parts.append(content)
    parts.append(FOOTER)
    return "\n\n".join(parts)


def build_message_with_ai(lesson: dict) -> str:
    """AI yordamida dars matnini Telegram uchun chiroyli, tartibli va
    o'qishga qulay qilib qayta formatlaydi. Speaking qismlari va hikoya
    saqlanadi; tarjima mashqlari olib tashlanadi; mavzu tarjimasi, daraja
    va qisqa grammatik tushuntirish qo'shiladi."""

    raw = json.dumps(
        {
            "lesson_number": lesson["n"],
            "header": lesson["header"],
            "meaning": lesson["meaning"],
            "content": lesson["content"],
        },
        ensure_ascii=False,
    )

    prompt = f"""Quyida IELTS Speaking uchun ingliz tili darsining xomaki matni JSON formatida
berilgan. Sen bu matnni Telegram kanal posti uchun CHIROYLI, TARTIBLI va O'QISHGA QULAY
qilib qayta formatlashing kerak, quyidagi ANIQ TUZILMA bo'yicha.

CHIQISH TUZILMASI (shu tartibda, boshqa hech narsa qo'shmasdan):

1-qator: "📘 <b><MAVZU NOMI BUTUNLAY KATTA HARFLARDA></b>"
2-qator: "<i>(<mavzu nomining o'zbekcha tarjimasi>)</i>"
3-qator: "🔵 Daraja: <CEFR darajasi, masalan B1, B2, C1 yoki C2>" — matn mazmuni,
   so'z boyligi va grammatik murakkabligiga qarab darajani o'zing aniqla; agar aniq
   bo'lmasa, C1 deb qo'y.

Bo'sh qator, so'ng:

"🧩 <b>Bu tuzilma nima uchun ishlatiladi?</b>" sarlavhasi ostida, mavzuning grammatik
tuzilmasi (masalan "not because... but because...") qachon va nima maqsadda
ishlatilishini 2-4 gapda, oddiy va tushunarli o'zbek tilida tushuntir.

Bo'sh qator, so'ng:

Xomaki matndagi "Speaking Part" bo'limi(lari) — har bir savol-javobni saqlab qol,
mos emoji bilan (masalan 🗣). Har bir savolni <b>qalin</b> qilib ber.

Agar xomaki matnda "Structure" yoki "Meaning" kabi tushuntirish qismlari bo'lsa,
ularni ham mos emoji bilan saqlab qol (mazmunini o'zgartirma).

Agar xomaki matnda hikoya ("short real-life story" yoki shunga o'xshash) bo'lsa,
uni 📖 emoji bilan, "Short real-life story" kabi inglizcha sarlavha bilan saqlab qol.

MUHIM CHIQARIB TASHLASH QOIDASI:
- Tarjima mashqlari, "#Exercise:", "Quyidagi gaplarni tarjima qiling" kabi
  topshiriqlar, raqamlangan tarjima jumlalari va "_________ not because..." kabi
  bo'sh joy to'ldirish mashqlari BUTUNLAY OLIB TASHLANSIN — ular chiqishga umuman
  kiritilmasin.
- Hech qayerda "Dars 1", "Dars 2", "Exercise", "Mashq" kabi so'zlar ishlatilmasin.

BOSHQA QOIDALAR (juda muhim):
1. Speaking Part va hikoya matnini TO'LIQ saqlab qol — ingliz gaplarni qisqartirma,
   o'zgartirma yoki o'chirma (faqat yuqoridagi chiqarib tashlash qoidasidagi qismlar
   olib tashlanadi).
2. Faqat Telegram HTML teglaridan foydalan: <b>qalin</b>, <i>kursiv</i> — boshqa teglar
   ishlamaydi (masalan <ul>, <table>, markdown ** ishlatma).
3. Bo'limlar orasida bo'sh qator qoldirib, ko'zga yoqimli tarzda joylashtir.
4. Matnda uchraydigan uzun tire ("—") belgilarini BUTUNLAY olib tashla — na
   sarlavhada, na matn ichida, hech qayerda uzun tire ishlatma. Masalan
   "— Honestly, I..." o'rniga shunchaki "Honestly, I..." deb yoz.
5. Matn oxirida ALBATTA aynan shu qatorni qo'sh (o'zgartirmasdan): "{FOOTER}"
6. Faqat tayyor Telegram post matnini qaytar — boshqa hech qanday izoh, preambula yoki
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
