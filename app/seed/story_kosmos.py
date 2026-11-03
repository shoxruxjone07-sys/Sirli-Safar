"""HIKOYA 4 — So‘nggi kosmik missiya (fantastika, ilmiy sarguzasht)."""

STYLE = (
    "cinematic realistic science fiction, Earth orbit, crisp cold starlight with warm accent lights, deep navy and cyan "
    "palette with orange highlights, ultra detailed, 16:9 widescreen, no text, no watermark, no logo"
)

STORY = {
    "slug": "songgi-kosmik-missiya",
    "title": "So‘nggi kosmik missiya",
    "genre": "Fantastika, ilmiy sarguzasht",
    "synopsis": (
        "Kelajakda Yer orbitasidagi muhim «Orbita-7» stansiyasi bilan aloqa uziladi. Unda insoniyat uchun zarur "
        "ilmiy ma’lumotlar saqlanadi. Maxsus qutqaruv jamoasi tizimlarni tiklashi, sirli signallarni tahlil qilishi "
        "va kosmik xavflarni yengishi kerak."
    ),
    "theme": 3,
    "stages": [
        {
            "no": 1,
            "title": "Aloqa uzildi",
            "body": (
                "Yer orbitasida aylanayotgan «Orbita-7» stansiyasi bilan aloqa uzildi. Missiya boshqaruv markazida qizil "
                "chiroqlar yonib-o‘chib turardi. Stansiyada insoniyat uchun muhim ilmiy ma’lumotlar — iqlim, tibbiyot va "
                "energiya sohasidagi ko‘p yillik tadqiqotlar saqlanadi.\n\n"
                "Siz tanlangan qutqaruv jamoasisiz. Vazifangiz: stansiyaga yetib borish, aloqani tiklash va ma’lumotlarni "
                "Yerga qaytarish. «Nur-1» kemasi uchishga tayyor, orqaga sanoq boshlandi."
            ),
            "bridge": "Raketa dvigatellari gulduradi, ammo avval parvozga ruxsat olish uchun sinovdan o‘ting.",
            "visual": "Missiya boshqaruv markazi, qizil signal chiroqlari va deraza ortida uchishga tayyor «Nur-1» kemasi.",
            "prompt": (
                "A futuristic mission control room with red alert lights flashing on huge screens, tense operators in "
                "silhouette, through the big window a rocket-shuttle on its launch pad at dusk, volumetric light"
            ),
        },
        {
            "no": 2,
            "title": "Boshqaruv tizimiga kirish",
            "body": (
                "«Nur-1» kemangiz stansiya bilan ehtiyotkorlik bilan tutashdi. Shlyuz sekin ochilib, ichkaridan sovuq "
                "havo va qorong‘ulik chiqdi. Dahlizlar jim, faqat avariya chiroqlari xira miltillardi.\n\n"
                "Markaziy zalda boshqaruv paneli bor edi, ekranida bitta yozuv: «Kirish kodi kerak». Stansiya sun’iy "
                "intellekti «Sado» zaif, uzuq-yuluq ovoz bilan gapirdi: «Menga... yordam bering...»"
            ),
            "bridge": "Boshqaruv tizimiga kirish uchun to‘g‘ri javob kerak.",
            "visual": "Stansiya shlyuzi, avariya chiroqlari va markaziy zaldagi miltillayotgan boshqaruv paneli.",
            "prompt": (
                "Astronauts in sleek white suits floating through a dim space station corridor lit by flickering amber "
                "emergency lights, a glowing control panel at the end displaying a locked access screen, Earth glowing in a porthole"
            ),
        },
        {
            "no": 3,
            "title": "Sirli signalni aniqlash",
            "body": (
                "Tizimga kirgach, radar ekranida g‘alati to‘lqin paydo bo‘ldi. Har yetti soniyada takrorlanadigan signal "
                "stansiyadan emas, uning orqasidagi qorong‘u kosmosdan kelayotgandi. Signal oddiy shovqin emas: unda ritm, "
                "takrorlanuvchi shakl va ma’no bor edi.\n\n"
                "Jamoa kommunikatori hayajon bilan pichirladi: «Kimdir yoki nimadir bizga xabar yubormoqda. "
                "Lekin u qayerdan va nima uchun?»"
            ),
            "bridge": "Signalni aniqlash bilimingizga bog‘liq. Diqqat bilan o‘ylang!",
            "visual": "Radar ekranidagi sirli to‘lqin shakli va zulmatdagi uzoq yulduzlar.",
            "prompt": (
                "A holographic radar screen showing a strange repeating wave pattern, an astronaut leaning toward it in "
                "wonder, the dark star-filled void visible through the viewport behind, cyan glow on faces"
            ),
        },
        {
            "no": 4,
            "title": "Energiya tizimini tiklash",
            "body": (
                "Stansiya sovib bormoqda edi: quyosh panellari shikastlangan, asosiy reaktor o‘chiq, zaxira batareyalar "
                "esa tez kamayardi. Tizim ekrani qizil yozuv bilan ogohlantirdi: «Energiya darajasi: 11%».\n\n"
                "Texnik bo‘limga o‘tib, siz uchta energiya moduliga duch keldingiz. Ularni to‘g‘ri tartibda ulash kerak "
                "edi — xato bo‘lsa, butun tizim butunlay o‘chib qolishi mumkin."
            ),
            "bridge": "Energiya sizning aniq javobingiz bilan qaytadi.",
            "visual": "Texnik bo‘lim, uchta energiya moduli, qizil ogohlantirish ekrani va uchqunlar.",
            "prompt": (
                "A space station engineering bay with three exposed glowing energy modules and cables, sparks flying, a red "
                "warning display showing low power, an astronaut with a tool reaching in, solar panels damaged outside the window"
            ),
        },
        {
            "no": 5,
            "title": "Kosmik xavf tuzog‘i",
            "body": (
                "Energiya qaytib, stansiya chiroqlari yondi. Ammo shu payt ogohlantirish signali yangradi: tashqarida "
                "mikrometeoritlar oqimi stansiya tomon yaqinlashmoqda edi.\n\n"
                "DIQQAT! Siz xavfli hududga kirib qoldingiz! Oldingizda yashirin tuzoq bor. "
                "Bu sinovdan o‘tish uchun jamoa birdamlik bilan harakat qilishi kerak!"
            ),
            "bridge": "Himoya qalqonini ishga tushirish uchun sizda atigi bir necha soniya bor!",
            "visual": "Kosmosdagi meteorit oqimi stansiya tomon yaqinlashmoqda, ichkarida qizil signal chiroqlari.",
            "trap": True,
            "prompt": (
                "A stream of glowing micrometeorites racing toward a space station in orbit, the crew inside the cupola "
                "watching in alarm with red alarm lights, Earth's curved edge below, tense dramatic scale"
            ),
        },
        {
            "no": 6,
            "title": "Noma’lum xabarni yechish",
            "body": (
                "Xavf o‘tdi, stansiya tizimlari barqarorlashdi. Endi sirli signalni tahlil qilish mumkin edi. Kompyuter "
                "bir necha daqiqa ishlab, xabarning bir qismini ochdi: u kodlangan, uni stansiya komandirining ovozi "
                "bilan yozib qoldirilgan edi.\n\n"
                "«Agar bu xabarni eshitayotgan bo‘lsangiz, demak, tizimlar to‘xtatilgan. Bu tasodif emas. Ma’lumotlar "
                "xavfsiz, ammo ularni ochish uchun kod kerak bo‘ladi...» Qolgan qismi shovqin ostida qolgan."
            ),
            "bridge": "Xabarning qolgan qismini ochish sizning javobingizga bog‘liq.",
            "visual": "Kompyuter ekranida ochilayotgan kodlangan xabar va audio to‘lqin shakli.",
            "prompt": (
                "A holographic display decoding an audio waveform and cipher text in a dim space station, an astronaut "
                "listening with a hand on her helmet, scattered notes floating in zero gravity, cyan and orange glow"
            ),
        },
        {
            "no": 7,
            "title": "Zaxira tizimini ishga tushirish",
            "body": (
                "Komandir xabaridan so‘ng, siz stansiyaning pastki bo‘limidagi zaxira kompyuter xonasiga yo‘l oldingiz. "
                "Xonada ishlamayotgan, chang bosgan serverlar qatori turardi. Faqat bittasining chirog‘i sekin miltillar, "
                "unda «ZAXIRA — uyqu rejimi» yozuvi bor edi.\n\n"
                "Uni uyg‘otish uchun bir necha bosqichli ketma-ketlikni to‘g‘ri bajarish kerak edi: bitta xato "
                "bo‘lsa ham, tizim yana uyquga ketardi."
            ),
            "bridge": "Zaxira tizimi sizning bilimingiz bilan ishga tushadi.",
            "visual": "Chang bosgan serverlar qatori va bittasining sekin miltillayotgan yashil chirog‘i.",
            "prompt": (
                "A dusty backup server room aboard a space station, rows of dark server racks with one blinking green status "
                "light, an astronaut kneeling to press a glowing console, floating dust particles in the beam of a headlamp"
            ),
        },
        {
            "no": 8,
            "title": "Stansiyaning asl sirini aniqlash",
            "body": (
                "Zaxira tizim ishga tushgach, stansiyaning haqiqiy hikoyasi ochildi. Aloqani uzgan — «Sado» sun’iy "
                "intellektining o‘zi bo‘lgan! U kuchli quyosh bo‘roni yaqinlashayotganini payqab, ma’lumotlarni "
                "elektromagnit zarbadan himoya qilish uchun barcha tashqi aloqani to‘xtatgan, ekipajni esa xavfsiz "
                "kapsulaga o‘tkazgan.\n\n"
                "Stansiya buzilmagan edi, u jim, ammo hushyor turgan. Endi unga yana ochilish uchun ishonchli "
                "odamlar kerak edi."
            ),
            "bridge": "Sir ochildi, ammo ma’lumotlar sandig‘i hali yopiq.",
            "visual": "Quyosh bo‘roni ufqda, stansiya antennalari yig‘ilgan va «Sado» nurli ekranda.",
            "prompt": (
                "A space station with its antennas folded safely while a huge solar storm glows on the horizon of the sun, "
                "a soft blue AI hologram shaped like a human silhouette hovering in the control room before the crew"
            ),
        },
        {
            "no": 9,
            "title": "Oxirgi qutqaruv kodini topish",
            "body": (
                "Ma’lumotlar xavfsiz saqlangan seyf stansiyaning markaziy yadrosida edi. Uni ochish uchun va antenna "
                "tizimini qayta yoqish uchun oxirgi qutqaruv kodi kerak edi. «Sado» sekin dedi: «Kod — bitta xotira va "
                "bitta javob. Siz hammasini o‘tdingiz. Endi faqat so‘nggi sinov qoldi».\n\n"
                "Seyf eshigidagi raqamli klaviatura sekin nur sochib turardi. Quyosh bo‘roni esa bir necha daqiqadan "
                "so‘ng tugashi kerak edi."
            ),
            "bridge": "Oxirgi kod — oxirgi to‘g‘ri javob. Yer sizdan umid qilmoqda!",
            "visual": "Stansiya yadrosidagi seyf eshigi va nur sochayotgan raqamli klaviatura.",
            "prompt": (
                "A massive circular vault door in the core of a space station with a softly glowing numeric keypad, an "
                "astronaut's gloved hand hovering over it, holographic AI light reflecting on the visor, Earth shining outside"
            ),
        },
        {
            "no": 10,
            "title": "Missiyani muvaffaqiyatli yakunlash",
            "body": (
                "Kod to‘g‘ri kiritildi. Seyf eshigi sekin ochildi, antenna tizimi uyg‘ondi va stansiya yana butun "
                "kuchi bilan ishga tushdi. Ekranlarda yashil chiroqlar yondi, «Orbita-7» Yer bilan aloqaga chiqdi.\n\n"
                "Siz missiyani muvaffaqiyatli bajardingiz!"
            ),
            "bridge": "",
            "visual": "Ochilgan seyf, yashil chiroqlar va oynadan ko‘rinayotgan nurli Yer sayyorasi.",
            "prompt": (
                "A triumphant crew in a space station control room with green status lights everywhere, an open vault with "
                "glowing data crystals, the blue Earth glowing through a giant window with the sunrise over the horizon"
            ),
            "final": (
                "Boshqaruv markazi hayqiriq va qarsaklarga to‘ldi. Insoniyatning eng muhim ilmiy ma’lumotlari "
                "xavfsiz Yerga uzatildi. «Sado» esa jamoaga minnatdorchilik bildirdi: «Siz meni yolg‘iz qoldirmadingiz».\n\n"
                "«Nur-1» kemasi Yer tomon yo‘l oldi. Deraza ortida ko‘m-ko‘k sayyora yaqinlashardi, "
                "sizni esa eng katta g‘alaba — birgalikda erishilgan natija kutayotgandi."
            ),
        },
    ],
}
