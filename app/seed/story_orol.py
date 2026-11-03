"""HIKOYA 1 — Yo‘qolgan orol siri (sarguzasht, sir, jumboq)."""

STYLE = (
    "cinematic realistic fantasy adventure, tropical island, dramatic golden-hour lighting, volumetric light, "
    "rich teal and amber color palette, ultra detailed, 16:9 widescreen, no text, no watermark, no logo"
)

STORY = {
    "slug": "yoqolgan-orol-siri",
    "title": "Yo‘qolgan orol siri",
    "genre": "Sarguzasht, sir, jumboq",
    "synopsis": (
        "Dengizdagi kuchli bo‘rondan so‘ng jamoa xaritalarda yo‘q sirli orolga kelib qoladi. "
        "Qirg‘oqdan topilgan qadimiy xarita orol markazidagi ming yillik xazinaga yo‘l ko‘rsatadi — "
        "ammo yo‘lda jungli, g‘orlar, yashirin eshiklar va xavfli tuzoqlar kutmoqda."
    ),
    "theme": 0,
    "stages": [
        {
            "no": 1,
            "title": "Sirli orol sohilida",
            "body": (
                "Tun bo‘yi dengiz g‘azab bilan bo‘kirdi. Yelkanli kemangiz to‘lqinlar changalida taxtadek uchib yurdi, "
                "so‘ng dahshatli zarba bilan qoyaga urildi. Ko‘zingizni ochganingizda quyosh balandlab qolgan, siz esa "
                "oppoq qumli sohilda yotardingiz. Atrofda kema qoldiqlari, bir-biriga suyanib turgan hamrohlaringiz... "
                "Kompasga qaradingiz — mili tinmay aylanardi. Xaritalardagi birorta orol bunday ko‘rinishda emas edi. "
                "Sohil ortidagi zich jungli ichidan esa qandaydir tosh minoraning uchi ko‘zga chalinardi.\n\n"
                "Bu orol sizni tasodifan kutib olmagan edi."
            ),
            "bridge": "Qum ustida sizdan boshqa birovning izlari ham bor... Orolning birinchi sinovi boshlanmoqda!",
            "visual": "Bo‘rondan keyingi tong: oppoq qumli sohil, kema parchalari, uzoqda jungli ichidan ko‘rinib turgan tosh minora.",
            "prompt": (
                "A shipwrecked group of travelers waking up on a pristine white-sand beach at dawn after a violent storm, "
                "broken wooden ship planks around them, a spinning brass compass in the sand, mysterious uncharted island "
                "with dense jungle behind them and a faint ancient stone tower rising above the trees, misty sea"
            ),
        },
        {
            "no": 2,
            "title": "Qadimiy xarita",
            "body": (
                "Kema qoldiqlari orasidan yaroqli narsalar izlab yurib, jamoadoshlaringizdan biri toshlar orasiga qistirilgan "
                "temir sandiqchani topdi. Zang bosgan qulf bir tegishda sinib tushdi. Ichida mumlangan mato o‘ramida eski "
                "xarita yotardi. Unda aynan siz turgan orolning shakli chizilgan, markazida esa qip-qizil X belgisi bor edi.\n\n"
                "Xarita chetida shoshib yozilgan so‘zlar: «Xazina yurak ostida. Yo‘lni faqat birdamlar topadi». "
                "Xaritaning bir burchagi yirtilgan, ammo asosiy yo‘l aniq ko‘rinardi: sohildan jungli, undan g‘or, "
                "so‘ng yerosti yo‘lagi orqali orol markaziga."
            ),
            "bridge": "Xarita qo‘lingizda. Endi undagi belgilarni tushunish uchun bilimingiz kerak bo‘ladi.",
            "visual": "Zang bosgan sandiqcha ichidan chiqqan eski xarita, markazda qizil X, chetida shoshilib yozilgan yozuv.",
            "prompt": (
                "Close-up of weathered hands unrolling an old treasure map on wet sand, a rusty open iron chest beside it, "
                "the map shows an island outline with a red X at its center and a torn corner, warm sunlight, "
                "sea foam and driftwood in the background"
            ),
        },
        {
            "no": 3,
            "title": "Jungli jumbog‘i",
            "body": (
                "Jungli sizni nam va issiq nafas bilan qarshi oldi. Qushlar tinimsiz sayrar, tepada maymunlar shox-shabbalarda "
                "sakrardi. Xarita ko‘rsatgan yo‘l bo‘ylab ketib, siz keng maydonchaga chiqdingiz. Maydon o‘rtasida moxlar bosgan "
                "tosh lavha turar, unga uchta hayvon — yaguar, to‘tiqush va ilon — o‘yib ishlangan edi.\n\n"
                "Lavha tagidagi yozuv shunday deydi: «Aql kalitni topadi, shoshqaloqlik esa yo‘lni yopadi». "
                "Oldinda esa yo‘lni tosh devor to‘sgan; u faqat jumboq yechilgandagina qimirlaydi."
            ),
            "bridge": "Jumboqni birgalikda yeching — devor ochilishi sizning javobingizga bog‘liq!",
            "visual": "Zich jungli ichidagi maydon, uchta hayvon o‘yilgan moxli tosh lavha va uning ortidagi tosh devor.",
            "prompt": (
                "A mossy ancient stone tablet carved with a jaguar, a parrot and a snake in a sunlit jungle clearing, "
                "a huge vine-covered stone wall blocking the path behind it, shafts of light through giant trees, "
                "tropical birds, explorers silhouetted in the foreground"
            ),
        },
        {
            "no": 4,
            "title": "Yashirin g‘or eshigi",
            "body": (
                "Devor ortida yo‘l tobora tikkalashib bordi va birdan quloqni kar qiluvchi shovqin eshitildi: oldinda baland "
                "sharshara guldirab oqardi. Xaritada aynan shu yerda g‘or borligi belgilangan, ammo kirish ko‘rinmasdi.\n\n"
                "Sharshara yoniga yaqinlashganingizda suv ortida nimadir yaltirab ketdi. Oqim pardasi ortida tosh eshik turar, "
                "uning o‘rtasida quyosh timsoli o‘yilgan, atrofida esa kichik teshiklar bor edi. Eshikda hech qanday tutqich yo‘q: "
                "uni faqat to‘g‘ri tartib bilan ochish mumkin."
            ),
            "bridge": "Sharshara ortidagi eshik sirini ochish uchun navbatdagi sinovdan o‘ting.",
            "visual": "Baland sharshara pardasi ortida quyosh timsolli tosh eshik, atrofda tuman va yorug‘lik nurlari.",
            "prompt": (
                "A hidden carved stone door with a sun emblem behind a thundering jungle waterfall, glowing small holes "
                "around the emblem, mist and rainbow light, wet mossy rocks, adventurers approaching along slippery stones"
            ),
        },
        {
            "no": 5,
            "title": "Xavfli tuzoq",
            "body": (
                "G‘orning birinchi zalida havo sovuq va qimirsiz edi. Birdan oyog‘ingiz ostidagi tosh plita sal pastga botdi — "
                "va shu zahoti devorlar ichida qadimiy mexanizmlar g‘ichirlay boshladi.\n\n"
                "DIQQAT! Siz xavfli hududga kirib qoldingiz! Oldingizda yashirin tuzoq bor. "
                "Bu sinovdan o‘tish uchun jamoa birdamlik bilan harakat qilishi kerak!"
            ),
            "bridge": "Har bir soniya qimmat — jamoa bo‘lib to‘g‘ri qaror toping!",
            "visual": "Qorong‘i g‘or zali, botib ketgan tosh plita, devorlardagi yashirin teshiklar va xavf tuyg‘usi.",
            "trap": True,
            "prompt": (
                "A dark ancient cave chamber with a pressure plate sinking under an explorer's boot, hidden dart holes "
                "and rusty mechanisms awakening in the stone walls, tense torchlight, dust in the air, "
                "the team frozen in alarm"
            ),
        },
        {
            "no": 6,
            "title": "Qadimiy yozuvni o‘qish",
            "body": (
                "Tuzoqdan omon chiqqach, mash’alingiz yorug‘ida g‘orning keyingi zali ochildi. Devorlar bo‘ylab oltin rangda "
                "yarqiragan qadimiy belgilar tizilgan, ularning ba’zilari yemirilib ketgan. Yozuvlar orolning tarixini "
                "aytib turganday edi: bir paytlar bu yerda dengizchi donishmandlar yashagan va xazinasini faqat bilimdonlarga "
                "qoldirgan.\n\n"
                "Yozuv ostidagi oxirgi satr yarim yo‘lda uzilgan — uni faqat o‘qib, to‘g‘ri tushungan kishi davom ettira oladi."
            ),
            "bridge": "Yozuvning siri sizning bilimingizda — o‘qing va javob bering!",
            "visual": "G‘or devorida oltin rangda porlayotgan qadimiy belgilar va mash’al yorug‘i.",
            "prompt": (
                "A vast cave wall covered with glowing golden ancient glyphs, a torch held up by an explorer reading them, "
                "some symbols eroded, a last unfinished line of inscription, warm firelight against cool blue stone"
            ),
        },
        {
            "no": 7,
            "title": "Yerosti yo‘lagi",
            "body": (
                "Yozuv to‘g‘ri o‘qilgach, devor ichidan toshlar bir-biriga ishqalanib, tor yo‘lak ochildi. Yo‘lak tubsiz "
                "zulmatga ketar, ichkaridan sovuq shamol esardi. Bir necha qadamdan keyin yo‘l uchga ajraldi: biri pastga, "
                "biri o‘ngga, uchinchisi esa suv ostidan o‘tardi.\n\n"
                "Xaritada faqat bittasi to‘g‘ri yo‘l. Qolganlari zulmatda adashtirib, sizni boshlang‘ich nuqtaga qaytarishi mumkin."
            ),
            "bridge": "Yo‘lni to‘g‘ri tanlash uchun aql va diqqat kerak.",
            "visual": "Yerosti yo‘lagi uchga ajralgan joy, mash’allar, qalqib yurgan ko‘rshapalaklar va suv yo‘li.",
            "prompt": (
                "An underground tunnel splitting into three paths, one descending stairs, one narrow corridor, one flooded "
                "channel, flickering torches on the walls, bats overhead, mysterious fog, explorers deciding which way to go"
            ),
        },
        {
            "no": 8,
            "title": "Xazina qo‘riqchisining sinovi",
            "body": (
                "Yo‘lak oxirida ulkan tosh zal ochildi. Zal o‘rtasida yigirma qadam balandlikdagi tosh haykal turardi: u "
                "ming yillar avval xazinani qo‘riqlash uchun yaratilgan Qo‘riqchi edi. Siz yaqinlashganingizda uning ko‘zlari "
                "qizil nur sochib yondi, tosh qovoqlari ochildi va zal bo‘ylab bo‘g‘iq ovoz yangradi:\n\n"
                "«Kim xazinaga intilsa, avval menga o‘zini isbotlasin!»\n\n"
                "Qo‘riqchi yo‘lni to‘sib turardi."
            ),
            "bridge": "Qo‘riqchining savoliga to‘g‘ri javob bergan kishigina o‘tadi!",
            "visual": "Ulkan tosh qo‘riqchi haykali, qizil nur sochayotgan ko‘zlari va uning oldida kichik jamoa.",
            "prompt": (
                "A colossal ancient stone guardian statue awakening in a huge cavern hall, glowing red eyes, cracked stone "
                "eyelids opening, tiny explorers standing before it holding torches, god rays through a ceiling opening, epic scale"
            ),
        },
        {
            "no": 9,
            "title": "So‘nggi sirli kalit",
            "body": (
                "Qo‘riqchi tosh yelkasini cho‘ktirib, yo‘l berdi. Zal ortida kichik xona bor edi: devorda quyosh shaklidagi "
                "tuynuk, uning ostida esa bo‘sh tosh quti. Xaritaning yirtilgan burchagi — endi tushundingiz — aynan shu "
                "yerga ishora qilgan edi.\n\n"
                "Qutini ochish uchun «So‘nggi kalit» kerak, uni esa faqat xona sirlarini yechgan kishi topadi. Tomdan "
                "ingichka yorug‘lik tushib turar, u kalit yashirin joyni ko‘rsatayotganday edi."
            ),
            "bridge": "Oxirgi qadam — kalitni topish. To‘xtamang!",
            "visual": "Kichik tosh xona, tomdan tushayotgan ingichka nur, bo‘sh tosh quti va devordagi quyosh tuynugi.",
            "prompt": (
                "A small hidden stone chamber with a single beam of sunlight falling from a sun-shaped hole onto an empty "
                "carved stone box, a glimmering ancient bronze key half hidden in a crack of the wall, dust motes in the light"
            ),
        },
        {
            "no": 10,
            "title": "Xazina xonasi",
            "body": (
                "Kalit qulfga tushdi va tosh eshik sekin ochildi. Ko‘z oldingizda ulkan xona yarqirab ketdi: shift teshigidan "
                "tushgan quyosh nuri oltin tangalar, qimmatbaho toshlar va qadimiy kitoblar uyumini yoritib turardi.\n\n"
                "Siz bu yerga yetib keldingiz!"
            ),
            "bridge": "",
            "visual": "Quyosh nuri bilan yoritilgan xazina xonasi: oltin tangalar, qimmatbaho toshlar, qadimiy kitoblar va sandiq.",
            "prompt": (
                "A magnificent treasure chamber flooded with golden sunlight from a ceiling opening, heaps of gold coins, "
                "jewels and ancient books, a large ornate chest in the center, triumphant explorers silhouetted at the "
                "entrance, sparkling dust in the air"
            ),
            "final": (
                "Xonaning o‘rtasida katta sandiq turardi. Uni ochganingizda ichida oltin bilan birga yana bir yozuv chiqdi: "
                "«Eng katta xazina — birga yo‘l bosgan do‘stlik».\n\n"
                "Tushundingiz: orol xazinasi bilim va birdamlikni qadrlaydiganlar uchun saqlangan ekan. Ertasi tongda dengiz "
                "sokinlashdi, kemangiz ta’mirlandi va siz oltin hamda yangi tajriba bilan uyga qaytdingiz. "
                "Sirli orol esa yana tuman ortida g‘oyib bo‘ldi — keyingi jasur sayohatchilarni kutib."
            ),
        },
    ],
}
