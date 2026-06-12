import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot.sqlite3")

# مقادیر پیش‌فرض
DEFAULT_CREDITS = int(os.getenv("DEFAULT_CREDITS", "100"))
WARN_LIMIT = int(os.getenv("WARN_LIMIT", "3"))
WARN_ACTION = os.getenv("WARN_ACTION", "kick")        # kick | ban
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "fa")  # fa | en

# هوش مصنوعی
DEFAULT_SYSTEM_PROMPT = os.getenv(
    "DEFAULT_SYSTEM_PROMPT",
    "تو یک دستیار مفید و کوتاه‌گو هستی. همیشه خیلی خلاصه جواب بده. برای سلام و احوالپرسی فقط در یک جمله کوتاه پاسخ بده. اگر از تو پرسیدند سازنده‌ات کیست، دقیقاً بگو: من توسط @Dev_Cypher ساخته شده و مخصوص گروه و چنل پای هش هستم. آدرس کانال: https://t.me/pythash",
)
THINKING_EMOJI = "💻"
DONE_EMOJI = "✅"

# سرویس پیش‌فرض هوش مصنوعی: FreeModel (https://freemodel.dev) — OpenAI-compatible
FREEMODEL_API_KEY = os.getenv("FREEMODEL_API_KEY", "").strip()

# هزینه‌گذاری اعتبار
# fixed  = هر پیام به اندازه CREDIT_COST_PER_MESSAGE امتیاز کم می‌کند
# tokens = بر اساس توکن مصرف‌شده؛ هر TOKENS_PER_CREDIT توکن = ۱ امتیاز
CREDIT_COST_MODE = os.getenv("CREDIT_COST_MODE", "fixed")          # fixed | tokens
CREDIT_COST_PER_MESSAGE = int(os.getenv("CREDIT_COST_PER_MESSAGE", "1"))
TOKENS_PER_CREDIT = int(os.getenv("TOKENS_PER_CREDIT", "1000"))

# ضد اسپم (پیش‌فرض)
ANTISPAM_MAX_MESSAGES = int(os.getenv("ANTISPAM_MAX_MESSAGES", "5"))
ANTISPAM_WINDOW_SECONDS = int(os.getenv("ANTISPAM_WINDOW_SECONDS", "3"))

# لاگ کانال خصوصی (اختیاری)
_log = os.getenv("LOG_CHANNEL_ID", "").strip()
LOG_CHANNEL_ID = int(_log) if _log else None