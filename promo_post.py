import os

import requests

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]

# Reklama matni — o'zgartirmoqchi bo'lsangiz shu joyni tahrirlang.
PROMO_TEXT = """📢 <b>Ingliz tilini bilasizmi?</b>

📚 @djami_teacher kanalida har kuni foydali ingliz tili darslari, foydali iboralar va grammatika tushuntirib beriladi.

🤝 Do'stlaringizni ham taklif qiling, havolani ulashing.
👉 @djami_teacher"""


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
    send_to_telegram(PROMO_TEXT)
    print("Reklama posti yuborildi.")


if __name__ == "__main__":
    main()
