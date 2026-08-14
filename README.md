# IELTS C1 Lesson Poster

Bu loyiha sizning 35 ta C1 darajali speaking darslaringizni (`data/lessons.json`)
Telegram kanalingizga **kuniga 4 marta, faqat kunduzi** (09:00, 12:00, 15:00, 18:00,
Toshkent vaqti) avtomatik, tartib bilan (1-darsdan 35-darsgacha, so'ng yana boshidan)
joylab boradi. Ishlash uchun GitHub Actions'dan foydalanadi — kompyuteringiz doim
yoqilgan bo'lishi shart emas.

## 1. Telegram bot yaratish

1. Telegram'da **@BotFather** ga yozing.
2. `/newbot` buyrug'ini yuboring, botga nom va username bering.
3. Sizga beriladigan **token**ni saqlab qo'ying (masalan `123456:ABC-DEF...`).
4. Botni o'z kanalingizga **administrator** qilib qo'shing (postlarni yuborish huquqi bilan).

## 2. Kanal ID'sini olish

- Agar kanalingiz ochiq (public) bo'lsa va username'i bo'lsa — shunchaki `@kanal_username`
  ishlatavering.
- Agar yopiq (private) kanal bo'lsa, kanal ID'sini olish uchun kanalga bitta xabar
  joylang, so'ng shu manzilga o'ting:
  `https://api.telegram.org/bot<TOKEN>/getUpdates`
  va javobdagi `"chat":{"id": -100...}` qiymatini oling.

## 3. GitHub'ga yuklash

1. GitHub'da yangi **repository** yarating (masalan `ielts-c1-poster`).
2. Shu papkadagi barcha fayl va papkalarni (`post.py`, `requirements.txt`, `data/`,
   `.github/workflows/post.yml`) o'sha repo'ga yuklang (push qiling).

## 4. Repo sozlamalarida yozish huquqini yoqish

**Settings → Actions → General → Workflow permissions** bo'limiga o'ting va
**"Read and write permissions"** ni tanlang, so'ng saqlang. (Skript har safar
qaysi darsda to'xtaganini `data/state.json` fayliga yozib, uni repo'ga qaytarib
push qiladi — shu uchun yozish huquqi kerak.)

## 5. Maxfiy kalitlarni (Secrets) qo'shish

Repo sahifasida: **Settings → Secrets and variables → Actions → New repository secret**
orqali quyidagi 2 ta secret'ni qo'shing:

| Nomi | Qiymati |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather'dan olgan token |
| `TELEGRAM_CHANNEL_ID` | Kanal username (`@kanal`) yoki ID (`-100...`) |

## 6. Tekshirish

**Actions** bo'limiga o'ting → **IELTS C1 Lesson Poster** workflow'ni tanlang →
**Run workflow** tugmasini bosib, qo'lda ishga tushiring. Agar hammasi to'g'ri
sozlangan bo'lsa, bir necha soniyada kanalingizga 1-dars tushadi, va
`data/state.json` fayli avtomatik `next_index: 1` ga yangilanadi.

Shundan keyin workflow avtomatik ravishda kuniga 4 marta (faqat kunduzi) o'zi
ishlab, darslarni ketma-ket joylab boradi — hech narsa qilish shart emas.
35-darsdan keyin yana 1-darsdan boshlab qaytadi.

## Sozlashlar

- **Vaqtlarni o'zgartirish**: `.github/workflows/post.yml` faylidagi `cron`
  qatorlarini tahrirlang (vaqtlar UTC bo'yicha; Toshkent = UTC+5).
- **Darslar tartibini qaytadan boshlash**: `data/state.json` faylidagi
  `next_index` qiymatini `0` ga o'zgartiring.
- **Dars matnini tahrirlash**: `data/lessons.json` faylidagi tegishli
  `header` / `meaning` / `content` maydonlarini o'zgartiring.
