import json
import os
import html
import re
import time
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]  # masalan: @mening_kanalim yoki -1001234567890
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
# Google model nomlarini tez-tez yangilab/eskirtirib turadi, shu sabab bir nechta
# nomni ketma-ket sinab ko'ramiz — birinchisi 404 bersa, keyingisiga o'tamiz.
GEMINI_MODEL_CANDIDATES = [
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.0-flash",
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LESSONS_PATH = os.path.join(BASE_DIR, "data", "lessons.json")
STATE_PATH = os.path.join(BASE_DIR, "data", "state.json")

FOOTER = "📤 Ulashing: @djami_teacher"

# Mavzu rasmi uchun shrift fayllari — Ubuntu GitHub Actions runnerlarida
# odatda shu yo'llarda mavjud bo'ladi (fonts-dejavu-core paketi).
_BOLD_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
_ITALIC_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
]


def _load_font(paths, size):
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def create_topic_image(title: str, translation: str) -> bytes:
    """Mavzu nomi va uning o'zbekcha tarjimasi tushirilgan chiroyli rasm
    (PNG) yaratadi va uni bayt ko'rinishida qaytaradi."""

    width, height = 1080, 720
    top_color = (24, 49, 84)
    bottom_color = (54, 103, 158)

    img = Image.new("RGB", (width, height), color=top_color)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / height
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    title_font = _load_font(_BOLD_FONT_PATHS, 64)
    subtitle_font = _load_font(_ITALIC_FONT_PATHS, 40)
    footer_font = _load_font(_ITALIC_FONT_PATHS, 26)

    max_text_width = width - 160

    title_lines = _wrap_text(draw, title.upper(), title_font, max_text_width)
    subtitle_lines = _wrap_text(draw, f"({translation})", subtitle_font, max_text_width)

    line_spacing = 14
    title_line_height = title_font.size + line_spacing
    subtitle_line_height = subtitle_font.size + line_spacing
    gap_between = 30

    total_height = (
        len(title_lines) * title_line_height
        + gap_between
        + len(subtitle_lines) * subtitle_line_height
    )
    y = (height - total_height) // 2

    for line in title_lines:
        w = draw.textlength(line, font=title_font)
        draw.text(((width - w) / 2, y), line, font=title_font, fill="white")
        y += title_line_height

    y += gap_between

    for line in subtitle_lines:
        w = draw.textlength(line, font=subtitle_font)
        draw.text(((width - w) / 2, y), line, font=subtitle_font, fill=(210, 225, 245))
        y += subtitle_line_height

    footer_text = "@djami_teacher"
    fw = draw.textlength(footer_text, font=footer_font)
    draw.text((width - fw - 30, height - footer_font.size - 24), footer_text, font=footer_font, fill=(180, 195, 220))

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def split_title_block(text: str):
    """AI formatlagan matnning boshidagi '📘 <b>Sarlavha</b>' va
    '<i>(tarjima)</i>' qatorlarini ajratib oladi, qolgan matnni (Daraja
    va undan keyingisi) alohida qaytaradi. Format mos kelmasa (None, None, text)
    qaytaradi."""
    lines = text.split("\n")
    if not lines:
        return None, None, text

    header_match = re.match(r"^📘\s*<b>(.*?)</b>\s*$", lines[0].strip())
    if not header_match:
        return None, None, text

    if len(lines) < 2:
        return None, None, text

    translation_match = re.match(r"^<i>\(?(.*?)\)?</i>\s*$", lines[1].strip())
    if not translation_match:
        return None, None, text

    header = html.unescape(header_match.group(1)).strip()
    translation = html.unescape(translation_match.group(1)).strip()
    rest = "\n".join(lines[2:]).lstrip("\n")
    return header, translation, rest

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

    last_error = None
    for model_name in GEMINI_MODEL_CANDIDATES:
        # Har bir model uchun 503/429 (vaqtinchalik ortiqcha yuklanish/limit)
        # holatlarida qisqa kutib, 3 martagacha qayta urinib ko'ramiz.
        for attempt in range(3):
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
                headers={
                    "x-goog-api-key": GEMINI_API_KEY,
                    "content-type": "application/json",
                },
                json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 2000},
                },
                timeout=60,
            )
            if response.status_code in (503, 429):
                wait = 5 * (attempt + 1)
                print(
                    f"Model '{model_name}' band/limitga tegdi ({response.status_code}), "
                    f"{wait}s kutib qayta urinamiz... ({attempt + 1}/3)"
                )
                last_error = RuntimeError(f"Model '{model_name}' {response.status_code} qaytardi")
                time.sleep(wait)
                continue
            break  # 503/429 emas — natija bilan davom etamiz (muvaffaqiyat yoki boshqa xato)
        else:
            # 3 urinish ham 503/429 bilan tugadi — keyingi modelga o'tamiz
            continue

        if response.status_code == 404:
            # Bu model nomi Google tomonidan endi qo'llab-quvvatlanmayapti —
            # keyingi nomni sinab ko'ramiz.
            print(f"Model '{model_name}' topilmadi (404), keyingisi sinaladi...")
            last_error = RuntimeError(f"Model '{model_name}' topilmadi (404)")
            continue

        if not response.ok:
            print("Gemini javobi (xato):", response.status_code, response.text)
        response.raise_for_status()
        data = response.json()

        try:
            candidate = data["candidates"][0]
        except (KeyError, IndexError) as exc:
            # Odatda xavfsizlik filtri javobni bloklaganda "candidates" bo'lmaydi
            # yoki bo'sh bo'ladi — to'liq javobni logga chiqaramiz.
            print("Gemini javobida 'candidates' topilmadi:", json.dumps(data, ensure_ascii=False))
            raise RuntimeError(f"Gemini candidates topilmadi: {data.get('promptFeedback', data)}") from exc

        print(f"Model '{model_name}' muvaffaqiyatli ishlatildi.")
        text = candidate["content"]["parts"][0]["text"].strip()

        # Footer har doim borligiga ishonch hosil qilamiz
        if FOOTER not in text:
            text = text.rstrip() + f"\n\n{FOOTER}"
        return text

    # Barcha model nomlari 404 bergan bo'lsa
    raise last_error or RuntimeError("Hech qanday Gemini modeli ishlamadi")


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


def send_photo_to_telegram(image_bytes: bytes) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    resp = requests.post(
        url,
        data={"chat_id": TELEGRAM_CHANNEL_ID},
        files={"photo": ("mavzu.png", image_bytes, "image/png")},
        timeout=30,
    )
    if not resp.ok:
        print("Telegram (rasm) javobi:", resp.status_code, resp.text)
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

    header, translation, rest_text = split_title_block(message)

    sent_with_image = False
    if header and translation:
        try:
            image_bytes = create_topic_image(header, translation)
            send_photo_to_telegram(image_bytes)
            send_to_telegram(rest_text)
            sent_with_image = True
        except Exception as e:  # noqa: BLE001
            print("Rasm yaratish/yuborishda xatolik, oddiy matn yuborildi:", e)

    if not sent_with_image:
        send_to_telegram(message)

    print(f"Dars {lesson['n']} yuborildi ({index + 1}/{len(lessons)}).")

    state["next_index"] = (index + 1) % len(lessons)
    save_state(state)


if __name__ == "__main__":
    main()
