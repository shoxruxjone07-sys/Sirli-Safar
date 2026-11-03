"""Admin parolidan bcrypt hash yaratadi (ADMIN_PASSWORD_HASH uchun).
Faqat `bcrypt` kutubxonasi kerak:  pip install bcrypt
Ishlatish (asosiy papkadan):       python scripts/make_password_hash.py
Yoki scripts papkasi ichidan:      python make_password_hash.py"""
import getpass
import sys

try:
    import bcrypt
except ImportError:
    sys.exit("bcrypt o‘rnatilmagan. Avval:  pip install bcrypt")

pw = getpass.getpass("Yangi admin paroli (yozganingiz ko‘rinmaydi): ")
if len(pw) < 8:
    sys.exit("Parol kamida 8 belgidan iborat bo‘lsin.")
if len(pw.encode("utf-8")) > 72:
    sys.exit("Parol juda uzun (bcrypt chegarasi 72 bayt). Qisqaroq parol tanlang.")
if pw != getpass.getpass("Parolni takrorlang: "):
    sys.exit("Parollar mos kelmadi. Qaytadan urinib ko‘ring.")
hashed = bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")
print("\nADMIN_PASSWORD_HASH qiymati (quyidagi qatorni to‘liq nusxalang):\n")
print(hashed)
