"""HIKOYA 3 — Oxirgi dalil (detektiv, psixologik jumboq, tergov)."""

STYLE = (
    "cinematic realistic noir mystery, moody low-key lighting, deep blue and warm amber lamp glow, shallow depth of field, "
    "film grain, ultra detailed, 16:9 widescreen, no text, no watermark, no logo"
)

STORY = {
    "slug": "oxirgi-dalil",
    "title": "Oxirgi dalil",
    "genre": "Detektiv, psixologik jumboq, tergov",
    "synopsis": (
        "Mashhur olim professor Anvar Karimov kutilmaganda g‘oyib bo‘ladi. Laboratoriyada sirli belgilar, "
        "tugallanmagan xat va shubhali dalillar qolgan. Jamoa tergovchi rolida: ba’zi dalillar soxta, "
        "ba’zilari esa haqiqatga olib boradi."
    ),
    "theme": 2,
    "stages": [
        {
            "no": 1,
            "title": "Olimning yo‘qolishi",
            "body": (
                "Ertalab soat yettida telefon jiringladi. Ilmiy tadqiqotlar markazidan xabar: mashhur olim, professor Anvar "
                "Karimov kecha kechqurun laboratoriyadan chiqmagan, ertalab esa eshik ochiq, o‘zi yo‘q. Siz tergov guruhi "
                "sifatida voqea joyiga yetib keldingiz.\n\n"
                "Dahlizda soqchi Rahmat aka bezovta yurardi. Laboratoriya ichi g‘alati tartibda edi: stol ustidagi choy "
                "hali iliq, ammo olim izsiz yo‘qolgan. Hech narsa o‘g‘irlanmagan ko‘rinadi, bu esa vaziyatni yanada sirli qiladi."
            ),
            "bridge": "Har bir mayda narsa dalil bo‘lishi mumkin. Birinchi qadam — kuzatuvchanlik.",
            "visual": "Tong chog‘ida ilmiy markaz laboratoriyasi, ochiq eshik, stol ustida iliq choy va tergovchilar.",
            "prompt": (
                "Early morning at a scientific research lab, the door ajar, a cup of tea still steaming on a cluttered desk, "
                "a group of investigators in coats stepping inside, a worried night guard in the hallway, cold blue window light"
            ),
        },
        {
            "no": 2,
            "title": "Laboratoriyadagi birinchi dalil",
            "body": (
                "Siz laboratoriyani sinchiklab ko‘zdan kechirdingiz. Stol ostida sinib yotgan probirka, yerda yarim yongan "
                "daftar varag‘i, devordagi soat esa tunda soat 02:17 da to‘xtab qolgan.\n\n"
                "Daftar varag‘ida faqat bitta so‘z o‘qiladi: «Ular». Eng qiziq narsa — olimning yozuv stoli tortmasi yarim "
                "ochiq, ichi esa bo‘m-bo‘sh edi. Kimdir shosha-pisha nimanidir olib ketgan."
            ),
            "bridge": "Dalil topildi, ammo u nimani anglatadi? Fikrlash vaqti!",
            "visual": "Sinib yotgan probirka, yarim yongan daftar varag‘i, 02:17 da to‘xtagan devor soati va bo‘sh tortma.",
            "prompt": (
                "Close-up of a broken test tube on the floor, a half-burned notebook page with a single word, a wall clock "
                "stopped at 02:17, an open empty desk drawer, a detective's flashlight beam cutting through the dark lab"
            ),
        },
        {
            "no": 3,
            "title": "Shubhali xat",
            "body": (
                "Axlat savatidan g‘ijimlangan, tugallanmagan xat topildi. Qo‘lyozma olimniki ekani darhol bilinadi, lekin "
                "yozuv shoshilib yozilgan, oxirgi so‘z esa tomchi tushib ivib ketgan.\n\n"
                "Xatda shunday ma’no bor: «Aziz do‘stim, agar bu xatni o‘qisang, men... Hammasini yulduzlar yonida yashirdim. "
                "Ular bilmasligi kerak, aks holda...» Xat kimga atalgani ko‘rsatilmagan. Imzo o‘rnida faqat bitta harf — «A»."
            ),
            "bridge": "Xat sirli, lekin unda yashirin ishora bor. Uni topish uchun mantiqqa tayaning.",
            "visual": "G‘ijimlangan xat, ivib ketgan so‘nggi so‘z, lupa va stol chirog‘ining iliq yorug‘i.",
            "prompt": (
                "A crumpled handwritten letter flattened on a desk under a green banker's lamp, a magnifying glass over a "
                "smudged last line and a single initial signature, investigators' hands pointing at it, dramatic shadows"
            ),
        },
        {
            "no": 4,
            "title": "Yashirin xona",
            "body": (
                "Laboratoriya devori bo‘ylab kitob javonlari terilgan edi. Diqqat bilan qaraganingizda, bir javonning "
                "qirrasida yangi chizilgan izni payqadingiz: kimdir uni tez-tez surgan. Javonni surishingiz bilan devor "
                "ortida tor eshik paydo bo‘ldi.\n\n"
                "Ichkarida kichik, derazasiz xona bor edi: stolda o‘chiq lampa, devorda yulduzlar xaritasi va unda qizil "
                "qalamda aylana qilib belgilangan bitta nuqta."
            ),
            "bridge": "Yashirin xona yangi savollarni ochdi. Javob topa olasizmi?",
            "visual": "Surilgan kitob javoni ortidagi tor eshik, derazasiz xona va yulduzlar xaritasi.",
            "prompt": (
                "A heavy bookshelf swung open revealing a narrow hidden doorway, a tiny windowless room beyond with an old "
                "desk lamp and a star chart on the wall with a red circle on one point, dust in flashlight beams"
            ),
        },
        {
            "no": 5,
            "title": "Soxta dalil tuzog‘i",
            "body": (
                "Yashirin xonadan chiqayotganingizda stol ustida yangi ko‘rinishli sumka va uning ichida xatni payqadingiz: "
                "«Olimni laboratoriya yordamchisi Madina olib ketgan. Uni eski omborxonadan izlang». Hamma narsa juda "
                "ravshan tuyuldi... juda ravshan.\n\n"
                "DIQQAT! Bu soxta dalil bo‘lishi mumkin! Oldingizda yashirin tuzoq bor: noto‘g‘ri ishonch sizni yo‘ldan "
                "chalg‘itadi. Bu sinovdan o‘tish uchun jamoa birdamlik bilan fikr yuritishi kerak!"
            ),
            "bridge": "Haqiqatni soxtadan ajrating — xato qadam sizni orqaga qaytaradi!",
            "visual": "Stol ustidagi sumka va juda qulay topilgan xat, tergovchilar ikkilanib turibdi.",
            "trap": True,
            "prompt": (
                "A suspiciously neat leather bag with a conveniently placed note on a desk, investigators exchanging doubtful "
                "glances, a shadowy figure's silhouette reflected in a dark window, tense noir atmosphere"
            ),
        },
        {
            "no": 6,
            "title": "Guvohning sirli bayonoti",
            "body": (
                "Siz soqchi Rahmat akani so‘roq qildingiz. U qo‘llari titrab dedi: «Kecha soat ikkida laboratoriyadan baland "
                "ovozli tortishuv eshitdim. Eshikni ochmoqchi bo‘lgan edim, ichkaridan professorning o‘zi «Hammasi joyida, "
                "xavotir olmang» dedi. Faqat... ovoz biroz boshqacha edi».\n\n"
                "Rahmat aka yana bir narsani esladi: tun yarmida orqa eshikdan notanish kishi qora papka ko‘tarib "
                "chiqib ketgan. U vaqtni 02:40 deb aytdi, to‘xtab qolgan soat esa 02:17 ni ko‘rsatardi."
            ),
            "bridge": "Guvoh bayonoti dalillarga zid keladi. Qaysi biriga ishonish kerak?",
            "visual": "So‘roq xonasi, asabiylashgan soqchi, stol ustidagi diktofon va tergovchilarning diqqatli nigohi.",
            "prompt": (
                "A nervous night guard being questioned in a dim office, an old voice recorder on the table, detectives "
                "leaning in with notebooks, a wall clock behind them, harsh side lighting with deep shadows"
            ),
        },
        {
            "no": 7,
            "title": "Kodlangan kundalik",
            "body": (
                "Yashirin xonadagi tortmadan olimning qalin kundaligi topildi. Uning har bir sahifasi g‘alati belgilar va "
                "raqamlar bilan to‘ldirilgan: har harf o‘rniga boshqa harf, ba’zan raqam yozilgan. Faqat oxirgi sahifada "
                "oddiy qilib bir jumla yozilgan: «Kalit — o‘sha kuni birinchi o‘qigan she’rimning bosh harflari».\n\n"
                "Demak, kod bor va uni yechish mumkin. Agar buni uddalasangiz, olimning izidan borishingiz mumkin."
            ),
            "bridge": "Kodni yechish — haqiqatga eltuvchi yagona yo‘l!",
            "visual": "Kodlangan belgilarga to‘la qalin kundalik, qalam va ochiq lupa, stol chirog‘ining nuri.",
            "prompt": (
                "An open thick diary filled with cipher symbols and numbers under a desk lamp, a pencil and a decoder grid "
                "beside it, a magnifying glass, a detective's hand tapping the last page that has a single line of plain writing"
            ),
        },
        {
            "no": 8,
            "title": "Haqiqiy gumondorni aniqlash",
            "body": (
                "Kundalik yechilgach, hammasi o‘z o‘rniga tusha boshladi. Olim yangi energiya manbasi haqidagi kashfiyotni "
                "yashirgan, uni esa kimdir qo‘lga kiritmoqchi bo‘lgan. Kundalikda bitta ism qayta-qayta uchraydi: tadqiqot "
                "markazining eski hamkasbi, doktor Botir Nazarov. U olimga bir necha marta bosim o‘tkazgan, kashfiyotni "
                "«birgalikda» e’lon qilishni talab qilgan.\n\n"
                "Soxta dalil ham aynan unga foyda keltirardi: tergovni boshqa tomonga burib yuborardi. Endi sizda haqiqiy gumondor bor."
            ),
            "bridge": "Gumondor aniq, lekin yagona dalil hali yetishmayapti.",
            "visual": "Dalillar osilgan tergov devori, iplar bilan bog‘langan suratlar va markazdagi bitta ism.",
            "prompt": (
                "A detective evidence wall with photos, notes and red string connecting them, one photo of a man in a suit "
                "highlighted in the center, the team standing in front of it in half-light, moody noir lighting"
            ),
        },
        {
            "no": 9,
            "title": "Oxirgi dalilni topish",
            "body": (
                "Kundalikning oxirgi kodidan bitta manzil ochildi: «Eski rasadxona, yulduzlar yonida». Siz u yerga yetib "
                "borganingizda, eshik ichidan yopilgan edi. Eshik tagidan olimning qo‘l yozuvida bitta qog‘oz chiqarib "
                "qo‘yilgan: «Men faqat to‘g‘ri o‘ylagan kishiga ishonaman. Oxirgi dalilni topgan kishi eshikni ochadi».\n\n"
                "Professor o‘z ishiga faqat ishonchli odamlarni qo‘yardi. Endi oxirgi sinovdan o‘tish qoldi."
            ),
            "bridge": "Oxirgi dalil eshik ortida sizni kutmoqda.",
            "visual": "Tungi eski rasadxona, yopiq temir eshik va eshik tagidan chiqib turgan qog‘oz.",
            "prompt": (
                "An old observatory dome at night under a starry sky, a heavy locked iron door with a folded paper slid "
                "beneath it, the investigators approaching with flashlights, cold moonlight and fog"
            ),
        },
        {
            "no": 10,
            "title": "Haqiqat e’lon qilinadi",
            "body": (
                "Siz oxirgi sinovni bajardingiz va eshik ochildi. Ichkarida — qo‘lida qalin ko‘zoynak, charchagan, ammo tirik "
                "va sog‘ olim, professor Anvar Karimov turardi!\n\n"
                "U jilmayib dedi: «Men sizlarni kutgan edim. Faqat eng aqlli tergovchilar kundalikdagi kodni yecha olishiga ishongan edim»."
            ),
            "bridge": "",
            "visual": "Rasadxona ichida tirik va sog‘ olim, uning atrofida tergovchilar, gumbazdan tushayotgan yulduz nuri.",
            "prompt": (
                "Inside an old observatory dome, a tired but smiling elderly scientist with thick glasses greeting the "
                "investigators, a big brass telescope behind him, starlight pouring through the open dome slit, warm relief"
            ),
            "final": (
                "Olim hammasini tushuntirdi. Doktor Botir kashfiyotni o‘g‘irlamoqchi bo‘lgan, shuning uchun professor o‘z "
                "g‘oyib bo‘lishini sahnalashtirgan va soxta dalillar qoldirib, uning e’tiborini chalg‘itgan. Haqiqiy "
                "dalillarni esa faqat ishonchli tergovchilar topishi uchun yashirgan edi.\n\n"
                "Ertasi kuni doktor Botir qonun oldida javob berdi, kashfiyot esa xavfsiz holda ilm-fan xizmatiga topshirildi. "
                "Tergov yakunlandi: haqiqat e’lon qilindi."
            ),
        },
    ],
}
