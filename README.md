# 🧭 SIRLI SAFAR — talabalar uchun interaktiv sarguzasht Telegram boti

O‘qituvchi dars davomida foydalanadigan jamoaviy o‘yin: guruhdagi barcha talabalar **bitta jamoa**. Jamoa **1-zinadan 10-zinaga** chiqadi — to‘g‘ri javob **+1 zina**, noto‘g‘ri javob yoki vaqt tugashi **−1 zina**. Yo‘lda hikoya bo‘laklari, topshiriqlar, individual sinovlar va tuzoqlar bor.

**Texnologiyalar (hammasi bepul):** Python 3.12 · aiogram 3 · PostgreSQL (Supabase Free) · Render Free Web Service · Telegram webhook · GitHub.
Pullik API, pullik AI yoki pullik rasm generatori **talab qilinmaydi**.

---

## ⚠️ Avval halol holat (nima sinalgan, nima sinalmagan)

| | Holat |
|---|---|
| O‘yin mantig‘i, admin panel, tuzoq, individual topshiriq, taymer, qayta ishga tushishdan tiklanish | ✅ **67 ta avtomatik test** (haqiqiy PostgreSQL + soxta Telegram sessiyasi) |
| Ilovani bo‘sh bazada ishga tushirish (migratsiya, hikoyalarni yuklash, server, webhook sozlash, to‘g‘ri to‘xtash) | ✅ sinab ko‘rilgan |
| **Haqiqiy Telegram** (sizning BOT_TOKEN’ingiz) va **haqiqiy Supabase/Render** | ❌ **men sinay olmadim** (menda token va akkauntlaringiz yo‘q). Birinchi haqiqiy sinovni siz o‘tkazasiz — pastdagi «Birinchi sinov» bo‘limiga qarang |
| AI orqali rasm yaratish | ❌ botda yo‘q (bepul bo‘lishi uchun). 40 ta tayyor **ingliz tilidagi prompt** bor: `assets/stories/image_prompts.md`. Rasm/GIF’ni admin Telegram orqali biriktiradi. Biriktirilmasa ham o‘yin matn bilan ishlayveradi |

---

## 1. Tezkor o‘rnatish (taxminan 20 daqiqa)

### 1.1. Telegram bot yaratish
1. Telegramda **@BotFather** → `/newbot` → nom va username bering → **token**ni oling (`BOT_TOKEN`).
2. O‘zingizning Telegram ID raqamingizni **@userinfobot** orqali biling (`ADMIN_IDS`). Bir nechta admin bo‘lsa, vergul bilan: `123456789,987654321`.

### 1.2. Admin parol hashi
```bash
pip install -r requirements.txt
python scripts/make_password_hash.py      # parol so‘raydi, ADMIN_PASSWORD_HASH qiymatini chiqaradi
```
Hash `$2b$12$...` ko‘rinishida bo‘ladi. Parolning o‘zi hech qayerda saqlanmaydi.

### 1.3. Supabase (ma’lumotlar bazasi)
1. https://supabase.com → yangi **Free** loyiha yarating, baza parolini eslab qoling.
2. **Project Settings → Database → Connection string → Session pooler** (URI) ni nusxalang. Parol o‘rniga o‘zingizning parolingizni qo‘ying. Bu `DATABASE_URL`.
   - ❗ **Session pooler** (yoki «Shared pooler», port 5432) ni tanlang. Render Free faqat IPv4 qo‘llaydi, Supabase’ning «Direct connection» manzili esa IPv6 bo‘lishi mumkin.
3. Jadvallarni qo‘lda yaratish shart emas: bot birinchi ishga tushganda `migrations/` ni o‘zi qo‘llaydi va 4 ta hikoyani yuklaydi.

### 1.4. GitHub
```bash
git init && git add . && git commit -m "SIRLI SAFAR"
# GitHub’da bo‘sh PRIVATE repo yarating, so‘ng:
git remote add origin https://github.com/<login>/sirli-safar.git
git branch -M main && git push -u origin main
```
`.env` fayli `.gitignore` da — maxfiy qiymatlar GitHub’ga tushmaydi.

### 1.4a. `.env` fayli (lokal ishlatish uchun)
Papkadagi `.env.example` ni `.env` nomi bilan nusxalab, ichiga 6 ta qiymatni yozishingiz mumkin — bot ishga tushganda uni o‘zi o‘qiydi (`python -m app.main`). Parolning o‘zini emas, **hash**ni yozing (1.2). `.env` GitHub’ga tushmaydi. ⚠️ Render `.env` faylini ko‘rmaydi: internetga joylaganda xuddi shu qiymatlarni Render → Environment ga ham kiriting. Lokal webhook ishlashi uchun `WEBHOOK_URL` ochiq https manzil (masalan, ngrok) bo‘lishi kerak, shuning uchun eng oson yo‘l — Render’ga joylab sinash.

### 1.5. Render (hosting)
1. https://render.com → **New → Blueprint** → GitHub repo’ni tanlang (`render.yaml` avtomatik o‘qiladi) **yoki** **New → Web Service** (Runtime: Python, Plan: Free, Build: `pip install -r requirements.txt`, Start: `python -m app.main`, Health Check Path: `/health`).
2. **Environment** bo‘limida 6 ta o‘zgaruvchini kiriting:

| O‘zgaruvchi | Qiymat |
|---|---|
| `BOT_TOKEN` | BotFather tokeni |
| `ADMIN_IDS` | admin Telegram ID(lar)i, vergul bilan |
| `ADMIN_PASSWORD_HASH` | 1.2-qadamdagi bcrypt hash |
| `DATABASE_URL` | Supabase Session pooler manzili |
| `WEBHOOK_URL` | Render manzili, masalan `https://sirli-safar.onrender.com` (oxirida `/` yo‘q) |
| `WEBHOOK_SECRET` | 16–256 belgi, faqat `A-Za-z0-9_-`. Hosil qilish: `python -c "import secrets;print(secrets.token_urlsafe(32))"` |

   Ixtiyoriy: `ADMIN_SESSION_HOURS` (standart 12), `LOG_LEVEL` (INFO).
3. Deploy tugagach loglarda `Webhook o‘rnatildi` yozuvini ko‘rasiz. `https://<manzil>/health` → `{"status":"ok","db":true}`.

> `WEBHOOK_URL` Render manzili ma’lum bo‘lgandan **keyin** kiritiladi: avval xizmatni yarating, manzilni oling, so‘ng o‘zgaruvchini qo‘shib qayta deploy qiling.

### 1.6. Birinchi sinov (siz o‘tkazasiz)
1. Botingizga shaxsiy chatda `/admin` → parol → boshqaruv paneli ochiladi.
2. Bitta sinov guruhi yarating, **botni guruhga qo‘shing** (qo‘shuvchi `ADMIN_IDS` ichida bo‘lishi shart — begona odam qo‘shsa, bot guruhni tark etadi).
3. `/admin` → **🆕 Yangi o‘yin yaratish** → guruh → hikoya → «Ro‘yxat yig‘ishni boshlash».
4. Sinov uchun 2–3 hisobdan guruhdagi **«✅ Ro‘yxatga yozilish»** tugmasini bosing → bot ochilganda **Start**.
5. Admin panelda **▶️ O‘yinni boshlash**.
6. Muammo bo‘lsa Render **Logs** bo‘limiga qarang va menga yuboring (token va parollar jurnalga yozilmaydi).

---

## 2. O‘qituvchi uchun ish tartibi

1. **Dars oldidan:** `/admin` → **🧩 Topshiriqlar** — har bir zina (1–9) uchun kamida 1 ta topshiriq qo‘shing (boshlang‘ich 27 ta demo topshiriq va 3 ta demo tuzoq bor — ularni o‘z fanigingizga almashtiring, ortiqchasini o‘chiring). Hikoya bosqichlariga rasm/GIF biriktirish ixtiyoriy (**📚 Hikoyalar kutubxonasi**).
2. **Talabalar** guruhga kiradi. **Yangi o‘yin** yarating: guruh → hikoya → lobbi xabari guruhga yuboriladi.
3. **Har bir talaba** lobbidagi tugma orqali botga o‘tib **Start** bosadi (Telegram bot guruh a’zolarini avtomatik ko‘ra olmaydi, shuning uchun ro‘yxat shunday yig‘iladi). Botga Start bosmagan talabaga shaxsiy topshiriq yuborib bo‘lmaydi — bu lobbi xabarida yozilgan.
4. **▶️ O‘yinni boshlash** — ro‘yxat muzlaydi. Keyin qo‘shilganlar keyingi o‘yinda qatnashadi.
5. O‘yin davomida: ⏸ pauza / ▶️ davom / 🛑 bekor qilish, 📝 javoblarni tekshirish, 📊 joriy natijalar.
6. 10-zinaga yetilganda g‘alaba xabari, yakuniy sahna, GIF, zinapoya rasmi, davomiylik, to‘g‘ri/noto‘g‘ri javoblar, individual topshiriqlar soni va eng faol talabalar reytingi guruhga **va sizning shaxsiy chatingizga** yuboriladi.

### Topshiriq turlari
| Tur | Qanday ishlaydi |
|---|---|
| **A. Variantli test** | Guruhda A/B/C/D tugmalari. Jamoadan **birinchi bosilgan** javob yakuniy; bot o‘zi tekshiradi |
| **B. Matnli savol** | Guruh topshiriq xabariga **reply** qilib yozadi, **birinchi javob yakuniy**. Javob sizga yuboriladi → ✅ TO‘G‘RI / ❌ NOTO‘G‘RI |
| **C. Individual** | Tasodifiy (adolatli) talabaga shaxsiy chatda; variantli bo‘lsa bot tekshiradi, matnli bo‘lsa siz baholaysiz. Vaqtida javob bermasa — noto‘g‘ri |
| **D. Ijodiy** | Matnli savol kabi, siz baholaysiz |
| **E. Tuzoq** | Hikoya bosqichida (standart: 5-zina) tuzoq hodisasi. Siz topshiriqni **o‘zingiz yozasiz yoki kutubxonadan tanlaysiz**, guruh javob beradi/bajaradi, siz baholaysiz. To‘g‘ri → o‘tadi (**bonus yo‘q**, zina o‘zgarmaydi); noto‘g‘ri yoki vaqt tugasa → bir zina pastga |

Har bir topshiriq uchun vaqt alohida belgilanadi (10–3600 soniya). Vaqt tugasa — noto‘g‘ri hisoblanadi va guruhga xabar boradi; 10 soniya qolganda ogohlantirish yuboriladi.

---

## 3. Render Free va Supabase Free cheklovlari (muhim!)

**Render Free uxlab qoladi.** 15 daqiqa so‘rov bo‘lmasa xizmat uxlaydi; keyingi so‘rovda uyg‘onishi ~30–60 soniya oladi.
- Bot webhook orqali ishlaydi: uxlab turganda kelgan Telegram xabarlari qayta yuboriladi va uyg‘ongach qayta ishlanadi.
- O‘yin holati, topshiriqlar, vaqt chegaralari (**UTC deadline**) bazada saqlanadi. Uxlab turib uyg‘ongach muddati o‘tgan topshiriqlar zudlik bilan hal qilinadi, ochiq topshiriqlar saqlanib qoladi, to‘xtab qolgan bosqich davom etadi.
- **Dars paytida uxlab qolmasligi uchun:** (1) bot faol o‘yin bor paytda o‘z `/health` manziliga har ~9 daqiqada so‘rov yuboradi (bu yordam berishi mumkin, lekin kafolat yo‘q); (2) ishonchliroq: bepul **UptimeRobot** (yoki cron-job.org) bilan `https://<manzil>/health` ni har 5 daqiqada ping qiling — dars vaqtida yoqib qo‘ying.
- Bepul tarifda oyiga 750 soat: bitta xizmat uchun yetarli.
- Render Free **diskiga hech narsa saqlanmaydi** — hamma narsa bazada.

**Supabase Free loyihasi** 1 hafta faolsiz turgach **pauza**ga tushishi mumkin. Pauza bo‘lsa Supabase panelida «Restore project» tugmasini bosing (ma’lumotlar saqlanadi). Dars bo‘lmaydigan haftalarda ham `/health` ni ping qilish bazaga so‘rov yuboradi, lekin Supabase buni «faollik» deb hisoblashiga kafolat yo‘q — shuning uchun zaxira oling.

### Zaxira nusxa (backup)
- **Botdan:** `/admin` → ⚙️ Sozlamalar → **💾 Zaxira nusxasi (JSON)** — hikoyalar (tahrirlaringiz bilan), topshiriqlar, tuzoqlar, guruhlar, o‘yinlar va natijalar bitta JSON fayl sifatida yuboriladi.
- **To‘liq PostgreSQL dump** (kompyuteringizdan, `pg_dump` o‘rnatilgan bo‘lsa):
  ```bash
  export DATABASE_URL='postgresql://...'
  python scripts/backup.py dump     # backups/*.sql
  python scripts/backup.py json     # backups/*.json
  ```
- Tiklash: yangi Supabase loyiha yarating → `psql "$DATABASE_URL" -f backups/<fayl>.sql` → `DATABASE_URL` ni yangilang.
- Supabase panelida ham (Database → Backups) o‘z zaxiralari bor; Free tarifda ularning mavjudligi/saqlanish muddati cheklangan bo‘lishi mumkin — shu sababli o‘zingiz ham oling.

---

## 4. Xavfsizlik
- Token, parol hashi, baza manzili, webhook maxfiy so‘zi — faqat **muhit o‘zgaruvchilari**da. Jurnalga token va baza paroli yozilmaydi (filtr bor).
- Admin: faqat `ADMIN_IDS` + parol (bcrypt hash). 5 ta noto‘g‘ri urinishdan keyin 15 daqiqaga bloklanadi; parol xabari chatdan o‘chiriladi; sessiya 12 soat.
- Webhook: Telegram `X-Telegram-Bot-Api-Secret-Token` sarlavhasi tekshiriladi, noto‘g‘ri bo‘lsa 401.
- Guruh a’zolari admin tugmalaridan foydalana olmaydi. Bot faqat admin qo‘shgan guruhda qoladi.
- Bir vaqtda kelgan javoblar: o‘yin qatori `FOR UPDATE` bilan qulflanadi; har bir topshiriqqa **bitta** javob (`answers.game_task_id UNIQUE`); javob va vaqt tugashi bir vaqtda kelsa, bazadagi `deadline_at` bo‘yicha yagona natija.

---

## 5. Loyiha tuzilmasi
```
SIRLI-SAFAR/
├── app/
│   ├── main.py            # aiohttp + aiogram webhook, ishga tushirish
│   ├── config.py          # muhit o‘zgaruvchilari
│   ├── database.py        # asyncpg, migratsiyalar, o‘yin qulflari
│   ├── deps.py            # servislar konteyneri
│   ├── handlers/          # admin.py, tasks.py, players.py, game.py, answers.py, states.py
│   ├── services/          # game_service, game_flow, timer_service, story_service, task_service,
│   │                      #   staircase_service (Pillow), gif_service, result_service, settings, backup
│   ├── keyboards/ middlewares/ utils/
│   └── seed/              # 4 hikoya (40 bosqich), demo topshiriqlar
├── migrations/001_init.sql  # 13 ta asosiy jadval + settings, user_states
├── assets/stories/image_prompts.md   # 40 ta rasm prompti
├── assets/fonts/ (zinapoya rasmi uchun)
├── scripts/ (make_password_hash.py, backup.py)
├── tests/
├── requirements.txt · render.yaml · .env.example · .gitignore
```

## 6. Testlarni ishga tushirish
Testlar **haqiqiy PostgreSQL** talab qiladi (Telegram esa soxtalashtirilgan, tarmoq kerak emas). Bo‘sh test bazasi yarating va:
```bash
pip install -r requirements-dev.txt
export TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/sirli_test   # ⚠️ bu baza testda TOZALANADI
pytest -q
```

Talablar bo‘yicha qamrov: admin kirishi (`test_admin`), begona foydalanuvchi, hikoya tanlash, o‘yin ochish, guruhni ro‘yxatga olish, topshiriq qo‘shish, tasodifiy tanlash (`test_special`), yuqoriga/pastga/1-zina/10-zina, individual topshiriq, vaqt tugashi, matnli javobni baholash, tuzoq, ikki guruhda bir vaqtda o‘yin, qayta ishga tushishdan tiklanish, takroriy javoblar (`test_game_flow`), webhook maxfiy so‘zi, konfiguratsiya, hikoya ma’lumotlari (`test_misc`).

## 7. Ma’lum cheklovlar
- Haqiqiy Telegram/Render/Supabase’da hali sinalmagan (yuqoriga qarang).
- Bot AI rasm yaratmaydi: zinapoya rasmi va GIF’lar Pillow bilan chiziladi; hikoya rasmlarini admin biriktiradi.
- Matnli topshiriqda jamoa nomidan **birinchi reply** yakuniy hisoblanadi (talabalar avval kelishib olishi kerak).
- Guruhda bot xabarlariga reply orqali javob olinadi (Telegram maxfiylik rejimi yoqiq bo‘lsa ham ishlaydi).
- Telegram guruhga daqiqasiga ~20 xabar limiti bor: har bir zina o‘zgarishida 4–5 xabar yuboriladi, juda tez ketma-ket javoblarda bot biroz kutishi mumkin (avtomatik qayta urinadi).
- Demo topshiriqlar umumiy o‘zbek tili/adabiyot savollari — o‘z fanigingizga almashtiring.
- Hikoya matnlari original yozilgan; xohlasangiz admin paneldan tahrirlang.
