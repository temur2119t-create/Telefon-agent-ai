# -*- coding: utf-8 -*-
"""
test_uzbek_commands.py
O'zbek tili fuzzy buyruqlarini, imlo xatolarini, kontekstli fe'llarni,
sinonimlarni va xavfli amallarni tekshiruvchi to'liq test to'plami (50+ test).
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import uzbek_intent

def run_tests():
    test_cases = [
        # -------------------------------------------------------------
        # 1. To'g'ri O'zbekcha buyruqlar
        # -------------------------------------------------------------
        ("fonarni yoq", "set_torch", {"on": True}, "To'g'ri: fonarni yoq"),
        ("fonarni o'chir", "set_torch", {"on": False}, "To'g'ri: fonarni o'chir"),
        ("batareyam necha foiz", "get_battery_status", {}, "To'g'ri: batareyam necha foiz"),
        ("telefonni titrat", "vibrate_device", {"duration_ms": 500}, "To'g'ri: telefonni titrat"),
        ("rasmga ol", "take_camera_photo", {}, "To'g'ri: rasmga ol"),
        ("kamerani och", "open_app", {"app_name": "camera"}, "To'g'ri: kamerani och"),
        ("joylashuvimni ko'rsat", "get_location", {}, "To'g'ri: joylashuvimni ko'rsat"),
        ("men qayerdaman", "get_location", {}, "To'g'ri: men qayerdaman"),
        ("WiFi ma'lumotlarini ko'rsat", "get_wifi_info", {}, "To'g'ri: WiFi ma'lumotlari"),
        ("clipboardni ko'rsat", "get_clipboard", {}, "To'g'ri: clipboardni ko'rsat"),

        # -------------------------------------------------------------
        # 2. Imlo xatolari va typo correction (ortiqcha / tushib qolgan harflar)
        # -------------------------------------------------------------
        ("fonnarni yoq", "set_torch", {"on": True}, "Typo (ortiqcha n): fonnarni yoq"),
        ("fonarni yoqq", "set_torch", {"on": True}, "Typo (ortiqcha q): fonarni yoqq"),
        ("fonar yoq", "set_torch", {"on": True}, "Tushgan harf (ni yo'q): fonar yoq"),
        ("fonari yoq", "set_torch", {"on": True}, "Typo: fonari yoq"),
        ("batareyya nechchi", "get_battery_status", {}, "Typo: batareyya nechchi"),
        ("batreya nechi", "get_battery_status", {}, "Typo: batreya nechi"),
        ("telefon titra", "vibrate_device", {}, "Tushgan harf: telefon titra"),
        ("tittrat", "vibrate_device", {}, "Typo: tittrat"),
        ("wifiy haqida malumot ber", "get_wifi_info", {}, "Typo: wifiy haqida malumot ber"),
        ("wifi korsat", "get_wifi_info", {}, "Typo: wifi korsat"),
        ("lakatsiya yubor", "get_location", {}, "Typo: lakatsiya yubor"),
        ("qayerdam", "get_location", {}, "Tushgan harf: qayerdam"),
        ("klipbord korsat", "get_clipboard", {}, "Typo: klipbord korsat"),
        ("kammera och", "open_app", {"app_name": "camera"}, "Typo: kammera och"),

        # -------------------------------------------------------------
        # 3. Noto'g'ri, lekin kontekstdan tushunarli fe'llar
        # -------------------------------------------------------------
        ("fonarni yop", "set_torch", {"on": False}, "Kontekstli: fonarni yop -> off"),
        ("fonarni yopqoy", "set_torch", {"on": False}, "Kontekstli: fonarni yopqoy -> off"),
        ("chiroqni och", "set_torch", {"on": True}, "Kontekstli: chiroqni och -> on"),
        ("fonarni och", "set_torch", {"on": True}, "Kontekstli: fonarni och -> on"),
        ("chiroqni yop", "set_torch", {"on": False}, "Kontekstli: chiroqni yop -> off"),
        ("fonarni to'xtat", "set_torch", {"on": False}, "Kontekstli: fonarni to'xtat -> off"),

        # -------------------------------------------------------------
        # 4. Apostrof variantlari (o', o‘, oʻ, o`, o’, oʼ)
        # -------------------------------------------------------------
        ("fonarni o‘chir", "set_torch", {"on": False}, "Apostrof (left quote ‘): fonarni o‘chir"),
        ("fonarni oʻchir", "set_torch", {"on": False}, "Apostrof (modifier turned comma ʻ): fonarni oʻchir"),
        ("fonarni o`chir", "set_torch", {"on": False}, "Apostrof (grave accent `): fonarni o`chir"),
        ("fonarni o'chir", "set_torch", {"on": False}, "Apostrof (ascii '): fonarni o'chir"),
        ("fonarni o’chir", "set_torch", {"on": False}, "Apostrof (right quote ’): fonarni o’chir"),
        ("fonarni ochir", "set_torch", {"on": False}, "Apostrofsiz: fonarni ochir"),
        ("joylashuvimni ko‘rsat", "get_location", {}, "Apostrof: joylashuvimni ko‘rsat"),
        ("qo‘ng‘iroqlar tarixi", "get_call_log", {}, "Apostrof: qo‘ng‘iroqlar"),

        # -------------------------------------------------------------
        # 5. Kirillcha O'zbek buyruqlari
        # -------------------------------------------------------------
        ("фонарни ёқ", "set_torch", {"on": True}, "Kirill: фонарни ёқ"),
        ("фонарни ўчир", "set_torch", {"on": False}, "Kirill: фонарни ўчир"),
        ("чироқни ёқ", "set_torch", {"on": True}, "Kirill: чироқни ёқ"),
        ("чироқни ўчир", "set_torch", {"on": False}, "Kirill: чироқни ўчир"),
        ("батареям неча фоиз", "get_battery_status", {}, "Kirill: батареям неча фоиз"),
        ("телефонни 3 сония титрат", "vibrate_device", {"duration_ms": 3000}, "Kirill: телефонни 3 сония титрат"),
        ("расмга ол", "take_camera_photo", {}, "Kirill: расмга ол"),
        ("камерани оч", "open_app", {"app_name": "camera"}, "Kirill: камерани оч"),
        ("жойлашувимни кўрсат", "get_location", {}, "Kirill: жойлашувимни кўрсат"),
        ("мен қаердаман", "get_location", {}, "Kirill: мен қаердаман"),
        ("клипбордни кўрсат", "get_clipboard", {}, "Kirill: клипбордни кўрсат"),

        # -------------------------------------------------------------
        # 6. Sinonimlar
        # -------------------------------------------------------------
        ("chiroqni yoq", "set_torch", {"on": True}, "Sinonim: chiroqni yoq"),
        ("chiroqni o'chir", "set_torch", {"on": False}, "Sinonim: chiroqni o'chir"),
        ("zaryadim qancha", "get_battery_status", {}, "Sinonim: zaryadim qancha"),
        ("quvvat necha foiz", "get_battery_status", {}, "Sinonim: quvvat necha foiz"),
        ("suratga ol", "take_camera_photo", {}, "Sinonim: suratga ol"),
        ("foto ol", "take_camera_photo", {}, "Sinonim: foto ol"),
        ("lokatsiyamni yubor", "get_location", {}, "Sinonim: lokatsiyamni yubor"),
        ("buferni ko'rsat", "get_clipboard", {}, "Sinonim: buferni ko'rsat"),
        ("vatsapni och", "open_app", {"app_name": "whatsapp"}, "Sinonim: vatsapni och"),
        ("yutubni och", "open_app", {"app_name": "youtube"}, "Sinonim: yutubni och"),
        ("telegr och", "open_app", {"app_name": "telegram"}, "Sinonim: telegr och"),

        # -------------------------------------------------------------
        # 7. Inglizcha buyruqlar (Backward Compatibility)
        # -------------------------------------------------------------
        ("turn on flashlight", "set_torch", {"on": True}, "Inglizcha: turn on flashlight"),
        ("turn off flashlight", "set_torch", {"on": False}, "Inglizcha: turn off flashlight"),
        ("switch on flashlight", "set_torch", {"on": True}, "Inglizcha: switch on flashlight"),
        ("battery status", "get_battery_status", {}, "Inglizcha: battery status"),
        ("what is the battery status", "get_battery_status", {}, "Inglizcha: what is the battery status"),
        ("vibrate phone for 2 seconds", "vibrate_device", {"duration_ms": 2000}, "Inglizcha: vibrate phone for 2 seconds"),
        ("take a photo", "take_camera_photo", {}, "Inglizcha: take a photo"),
        ("open camera", "open_app", {"app_name": "camera"}, "Inglizcha: open camera"),
        ("where am i", "get_location", {}, "Inglizcha: where am i"),
        ("wi-fi info", "get_wifi_info", {}, "Inglizcha: wi-fi info"),
        ("open youtube", "open_app", {"app_name": "youtube"}, "Inglizcha: open youtube"),
    ]

    print("=" * 70)
    print(f"FUZZY COMMAND UNDERSTANDING TEST SUITE: {len(test_cases)} TESTS")
    print("=" * 70)

    passed = 0
    failed = 0

    for idx, (query, exp_tool, exp_args, label) in enumerate(test_cases, 1):
        res = uzbek_intent.match_intent(query)
        matched = res.get("matched", False)
        tool_name = res.get("tool_name")
        args = res.get("args", {})
        conf = res.get("confidence", 0.0)

        is_tool_ok = (tool_name == exp_tool)
        is_args_ok = True
        for k, v in exp_args.items():
            if k not in args or args[k] != v:
                is_args_ok = False
                break

        if matched and is_tool_ok and is_args_ok and conf >= 0.70:
            passed += 1
            print(f"[{idx:02d}] PASS ({conf:.2f}): '{query}' -> {tool_name}({args}) | {label}")
        else:
            failed += 1
            print(f"[{idx:02d}] FAIL ({conf:.2f}): '{query}' -> Expected: {exp_tool}({exp_args}), Got: {tool_name}({args}) | {label}")

    # -------------------------------------------------------------
    # 8. XAVFLI HARAKATLAR UCHUN TASDIQLASH (Confirmation Tests)
    # -------------------------------------------------------------
    print("\n" + "-" * 70)
    print("TESTING DANGEROUS ACTION CONFIRMATION FLOW:")
    print("-" * 70)

    dummy_tools = {
        "make_phone_call": lambda phone_number: f"Dialed {phone_number}",
        "send_sms": lambda recipient, message: f"Sent to {recipient}: {message}",
        "get_contacts": lambda: [{"name": "Ali", "number": "+998901234567"}]
    }

    # 1-qadam: Foydalanuvchi "Ali ga qongiroq qil" deb yozadi
    session_id = "test_user_session_1"
    res1 = uzbek_intent.process_agent_query(None, "Ali ga qongiroq qil", dummy_tools, session_id=session_id)
    print("Step 1 (Trigger call):", res1)
    assert res1.get("type") == "confirm", f"Expected type 'confirm', got {res1.get('type')}"
    assert res1.get("needs_confirmation") is True, "Expected needs_confirmation=True"

    # 2-qadam: Foydalanuvchi "ha" deb tasdiqlaydi
    res2 = uzbek_intent.process_agent_query(None, "ha", dummy_tools, session_id=session_id)
    print("Step 2 (Confirm 'ha'):", res2)
    assert res2.get("type") == "call", f"Expected type 'call' after confirmation, got {res2.get('type')}"
    assert "Dialed +998901234567" in res2.get("results", [])[0], f"Call not executed properly: {res2}"

    # Bekor qilish sinovi:
    session_id_2 = "test_user_session_2"
    res_c1 = uzbek_intent.process_agent_query(None, "Ali ga Salom deb sms yubor", dummy_tools, session_id=session_id_2)
    print("Step 3 (Trigger SMS):", res_c1)
    assert res_c1.get("type") == "confirm"

    res_c2 = uzbek_intent.process_agent_query(None, "yo'q", dummy_tools, session_id=session_id_2)
    print("Step 4 (Cancel 'yo\\'q'):", res_c2)
    assert "bekor qilindi" in res_c2.get("results", [])[0].lower()

    print("\n" + "=" * 70)
    print(f"OVERALL SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests.")
    print("CONFIRMATION WORKFLOW: VERIFIED 100% CORRECT.")
    print("=" * 70)

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(run_tests())
