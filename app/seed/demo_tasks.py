"""Demo topshiriqlar: bot birinchi ishga tushganda o‘yinni darhol sinab ko‘rish uchun.
O‘qituvchi o‘z fani bo‘yicha topshiriqlarni admin panel orqali qo‘shadi; demolarni o‘chirish mumkin."""


def _t(stage, question, options, correct, sec=45):
    return {"stage_no": stage, "kind": "test", "question": question, "options": options,
            "correct_option": correct, "time_limit_sec": sec}


DEMO_TASKS = [
    _t(1, "Alisher Navoiy qaysi asrda yashagan?", ["XIII asr", "XV asr", "XVII asr", "XIX asr"], 1),
    _t(1, "Alisher Navoiyning «Xamsa»si nechta dostondan iborat?", ["3 ta", "4 ta", "5 ta", "7 ta"], 2),
    _t(2, "O‘zbek tilida nechta kelishik bor?", ["4 ta", "5 ta", "6 ta", "7 ta"], 2),
    _t(2, "«O‘tkan kunlar» romanining muallifi kim?", ["Cho‘lpon", "Abdulla Qodiriy", "Oybek", "G‘afur G‘ulom"], 1),
    _t(3, "Ot so‘z turkumi qaysi so‘roqlarga javob bo‘ladi?", ["qanday?", "nima qildi?", "kim? nima?", "nechta?"], 2),
    _t(3, "«Boburnoma» asarining muallifi kim?", ["Zahiriddin Muhammad Bobur", "Alisher Navoiy",
                                               "Mirzo Ulug‘bek", "Ahmad Yassaviy"], 0),
    _t(4, "Sifat so‘z turkumi qaysi so‘roqqa javob bo‘ladi?", ["kim?", "qanday?", "nima qildi?", "qancha?"], 1),
    _t(4, "«Kecha va kunduz» romanining muallifi kim?", ["Cho‘lpon", "Abdulla Qahhor", "Hamza", "Erkin Vohidov"], 0),
    _t(5, "«Mehrobdan chayon» romanining muallifi kim?", ["Abdulla Qodiriy", "Oybek", "Said Ahmad", "Pirimqul Qodirov"], 0),
    _t(5, "Fe’l so‘z turkumi qaysi so‘roqqa javob bo‘ladi?", ["nima qildi?", "kim?", "qanday?", "necha?"], 0),
    _t(6, "«Chiroyli» so‘ziga ma’nodosh (sinonim) so‘z qaysi?", ["xunuk", "go‘zal", "baland", "katta"], 1),
    _t(6, "«Yuz» so‘zi qaysi tushunchaga misol bo‘ladi (bir xil yoziladi, ma’nosi har xil)?",
       ["Sinonim", "Antonim", "Omonim", "Paronim"], 2),
    _t(7, "«Baland» so‘ziga qarama-qarshi ma’noli (antonim) so‘z qaysi?", ["past", "uzun", "keng", "yaqin"], 0),
    _t(7, "O‘zbek tilidagi unli tovushlar soni nechta?", ["4 ta", "5 ta", "6 ta", "8 ta"], 2),
    _t(8, "Gapning asosiy bo‘laklari qaysilar?", ["Aniqlovchi va hol", "Ega va kesim",
                                                  "To‘ldiruvchi va hol", "Ega va to‘ldiruvchi"], 1),
    _t(8, "Gapda ish-harakat yoki holatni bildirib, ega haqida xabar beruvchi bo‘lak qaysi?",
       ["Ega", "Kesim", "Aniqlovchi", "Hol"], 1, 60),
    _t(9, "«Tut» (daraxt) va «tut» (ushla) so‘zlari qanday so‘zlar?", ["Omonim", "Sinonim", "Antonim", "Termin"], 0),
    _t(9, "«Ona tili» fanida so‘zlarning ma’nosini o‘rganuvchi bo‘lim nima deyiladi?",
       ["Fonetika", "Leksikologiya", "Morfologiya", "Sintaksis"], 1),
    # Matnli / ijodiy / individual namunalar
    {"stage_no": 2, "kind": "text", "question": "«Ilm — hayot chirog‘i» mavzusida bitta gap tuzing.",
     "time_limit_sec": 90},
    {"stage_no": 4, "kind": "creative", "question": "Sarguzashtingiz uchun 2 gapdan iborat qisqa shior toping.",
     "time_limit_sec": 120},
    {"stage_no": 6, "kind": "text", "question": "Bitta o‘zbek maqolini yozing va ma’nosini bir gapda izohlang.",
     "time_limit_sec": 120},
    {"stage_no": 8, "kind": "creative", "question": "Jamoa tanlagan so‘zdan foydalanib 3 gapli mini-hikoya yozing.",
     "time_limit_sec": 180},
    {"stage_no": 1, "kind": "individual", "question": "Ona tilimizning qaysi harflari «o‘», «g‘», «sh», «ch» ko‘rinishida yoziladi?",
     "options": ["Ular yozuvda umuman ishlatilmaydi", "Bitta tovushni ifodalovchi harf birikmalari yoki belgilar",
                 "Faqat xorijiy so‘zlarda uchraydi"], "correct_option": 1, "time_limit_sec": 60},
    {"stage_no": 3, "kind": "individual", "question": "Sizningcha, nega kitob o‘qish nutqni boyitadi? Qisqa yozing.",
     "time_limit_sec": 120},
    {"stage_no": 5, "kind": "individual", "question": "Navoiyning bitta g‘azalidan bayt yoki bayt mazmunini yozing.",
     "time_limit_sec": 150},
    {"stage_no": 7, "kind": "individual", "question": "«Kitob» so‘zining 3 ta ma’nodoshi yoki yaqin ma’noli so‘zini yozing.",
     "time_limit_sec": 90},
    {"stage_no": 9, "kind": "individual", "question": "Hozirgi darsdan o‘rgangan eng muhim narsangizni bir gapda yozing.",
     "time_limit_sec": 120},
]

DEMO_TRAPS = [
    {"stage_no": 5, "prompt": "Tuzoq! Jamoa 3 ta o‘zbek maqolini aytsin va hech biri takrorlanmasin.",
     "time_limit_sec": 120},
    {"stage_no": 5, "prompt": "Tuzoq! «Ilm» so‘ziga 4 ta ma’nodosh so‘z yoki so‘z birikmasi topib yozing.",
     "time_limit_sec": 120},
    {"stage_no": 5, "prompt": "Tuzoq! Jamoa bitta zanjirli gap tuzsin: har bir yangi so‘z oldingi so‘zning "
                              "oxirgi harfidan boshlansin (kamida 6 so‘z).", "time_limit_sec": 150},
]
