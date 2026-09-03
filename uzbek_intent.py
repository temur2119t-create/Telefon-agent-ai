# -*- coding: utf-8 -*-
"""
uzbek_intent.py
Kuchli O'zbek tilidagi fuzzy command understanding va kontekstli intent tahlili tizimi.
Needle agentic assistant uchun O'zbekcha (Lotin va Kirill) va Inglizcha buyruqlarni
imlo xatolari, sinonimlar, noto'g'ri/kontekstli fe'llar va xavfli amallar nazorati bilan
qayta ishlash moduli.
"""

import sys
import os
import re
import json
from difflib import SequenceMatcher

# Agar rapidfuzz o'rnatilgan bo'lsa, undan foydalanamiz, aks holda difflib (standart kutubxona)
try:
    import rapidfuzz
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

# Ensure UTF-8 output encoding across environments
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Needle LLM uchun mukammal ko'p tilli tizim ko'rsatmasi (System Instruction)
SYSTEM_PROMPT_MULTILINGUAL = (
    "You are an on-device Android assistant running via Termux:API. "
    "Foydalanuvchi O‘zbek (lotin yoki kirill) yoki Ingliz tilida buyruq berishi mumkin. "
    "Foydalanuvchi matnida imlo xatolari, ortiqcha yoki tushirib qoldirilgan harflar, "
    "apostrof xatoliklari yoki sinonimlar bo'lishi mumkin. "
    "Sen foydalanuvchining asl maqsadini kontekst orqali aniqlashing va "
    "faqatgina mavjud tools_map ichidagi action va tool formatiga mos buyruq qaytarishing kerak. "
    "Mavjud bo'lmagan tool nomlarini aslo o'ylab topma. "
    "Available tools include: set_torch, get_battery_status, vibrate_device, "
    "take_camera_photo, open_app, get_location, get_wifi_info, scan_wifi_networks, "
    "get_clipboard, set_clipboard, make_phone_call, send_sms, get_sms_messages, "
    "get_contacts, get_call_log, show_toast, show_notification, text_to_speech, "
    "set_screen_brightness, get_volume_info, set_volume, record_audio_start, "
    "record_audio_stop, get_telephony_info, download_file, share_content, authenticate_fingerprint."
)

# O'zbek Kirill alifbosidan Lotin alifbosiga to'liq transliteratsiya jadvali
CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ҳ': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh',
    'ъ': "'", 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya', 'ў': "o'", 'қ': 'q', 'ғ': "g'"
}

# Xavfli harakatlar uchun kutish holatidagi tasdiqlar (Session ID -> pending dict)
_PENDING_CONFIRMATIONS = {}

def string_similarity(s1: str, s2: str) -> float:
    """Ikki satr orasidagi o'xshashlik koeffitsienti (0.0 dan 1.0 gacha)."""
    s1 = s1.lower().strip()
    s2 = s2.lower().strip()
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    if HAS_RAPIDFUZZ:
        return fuzz.ratio(s1, s2) / 100.0
    return SequenceMatcher(None, s1, s2).ratio()

def transliterate_cyrillic_uzbek(text: str) -> str:
    """O'zbek Kirill yozuvini Lotin yozuviga transliteratsiya qiladi."""
    if not text:
        return ""
    res = []
    for ch in text:
        low = ch.lower()
        if low in CYRILLIC_TO_LATIN:
            trans = CYRILLIC_TO_LATIN[low]
            res.append(trans.upper() if ch.isupper() else trans)
        else:
            res.append(ch)
    return ''.join(res)

def normalize_apostrophes(text: str) -> str:
    """
    Barcha turdagi apostroflarni (`, ‘, ’, ʻ, ʼ, ´) standart ASCII (') belgisiga keltiradi.
    o‘, o', oʻ, o`, o’, oʼ -> o'
    g‘, g', gʻ, g`, g’, gʼ -> g'
    """
    if not text:
        return ""
    cleaned = re.sub(r"[\u2018\u2019\u02BB\u02BC\u0060\u00B4`ʼʻ‘]", "'", text)
    return cleaned

def normalize_text(text: str) -> str:
    """
    Unicode normalization, Kirill transliteratsiyasi, apostrof normallashtirish,
    lowercase qilish va ortiqcha bo'sh joylarni tozalash pipeline'i.
    """
    if not text:
        return ""
    t = transliterate_cyrillic_uzbek(text)
    t = normalize_apostrophes(t)
    t = t.lower()
    t = re.sub(r"[^\w\s\'+:-]", " ", t)  # tinish belgilarini bo'shliq bilan almashtirish
    t = re.sub(r"\s+", " ", t).strip()
    return t

# ----------------------------------------------------------------------
# Lug'atlar va Typo Correction (Imlo xatolarini tuzatish)
# ----------------------------------------------------------------------

CANONICAL_KEYWORDS = {
    # Objects
    "fonar": ["fonar", "fonarni", "fonari", "chiroq", "chiroqni", "chirogi", "chirog'i", "flashlight", "torch", "fanaar", "fonor", "fonarcha"],
    "batareya": ["batareya", "batareyam", "batareyasi", "zaryad", "zaryadim", "zaryadi", "quvvat", "quvvatim", "quvvati", "battery", "akkumulyator", "batreya", "batareyka", "zaryatka"],
    "kamera": ["kamera", "kamerani", "kamerasi", "foto", "rasm", "rasmni", "surat", "suratni", "fotoapparat", "camera", "photo"],
    "joylashuv": ["joylashuv", "joylashuvim", "joylashuvni", "joylashuvimni", "lokatsiya", "lokatsiyam", "lokatsiyani", "location", "qayerdaman", "manzil", "manzilim", "koordinata", "gps"],
    "wifi": ["wifi", "wi-fi", "vayfay", "vay-fay", "internet", "tarmoq", "network", "wifiy", "wifisi"],
    "clipboard": ["clipboard", "clipboardni", "klipbord", "klipbordni", "bufer", "buferni", "xotira"],
    "sms": ["sms", "xabar", "xabarni", "xabarnoma", "message", "text"],
    "kontakt": ["kontakt", "kontaktlar", "raqamlar", "contacts", "contact"],
    "ovoz": ["ovoz", "audio", "diktofon", "mikrofon", "volume", "tovush"],
    "titrat": ["titrat", "titrash", "titra", "vibrat", "vibrate", "vibro", "vibratsiya"],
    "yorqinlik": ["yorqinlik", "yorqinlikni", "brightness"],
    
    # Actions
    "yoqish": ["yoq", "yoqish", "yoqib", "yoqqin", "yoqvor", "yoqq", "yok", "och", "ochish", "ishga tushir", "aktiv qil", "on", "turn on", "switch on", "enable"],
    "ochirish": ["o'chir", "ochir", "ochirish", "o'chirish", "o'chirvor", "yop", "yopish", "yopqoy", "to'xtat", "toxtat", "off", "turn off", "switch off", "disable", "yopvor"]
}

def correct_typo(word: str) -> str:
    """
    Berilgan so'zning imlo xatolarini tekshiradi va ma'lum standart kalit so'zlarga
    yaqin bo'lsa (similarity >= 0.78), to'g'rilangan variantini qaytaradi.
    """
    clean_w = word.strip().lower()
    if not clean_w or len(clean_w) < 3:
        return clean_w

    # To'g'ridan-to'g'ri moslik tekshiruvi
    for canonical, variations in CANONICAL_KEYWORDS.items():
        if clean_w in variations:
            return canonical

    # Fuzzy o'xshashlik tekshiruvi
    best_match = clean_w
    best_score = 0.0

    for canonical, variations in CANONICAL_KEYWORDS.items():
        for var in variations:
            score = string_similarity(clean_w, var)
            if score > best_score and score >= 0.78:
                best_score = score
                best_match = canonical

    return best_match

def resolve_contact_number(target: str, contacts: list) -> str:
    """
    Kontakt nomini ro'yxatdan qidirib telefon raqamini aniqlaydi.
    Agar topilmasa yoki raqam bo'lsa, o'zini qaytaradi.
    """
    clean_target = target.strip()
    digits_only = re.sub(r"[^\d+]", "", clean_target)
    if digits_only and (clean_target.startswith("+") or clean_target.isdigit() or len(digits_only) >= 7):
        return clean_target

    target_low = clean_target.lower()
    if isinstance(contacts, list):
        for c in contacts:
            if isinstance(c, dict):
                c_name = str(c.get("name", "")).strip().lower()
                if c_name == target_low or target_low in c_name:
                    return str(c.get("number", clean_target))

    return clean_target

# ----------------------------------------------------------------------
# Kontekstli Intent Tahlili va Confidence Score Hisoblash
# ----------------------------------------------------------------------

def calculate_confidence(raw_query: str, matched_info: dict) -> float:
    """
    Aniqlangan intent va foydalanuvchi so'rovi asosida ishonch darajasini (confidence) hisoblaydi:
    0.95 - 1.00 -> Juda yuqori ishonch, aniq moslik
    0.75 - 0.94 -> Yuqori ishonch (typo yoki sinonim orqali topilgan)
    0.40 - 0.74 -> O'rta ishonch (qo'shimcha aniqlashtirish tavsiya etiladi)
    0.00 - 0.39 -> Aniqlanmadi
    """
    if not matched_info.get("matched"):
        return 0.0

    match_type = matched_info.get("match_type", "fuzzy")
    if match_type == "exact":
        return 1.0
    if match_type == "strong_regex":
        return 0.98
    if match_type == "contextual_verb":  # Masalan: "fonarni yop" -> set_torch(False)
        return 0.95
    if match_type == "fuzzy_typo":       # Masalan: "fonnarni yoqq" -> set_torch(True)
        return 0.92
    if match_type == "partial_synonym":
        return 0.85

    return 0.80

def find_fuzzy_intent(query_text: str) -> dict:
    """
    So'rovdan obyekt, harakat va parametrlarni kontekstual ravishda aniqlaydi.
    """
    raw = query_text.strip()
    norm = normalize_text(raw)
    words = norm.split()
    corrected_words = [correct_typo(w) for w in words]
    corrected_str = " ".join(corrected_words)

    # -------------------------------------------------------------
    # 1. Flashlight / Torch (Fonar / Chiroq)
    # -------------------------------------------------------------
    has_torch_obj = any(w in corrected_words for w in ("fonar", "chiroq")) or \
                    any(string_similarity(w, "fonarni") >= 0.75 or string_similarity(w, "chiroqni") >= 0.75 for w in words) or \
                    "flashlight" in norm or "torch" in norm

    if has_torch_obj:
        # Kontekst: Fonar uchun "och" / "yoq" -> ON, "yop" / "o'chir" -> OFF
        # O'chirish ko'rsatkichlari:
        is_turn_off = any(w in corrected_words for w in ("ochirish",)) or \
                      any(w in words for w in ("o'chir", "ochir", "yop", "yopqoy", "yopib", "to'xtat", "toxtat", "off", "disable", "o'chirib", "yopvor")) or \
                      "turn off" in norm or "switch off" in norm or "off qil" in norm

        # Yoqish ko'rsatkichlari:
        is_turn_on = any(w in corrected_words for w in ("yoqish",)) or \
                     any(w in words for w in ("yoq", "yoqq", "yoqvor", "yoqib", "och", "ishga", "on", "enable", "yoqqin", "aktiv")) or \
                     "turn on" in norm or "switch on" in norm or "yoq" in norm

        if is_turn_off:
            match_type = "exact" if norm in ("fonarni o'chir", "fonarni ochir", "chiroqni o'chir") else \
                         ("contextual_verb" if "yop" in norm else "fuzzy_typo")
            return {
                "matched": True,
                "tool_name": "set_torch",
                "args": {"on": False},
                "action_desc": "flashlight_off",
                "match_type": match_type,
                "is_dangerous": False,
                "reasoning": "Kontekst tahlili: Fonarni o'chirish / yopish maqsadi aniqlandi (set_torch: False)."
            }

        if is_turn_on:
            match_type = "exact" if norm in ("fonarni yoq", "chiroqni yoq") else \
                         ("contextual_verb" if "och" in norm else "fuzzy_typo")
            return {
                "matched": True,
                "tool_name": "set_torch",
                "args": {"on": True},
                "action_desc": "flashlight_on",
                "match_type": match_type,
                "is_dangerous": False,
                "reasoning": "Kontekst tahlili: Fonarni yoqish / ochish maqsadi aniqlandi (set_torch: True)."
            }

    # -------------------------------------------------------------
    # 2. Battery (Batareya / Zaryad / Quvvat)
    # -------------------------------------------------------------
    has_battery_obj = any(w in corrected_words for w in ("batareya",)) or \
                      any(string_similarity(w, "batareya") >= 0.72 or string_similarity(w, "zaryad") >= 0.75 or string_similarity(w, "quvvat") >= 0.75 for w in words) or \
                      "battery" in norm

    if has_battery_obj:
        match_type = "exact" if norm in ("batareyam necha foiz", "batareya holati") else "fuzzy_typo"
        return {
            "matched": True,
            "tool_name": "get_battery_status",
            "args": {},
            "action_desc": "battery_status",
            "match_type": match_type,
            "is_dangerous": False,
            "reasoning": "Batareya holati va quvvat darajasini tekshirish maqsadi aniqlandi."
        }

    # -------------------------------------------------------------
    # 3. Vibration (Telefonni titratish)
    # -------------------------------------------------------------
    has_vibrate = any(w in corrected_words for w in ("titrat",)) or \
                  any(string_similarity(w, "titrat") >= 0.70 or string_similarity(w, "vibrate") >= 0.75 for w in words) or \
                  "titra" in norm or "vibro" in norm

    if has_vibrate:
        sec_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:soniya|sekund|sek|second|sec|s\b)", norm)
        ms_m = re.search(r"(\d+)\s*(?:millisoniya|ms\b)", norm)
        duration_ms = 500
        if sec_m:
            duration_ms = int(float(sec_m.group(1)) * 1000)
        elif ms_m:
            duration_ms = int(ms_m.group(1))

        match_type = "exact" if "telefonni titrat" in norm else "fuzzy_typo"
        return {
            "matched": True,
            "tool_name": "vibrate_device",
            "args": {"duration_ms": duration_ms},
            "action_desc": f"vibrate(duration_ms={duration_ms})",
            "match_type": match_type,
            "is_dangerous": False,
            "reasoning": f"Telefonni {duration_ms} millisoniya titratish maqsadi aniqlandi."
        }

    # -------------------------------------------------------------
    # 4. Camera (Rasmga olish vs Kamera ilovasini ochish/yopish)
    # -------------------------------------------------------------
    has_camera_obj = any(w in corrected_words for w in ("kamera",)) or \
                     any(string_similarity(w, "kamera") >= 0.75 or string_similarity(w, "rasm") >= 0.75 or string_similarity(w, "surat") >= 0.75 for w in words) or \
                     "camera" in norm or "photo" in norm

    if has_camera_obj:
        # Rasmga olish harakati:
        is_capture = any(w in words for w in ("ol", "tushir", "tort", "qil", "olvor", "take", "capture", "snap")) or \
                     "rasmga ol" in norm or "suratga ol" in norm or "take photo" in norm or "rasm ol" in norm

        # Ilovani ochish:
        is_open_app = any(w in words for w in ("och", "ishga", "kir", "boshla", "open", "launch")) or \
                      "kamerani och" in norm or "open camera" in norm

        # Ilovani yopish:
        is_close_app = any(w in words for w in ("yop", "chiq", "close", "exit"))

        if is_capture and not is_open_app:
            match_type = "exact" if norm in ("rasmga ol", "suratga ol", "take a photo") else "fuzzy_typo"
            return {
                "matched": True,
                "tool_name": "take_camera_photo",
                "args": {},
                "action_desc": "camera_capture",
                "match_type": match_type,
                "is_dangerous": False,
                "reasoning": "Orqa kamera orqali rasmga olish maqsadi aniqlandi."
            }

        if is_open_app:
            match_type = "exact" if norm in ("kamerani och", "open camera") else "fuzzy_typo"
            return {
                "matched": True,
                "tool_name": "open_app",
                "args": {"app_name": "camera"},
                "action_desc": "open_camera",
                "match_type": match_type,
                "is_dangerous": False,
                "reasoning": "Kamera ilovasini ochish maqsadi aniqlandi."
            }

    # -------------------------------------------------------------
    # 5. Location (Joylashuv / Men qayerdaman)
    # -------------------------------------------------------------
    has_location_obj = any(w in corrected_words for w in ("joylashuv",)) or \
                       any(string_similarity(w, "joylashuv") >= 0.70 or string_similarity(w, "lokatsiya") >= 0.75 for w in words) or \
                       "qayerdaman" in norm or "qayerdam" in norm or "qattaman" in norm or "location" in norm or "where am i" in norm

    if has_location_obj:
        match_type = "exact" if norm in ("joylashuvimni ko'rsat", "men qayerdaman", "where am i") else "fuzzy_typo"
        return {
            "matched": True,
            "tool_name": "get_location",
            "args": {},
            "action_desc": "get_location",
            "match_type": match_type,
            "is_dangerous": False,
            "reasoning": "GPS koordinatalari va joylashuvni aniqlash maqsadi aniqlandi."
        }

    # -------------------------------------------------------------
    # 6. Wi-Fi / Internet
    # -------------------------------------------------------------
    has_wifi_obj = any(w in corrected_words for w in ("wifi",)) or \
                   any(string_similarity(w, "wifi") >= 0.75 or string_similarity(w, "vayfay") >= 0.75 for w in words) or \
                   "internet" in norm or "tarmoq" in norm

    if has_wifi_obj:
        is_scan = any(w in words for w in ("qidir", "skaner", "atrof", "atrofdagi", "top", "scan", "list"))
        if is_scan:
            return {
                "matched": True,
                "tool_name": "scan_wifi_networks",
                "args": {},
                "action_desc": "wifi_scan",
                "match_type": "strong_regex",
                "is_dangerous": False,
                "reasoning": "Atrofdagi Wi-Fi tarmoqlarini skaner qilish maqsadi aniqlandi."
            }
        return {
            "matched": True,
            "tool_name": "get_wifi_info",
            "args": {},
            "action_desc": "wifi_info",
            "match_type": "fuzzy_typo",
            "is_dangerous": False,
            "reasoning": "Faol Wi-Fi ulanishi haqida ma'lumot olish maqsadi aniqlandi."
        }

    # -------------------------------------------------------------
    # 7. Clipboard (Bufer / Xotira)
    # -------------------------------------------------------------
    has_clipboard_obj = any(w in corrected_words for w in ("clipboard",)) or \
                        any(string_similarity(w, "clipboard") >= 0.75 or string_similarity(w, "klipbord") >= 0.75 or string_similarity(w, "bufer") >= 0.75 for w in words)

    if has_clipboard_obj:
        m_write = re.search(r"(?:clipboard(?:ga)?|bufer(?:ga)?|klipbord(?:ga)?)\s+(?:yoz\s*[:=]?\s*(.+)|(.+?)\s+yoz(?:ish|gin)?)$", norm, re.IGNORECASE)
        if not m_write:
            m_write = re.search(r"(?:copy|write|set)\s+(.+?)\s+(?:to|in)\s+(?:clipboard|bufer|klipbord)", norm, re.IGNORECASE)
        if m_write:
            val = (m_write.group(1) or m_write.group(2) or "").strip().strip('"\'')
            if val:
                return {
                    "matched": True,
                    "tool_name": "set_clipboard",
                    "args": {"text": val},
                    "action_desc": f"clipboard_write('{val}')",
                    "match_type": "strong_regex",
                    "is_dangerous": False,
                    "reasoning": f"Clipboardga matn nusxalash maqsadi: '{val}'."
                }
        return {
            "matched": True,
            "tool_name": "get_clipboard",
            "args": {},
            "action_desc": "clipboard_read",
            "match_type": "fuzzy_typo",
            "is_dangerous": False,
            "reasoning": "Clipboarddagi matnni o'qish maqsadi aniqlandi."
        }

    # -------------------------------------------------------------
    # 8. Call Log History (Qo'ng'iroqlar tarixi)
    # -------------------------------------------------------------
    if any(k in norm for k in ("qo'ng'iroqlar", "qongiroqlar", "chaqiruvlar", "call log", "call logs", "calls")) and \
       any(w in norm for w in ("tarix", "oxirgi", "kim", "history", "recent", "log")):
        m_lim = re.search(r"(\d+)", norm)
        limit = int(m_lim.group(1)) if m_lim else 5
        return {
            "matched": True,
            "tool_name": "get_call_log",
            "args": {"limit": limit},
            "action_desc": f"get_call_log(limit={limit})",
            "match_type": "strong_regex",
            "is_dangerous": False,
            "reasoning": f"Oxirgi {limit} ta qo'ng'iroqlar tarixini ko'rsatish maqsadi aniqlandi."
        }

    # -------------------------------------------------------------
    # 9. Phone Call (Qo'ng'iroq qilish - XAVFLI HARAKAT)
    # -------------------------------------------------------------
    m_call = None
    if "tarix" not in norm and "history" not in norm:
        m_call = re.search(r"(\+?[a-zA-Z0-9_\u0400-\u04FF]+)(?:ga|\s+ga|\s+ga\s+ham)?\s+(?:qo'?ng'?iroq\s+qil|telefon\s+qil|qilvor|tel\s+qil|call)", norm)
        if not m_call:
            m_call = re.search(r"(?:qo'?ng'?iroq\s+qil|telefon\s+qil|call)\s+(\+?[a-zA-Z0-9_\u0400-\u04FF]+)", norm)
        if not m_call and any(string_similarity(w, "qongiroq") >= 0.75 for w in words):
            # Masalan "Ali qongroq qil"
            target_word = words[0] if len(words) > 1 and words[0] not in ("qongiroq", "telefon", "qil") else "Ali"
            m_call = True
            target = target_word
        elif m_call:
            target = m_call.group(1).strip()
        else:
            target = None
    else:
        target = None

    if target:
        if target.lower().endswith("ga") and len(target) > 2 and not target.isdigit():
            target = target[:-2]
        return {
            "matched": True,
            "tool_name": "make_phone_call",
            "args": {"phone_number": target},
            "action_desc": f"call_contact('{target}')",
            "match_type": "strong_regex",
            "is_dangerous": True,  # XAVFLI HARAKAT: tasdiqlash talab qilinadi
            "reasoning": f"Qo'ng'iroq qilish maqsadi aniqlandi: {target}."
        }

    # -------------------------------------------------------------
    # 9. SMS (Xabar yuborish - XAVFLI HARAKAT / SMS o'qish)
    # -------------------------------------------------------------
    has_sms_obj = any(w in corrected_words for w in ("sms",)) or \
                  any(string_similarity(w, "sms") >= 0.80 or string_similarity(w, "xabar") >= 0.75 for w in words)

    if has_sms_obj:
        is_read = any(w in words for w in ("o'qi", "ko'rsat", "kelgan", "oxirgi", "list", "read", "inbox"))
        if is_read:
            m_lim = re.search(r"(\d+)", norm)
            limit = int(m_lim.group(1)) if m_lim else 5
            return {
                "matched": True,
                "tool_name": "get_sms_messages",
                "args": {"limit": limit},
                "action_desc": f"get_sms_messages(limit={limit})",
                "match_type": "strong_regex",
                "is_dangerous": False,
                "reasoning": f"Oxirgi {limit} ta SMS xabarni o'qish maqsadi aniqlandi."
            }

        # SMS yuborish (XAVFLI HARAKAT)
        m_sms_full = re.search(r"(\+?[a-zA-Z0-9_\u0400-\u04FF]+)(?:ga|\s+ga)?\s+(.+?)\s+(?:deb|matnli)?\s*sms\s+yubor", norm)
        recip = m_sms_full.group(1).strip() if m_sms_full else "contact"
        body = m_sms_full.group(2).strip().strip('"\'') if m_sms_full else "Salom"
        if recip.lower().endswith("ga") and len(recip) > 2 and not recip.isdigit():
            recip = recip[:-2]
        return {
            "matched": True,
            "tool_name": "send_sms",
            "args": {"recipient": recip, "message": body},
            "action_desc": f"send_sms('{recip}', '{body}')",
            "match_type": "strong_regex",
            "is_dangerous": True,  # XAVFLI HARAKAT: tasdiqlash talab qilinadi
            "reasoning": f"{recip} ga SMS xabar yuborish maqsadi aniqlandi."
        }

    # -------------------------------------------------------------
    # 10. Contacts List (Kontaktlar)
    # -------------------------------------------------------------
    has_contact_obj = any(w in corrected_words for w in ("kontakt",)) or \
                      any(string_similarity(w, "kontakt") >= 0.75 or string_similarity(w, "contacts") >= 0.75 for w in words)
    if has_contact_obj:
        return {
            "matched": True,
            "tool_name": "get_contacts",
            "args": {},
            "action_desc": "get_contacts",
            "match_type": "fuzzy_typo",
            "is_dangerous": False,
            "reasoning": "Kontaktlar ro'yxatini ko'rsatish maqsadi aniqlandi."
        }

    # -------------------------------------------------------------
    # 11. Apps (WhatsApp, Telegram, YouTube, Chrome, etc.)
    # -------------------------------------------------------------
    app_keywords = {
        "whatsapp": ["whatsapp", "vatsap", "vatssap", "wa"],
        "telegram": ["telegram", "telegr", "tg"],
        "youtube": ["youtube", "yutub", "yt"],
        "chrome": ["chrome", "chrom", "google", "brauzer"],
        "instagram": ["instagram", "insta"],
        "spotify": ["spotify"],
        "calculator": ["kalkulyator", "kalkulator", "calculator"],
        "settings": ["sozlamalar", "nastroyka", "settings"]
    }
    for app_id, triggers in app_keywords.items():
        if any(any(string_similarity(w, tr) >= 0.78 for w in words) for tr in triggers):
            if any(w in words for w in ("och", "kir", "ishga", "open", "launch")):
                return {
                    "matched": True,
                    "tool_name": "open_app",
                    "args": {"app_name": app_id},
                    "action_desc": f"open_app('{app_id}')",
                    "match_type": "fuzzy_typo",
                    "is_dangerous": False,
                    "reasoning": f"{app_id} ilovasini ochish maqsadi aniqlandi."
                }

    # -------------------------------------------------------------
    # 12. Audio Recording (Ovoz yozish)
    # -------------------------------------------------------------
    if any(w in words for w in ("ovoz", "audio", "diktofon", "mikrofon")):
        if any(w in words for w in ("to'xtat", "toxtat", "ochir", "tamom", "stop")):
            return {
                "matched": True,
                "tool_name": "record_audio_stop",
                "args": {},
                "action_desc": "record_audio_stop",
                "match_type": "strong_regex",
                "is_dangerous": False,
                "reasoning": "Ovoz yozishni to'xtatish maqsadi aniqlandi."
            }
        if any(w in words for w in ("boshla", "yoz", "yoq", "start", "record")):
            return {
                "matched": True,
                "tool_name": "record_audio_start",
                "args": {"file_path": "recording.3gp", "limit_seconds": 0},
                "action_desc": "record_audio_start",
                "match_type": "strong_regex",
                "is_dangerous": False,
                "reasoning": "Ovoz yozishni boshlash maqsadi aniqlandi."
            }

    # -------------------------------------------------------------
    # 13. Screen Brightness (Ekran yorqinligi)
    # -------------------------------------------------------------
    if "yorqinlik" in norm or "brightness" in norm or any(string_similarity(w, "yorqinlik") >= 0.75 for w in words):
        m_br = re.search(r"(\d+)", norm)
        level = "150"
        if m_br:
            level = str(max(0, min(255, int(m_br.group(1)))))
        return {
            "matched": True,
            "tool_name": "set_screen_brightness",
            "args": {"level": level},
            "action_desc": f"set_screen_brightness({level})",
            "match_type": "strong_regex",
            "is_dangerous": False,
            "reasoning": f"Ekran yorqinligini {level} ga sozlash maqsadi aniqlandi."
        }

    # -------------------------------------------------------------
    # 14. Volume (Ovoz balandligi)
    # -------------------------------------------------------------
    if "ovoz" in norm or "volume" in norm or "tovush" in norm:
        m_vol = re.search(r"(\d+)", norm)
        if m_vol:
            val = int(m_vol.group(1))
            return {
                "matched": True,
                "tool_name": "set_volume",
                "args": {"stream": "music", "volume": val},
                "action_desc": f"set_volume('music', {val})",
                "match_type": "strong_regex",
                "is_dangerous": False,
                "reasoning": f"Musiqa ovozini {val} ga sozlash maqsadi aniqlandi."
            }
        return {
            "matched": True,
            "tool_name": "get_volume_info",
            "args": {},
            "action_desc": "get_volume_info",
            "match_type": "fuzzy_typo",
            "is_dangerous": False,
            "reasoning": "Ovoz balandligi holatini tekshirish maqsadi aniqlandi."
        }

    return {"matched": False}

def match_intent(text: str) -> dict:
    """
    To'liq pipeline orqali intent, parametrlar va confidence score'ni aniqlaydi.
    """
    result = find_fuzzy_intent(text)
    if result.get("matched"):
        conf = calculate_confidence(text, result)
        result["confidence"] = conf
    else:
        result["confidence"] = 0.0
    return result

# ----------------------------------------------------------------------
# Asosiy Dispatcher va Xavfli Harakatlar Nazorati
# ----------------------------------------------------------------------

def process_agent_query(agent, query: str, tools_map: dict, session_id: str = "default", preprocess_query_fn=None) -> dict:
    """
    Foydalanuvchi so'rovini qayta ishlovchi bosh dispatcher:
    1. Pending tasdiqlashni tekshiradi (agar foydalanuvchi 'ha' yoki 'yoq' desa).
    2. Fuzzy intent matching va confidence score hisoblaydi.
    3. Agar action XAVFLI (qo'ng'iroq, SMS) bo'lsa, avtomatik bajarmasdan tasdiq so'raydi.
    4. Agar confidence >= 0.70 bo'lsa, xavfsiz tool'ni to'g'ridan-to'g'ri ishga tushiradi.
    5. Agar confidence 0.40 - 0.69 bo'lsa, foydalanuvchidan aniqlashtirish so'raydi.
    6. Agar intent topilmasa (confidence < 0.40), Needle LLM modeliga yo'naltiradi (Fallback).
    """
    user_query = query.strip() if query else ""
    if not user_query:
        return {
            "type": "error",
            "reasoning": "Bo'sh so'rov yuborildi.",
            "confidence": 0.0,
            "results": ["Xato: Buyruq matni bo'sh."]
        }

    norm_q = normalize_text(user_query)

    # 1. Oldingi xavfli harakat uchun tasdiqni tekshirish
    if session_id in _PENDING_CONFIRMATIONS:
        pending = _PENDING_CONFIRMATIONS[session_id]
        # Foydalanuvchi tasdiqlasa:
        if norm_q in ("ha", "tasdiqlayman", "yes", "albatta", "bajar", "ok", "mayli"):
            del _PENDING_CONFIRMATIONS[session_id]
            t_name = pending["tool_name"]
            t_args = pending["args"]
            t_fn = tools_map.get(t_name)
            if t_fn:
                try:
                    res_out = t_fn(**t_args)
                    return {
                        "type": "call",
                        "reasoning": f"Foydalanuvchi tasdiqladi. Amal bajarildi: {t_name}",
                        "confidence": 1.0,
                        "function_calls": [{"name": t_name, "arguments": t_args}],
                        "results": [res_out]
                    }
                except Exception as ex:
                    return {"type": "error", "confidence": 0.5, "results": [f"Xatolik: {ex}"]}

        # Foydalanuvchi bekor qilsa:
        if norm_q in ("yo'q", "yoq", "bekor", "bekor qil", "no", "cancel", "kerakmas"):
            del _PENDING_CONFIRMATIONS[session_id]
            return {
                "type": "respond",
                "reasoning": "Foydalanuvchi amaldan voz kechdi.",
                "confidence": 1.0,
                "results": ["Amal bekor qilindi."]
            }

    # 2. Fuzzy Intent Matching
    intent_res = match_intent(user_query)
    conf = intent_res.get("confidence", 0.0)

    if intent_res.get("matched"):
        tool_name = intent_res.get("tool_name")
        args = intent_res.get("args", {})
        action_desc = intent_res.get("action_desc")
        reasoning = intent_res.get("reasoning")
        is_dangerous = intent_res.get("is_dangerous", False)

        # Kontakt nomini aniqlash (make_phone_call / send_sms uchun)
        if tool_name == "make_phone_call" and "phone_number" in args:
            target = args["phone_number"]
            contacts_fn = tools_map.get("get_contacts")
            if contacts_fn:
                try:
                    c_list = contacts_fn()
                    if isinstance(c_list, str):
                        try:
                            c_list = json.loads(c_list)
                        except Exception:
                            c_list = []
                    args["phone_number"] = resolve_contact_number(target, c_list)
                except Exception:
                    pass

        if tool_name == "send_sms" and "recipient" in args:
            target = args["recipient"]
            contacts_fn = tools_map.get("get_contacts")
            if contacts_fn:
                try:
                    c_list = contacts_fn()
                    if isinstance(c_list, str):
                        try:
                            c_list = json.loads(c_list)
                        except Exception:
                            c_list = []
                    args["recipient"] = resolve_contact_number(target, c_list)
                except Exception:
                    pass

        # 3. Xavfli harakat bo'lsa - TASDIQLASH SO'RASH
        if is_dangerous:
            _PENDING_CONFIRMATIONS[session_id] = {
                "tool_name": tool_name,
                "args": args,
                "action_desc": action_desc
            }
            if tool_name == "make_phone_call":
                confirm_msg = f"{args['phone_number']} ga qo‘ng‘iroq qilishni xohlaysizmi? (Tasdiqlash uchun: 'ha', bekor qilish: 'yoq')"
            elif tool_name == "send_sms":
                confirm_msg = f"{args['recipient']} ga SMS yuborishni xohlaysizmi? (Tasdiqlash uchun: 'ha', bekor qilish: 'yoq')"
            else:
                confirm_msg = f"'{action_desc}' amalini bajarishni xohlaysizmi? (Tasdiqlash uchun: 'ha', bekor qilish: 'yoq')"

            return {
                "type": "confirm",
                "needs_confirmation": True,
                "confidence": conf,
                "reasoning": f"Xavfli amal aniqlandi ({tool_name}). Foydalanuvchi tasdig'i kutilmoqda.",
                "results": [confirm_msg]
            }

        # 4. Yuqori ishonch (conf >= 0.70) bo'lsa - avtomatik bajarish
        if conf >= 0.70:
            tool_fn = tools_map.get(tool_name)
            if tool_fn:
                try:
                    print(f"[Fuzzy Engine Match: {conf:.2f}] {action_desc} -> {tool_name}({args})")
                    res_val = tool_fn(**args)
                    return {
                        "type": "call",
                        "reasoning": reasoning,
                        "confidence": conf,
                        "function_calls": [{"name": tool_name, "arguments": args}],
                        "results": [res_val]
                    }
                except Exception as err:
                    return {
                        "type": "error",
                        "reasoning": f"Tool execution failed: {err}",
                        "confidence": conf,
                        "results": [f"Error in {tool_name}: {str(err)}"]
                    }

        # 5. O'rtacha ishonch (0.40 <= conf < 0.70) - Aniqlashtirish so'rash
        return {
            "type": "clarify",
            "reasoning": f"O'rtacha ishonch ({conf:.2f}). Buyruq aniqlashtirishni talab qiladi.",
            "confidence": conf,
            "results": [f"Buyrug'ingiz to'liq tushunarsiz bo'ldi. Siz '{action_desc}' ni nazarda tutdingizmi?"]
        }

    # 6. LLM Fallback (conf < 0.40)
    query_to_send = user_query
    if preprocess_query_fn:
        query_to_send = preprocess_query_fn(query_to_send)

    print(f"[LLM Fallback] Passing query to Needle local model: '{query_to_send}'")
    try:
        res = agent.run(query_to_send)
        return res
    except Exception as exc:
        print(f"[LLM Error] {exc}", file=sys.stderr)
        return {
            "type": "error",
            "reasoning": f"LLM error: {exc}",
            "confidence": 0.0,
            "results": [f"Error: {str(exc)}"]
        }
