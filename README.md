# Termux Agentic Assistant (Needle LLM) + O'zbek Tili Fuzzy Matching

An ultra-lightweight, local agentic assistant for Android/Termux that controls phone hardware and parses queries in plain **English** and **Uzbek (O'zbek lotin va kirill)** with advanced **Fuzzy Command Understanding**, typo correction, and contextual intent analysis. Powered by Cactus Compute's **Needle (14MB)** local LLM.

## 🌟 Yangi Imkoniyatlar / Features
- **🧠 Kuchli Fuzzy Command Understanding:** Foydalanuvchi buyruqlarni mukammal yozmasa ham (imlo xatolari, ortiqcha yoki tushirib qoldirilgan harflar: *"fonnarni yoqq"*, *"batareyya nechchi"*, *"telefon titra"*, *"wifiy"*), tizim uning maqsadini aniqlaydi.
- **🔄 Kontekstli tushunish:** So'zlarning obyektga bog'liq ma'nosi inobatga olinadi. Masalan:
  - `"fonarni yop"` / `"fonarni yopqoy"` → `set_torch(on=False)` (fonarni o'chirish)
  - `"fonarni och"` → `set_torch(on=True)` (fonarni yoqish)
  - `"kamerani och"` → `open_app("camera")`
- **🔤 O'zbek tili (Lotin & Kirill):** Har ikki alifboda erkin yozish mumkin (*"fonarni yoq"* yoki *"фонарни ёқ"*, *"батареям неча фоиз"*, *"расмга ол"*).
- **✍️ Apostroflar normallashtirilishi:** `o‘`, `o'`, `oʻ`, `o``, `o’`, `oʼ` va `g‘`, `g'`, `gʻ` kabi barcha belgilar to'liq normallashtiriladi.
- **🛡️ Xavfli harakatlar nazorati (Safety Confirmation):** SMS yuborish, qo'ng'iroq qilish kabi muhim amallarda tizim avval tasdiq so'raydi (*"Ali ga qo‘ng‘iroq qilishni xohlaysizmi?"*).
- **⚡ Tezkor va Yengil:** `difflib` (standart kutubxona) va ixtiyoriy `rapidfuzz` orqali Termux muhitida ortiqcha xotira sarflamasdan ishlaydi.
- **🌐 Glassmorphic Web UI & Telegram Bot:** Flask orqali veb interfeys hamda fonda chiquvchi Telegram bot.

---

## 📁 Project Structure
- `app.py`: Flask Web Server hosting the Web UI + background Telegram bot listener with Uzbek & English triggers.
- `termux_needle.py`: Lightweight interactive command-line assistant with multilingual support.
- `uzbek_intent.py`: Fuzzy matching, apostrophe normalization, typo correction, and contextual intent engine.
- `test_uzbek_commands.py`: 70+ automated tests covering typos, synonyms, Cyrillic, context, and confirmation flows.
- `requirements.txt`: Python package dependencies list.

---

## 🚀 O'rnatish va Ishga Tushirish / Setup Guide

### 1. Android / Termux Muhitida
Termux terminalida:
```bash
pkg update && pkg upgrade
pkg install termux-api python git
```
F-Droid orqali **Termux:API** ilovasi o'rnatilgani va unga Kamera/Lokatsiya/Storage ruxsatlari berilganiga ishonch hosil qiling.

### 2. Bog'liqliklarni o'rnatish
```bash
git clone https://github.com/AbuZar-Ansarii/Needle.git
cd Needle
pip install -r requirements.txt
```

### 3. Testlarni ishga tushirish (70+ test)
Fuzzy matching va barcha buyruqlar to'g'ri ishlashini tekshirish:
```bash
python test_uzbek_commands.py
```

### 4. Agentni ishga tushirish

#### Variant A: Web UI interfeysi
```bash
python app.py
```
Brauzerda oching: `http://127.0.0.1:5000` (yoki mahalliy tarmoq IP manzili orqali).

#### Variant B: Terminal CLI rejimi
```bash
python termux_needle.py
```

#### Variant C: Masofaviy Telegram Bot
```bash
python app.py --telegram <SIZNING_BOT_TOKENINGIZ>
```
Botga `/start` buyrug'ini yuboring va O'zbek yoki Ingliz tilida xabar yozib telefoningizni boshqaring!

---

## ⚡ Namuna Buyruqlar / Example Commands

| Intent / Amal | O'zbekcha (Lotin) | Imlo xatosi / Fuzzy | Kirillcha | English |
|---|---|---|---|---|
| **Fonarni yoqish** | `fonarni yoq`, `chiroqni yoq` | `fonnarni yoq`, `fonarni yoqq`, `chiroqni och` | `фонарни ёқ` | `turn on flashlight` |
| **Fonarni o'chirish** | `fonarni o'chir`, `chiroqni o'chir` | `fonarni yop`, `fonarni yopqoy`, `fonarni ochir` | `фонарни ўчир` | `turn off flashlight` |
| **Batareya holati** | `batareyam necha foiz` | `batareyya nechchi`, `zaryadim qancha` | `батареям неча фоиз` | `battery status` |
| **Titratish** | `telefonni titrat` | `telefon titra`, `tittrat` | `телефонни титрат` | `vibrate phone` |
| **Davomiylik bilan** | `telefonni 3 soniya titrat` | `3 sek titrat` | `3 сония титрат` | `vibrate for 3 seconds` |
| **Rasmga olish** | `rasmga ol`, `suratga ol` | `foto ol`, `rasimga ol` | `расмга ол` | `take a photo` |
| **Kamerani ochish** | `kamerani och` | `kammera och` | `камерани оч` | `open camera` |
| **GPS Joylashuv** | `joylashuvimni ko'rsat` | `lakatsiya yubor`, `qayerdam` | `жойлашувимни кўрсат` | `where am I` |
| **Wi-Fi ma'lumoti** | `WiFi ma'lumotlarini ko'rsat` | `wifiy haqida malumot ber`, `wifi korsat` | `вайфай маълумотлари` | `wi-fi info` |
| **Clipboard o'qish** | `clipboardni ko'rsat` | `klipbord korsat`, `buferni ko'rsat` | `клипбордни кўрсат` | `get clipboard` |
| **Clipboard yozish** | `clipboardga Salom yoz` | `klipbordga Salom yoz` | `клипбордга Салом ёз` | `copy Salom to clipboard` |
| **Qo'ng'iroq (Xavfli)** | `Ali ga qo'ng'iroq qil` | `Aliga qongiroq qil` *(Tasdiq: 'ha'/'yoq')* | `Алига қўнғироқ қил` | `call Ali` |
| **SMS (Xavfli)** | `Ali ga Salom deb sms yubor` | `sms yubor` *(Tasdiq: 'ha'/'yoq')* | `смс юбор` | `send sms to Ali saying Hello` |
| **Ilovalarni ochish** | `whatsappni och`, `youtubeni och` | `vatsapni och`, `yutubni och`, `telegr och` | `ютубни оч` | `open youtube` |
