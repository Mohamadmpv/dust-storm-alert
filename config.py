import os
from dotenv import load_dotenv

load_dotenv()

# ==================== توکن و Chat IDهای بله ====================
BALE_TOKEN = os.getenv("BALE_TOKEN")

# BALE_CHAT_ID دیگر استفاده نمی‌شود (همه از BALE_CHAT_IDS می‌آید)
BALE_CHAT_ID = ""

# Chat IDها با کاما از محیط خوانده می‌شوند
_env_chat_ids = os.getenv("BALE_CHAT_IDS", "")
if _env_chat_ids:
    BALE_CHAT_IDS = [cid.strip() for cid in _env_chat_ids.split(",") if cid.strip()]
else:
    BALE_CHAT_IDS = []

# ==================== آستانه‌ها ====================
WIND_SPEED_THRESHOLD = 20   # km/h
MIN_DIRECTION = 225
MAX_DIRECTION = 315

# ==================== نقاط بررسی ====================
SOURCE_POINTS = [
    # --- نقاط منشأ گرد و خاک خارجی ---
    {"name": "بغداد (عراق)",     "lat": 33.3152, "lon": 44.3661, "type": "external"},
    {"name": "دمشق (سوریه)",      "lat": 33.5138, "lon": 36.2765, "type": "external"},
    {"name": "تالاب هامون",       "lat": 31.0,    "lon": 61.5,    "type": "external"},
    {"name": "ترکمنستان",         "lat": 37.95,   "lon": 58.38,   "type": "external"},
    {"name": "صحرای عربستان",     "lat": 24.0,    "lon": 45.0,    "type": "external"},

    # --- دریاها ---
    {"name": "دریای خزر",         "lat": 40.0,    "lon": 51.0,    "type": "internal"},
    {"name": "خلیج فارس",         "lat": 27.0,    "lon": 51.0,    "type": "internal"},
    {"name": "دریای عمان",        "lat": 25.0,    "lon": 58.0,    "type": "internal"},

    # --- شهرها و بنادر ایران ---
    {"name": "تهران",             "lat": 35.6892, "lon": 51.3890, "type": "internal"},
    {"name": "تبریز",             "lat": 38.0800, "lon": 46.2919, "type": "internal"},
    {"name": "اهواز",             "lat": 31.3183, "lon": 48.6706, "type": "internal"},
    {"name": "اصفهان",            "lat": 32.6546, "lon": 51.6680, "type": "internal"},
    {"name": "بندرعباس",          "lat": 27.1832, "lon": 56.2666, "type": "internal"},
    {"name": "بوشهر",             "lat": 28.9234, "lon": 50.8200, "type": "internal"},
    {"name": "چابهار",            "lat": 25.2900, "lon": 60.6430, "type": "internal"},
    {"name": "بندر انزلی",         "lat": 37.4720, "lon": 49.4630, "type": "internal"},
]

# ==================== تنظیمات API ====================
FORECAST_DAYS = 2
API_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"