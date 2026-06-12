from telegram import Update
from telegram.ext import ContextTypes

from app import config, db
from app.ai_provider import call_ai
from app.permissions import is_owner

INSUFFICIENT = "❌ امتیاز شما کافی نیست. از ادمین اصلی درخواست کنید."
CREATOR_REPLY = "من توسط @Dev_Cypher ساخته شده و مخصوص گروه و چنل پای هش هستم.\nآدرس کانال: https://t.me/pythash"
CREATOR_KEYWORDS = (
    # فارسی — سازنده / برنامه‌نویس / طراح / خالق / صاحب / هویت
    "سازنده", "سازندت", "سازنده ات", "سازنده‌ات", "سازندتو",
    "کی ساختت", "کی ساختتت", "کی تورو ساخت", "کی تو رو ساخت",
    "تورو کی ساخت", "تو رو کی ساخت", "کی درستت کرد", "کی نوشتت",
    "کی کدتو", "کی کدت رو", "کیه که ساختت", "کی ساخته", "کی تورو ساخته",
    "برنامه نویس", "برنامه‌نویس", "برنامه نویست", "برنامه‌نویست", "کدنویس",
    "توسعه دهنده", "توسعه‌دهنده", "توسعه دهندت", "دولوپر",
    "طراح", "طراحت", "خالق", "خالقت", "صاحبت", "مالکت", "مال کیه", "متعلق به کی",
    "کی هستی", "تو کیه‌ی", "تو چی هستی", "چه رباتی هستی", "خودتو معرفی",
    # English
    "who made you", "who created you", "who built you", "who developed you",
    "who programmed you", "who coded you", "who designed you", "who wrote you",
    "who owns you", "your creator", "your developer", "your maker", "your owner",
    "who is your creator", "who is your developer", "what are you", "who are you",
    "introduce yourself", "creator", "developer", "made you",
)
GREETING_KEYWORDS = (
    "سلام", "سلامم", "درود", "hi", "hello", "hey"
)
GREETING_REPLY = "سلام داداش 🌹 چطور می‌تونم کمکت کنم؟"


async def handle_ai_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question: str):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    db.ensure_user(user.id, user.username)

    q = (question or "").strip().lower()
    if q in tuple(x.lower() for x in GREETING_KEYWORDS):
        await msg.reply_text(GREETING_REPLY)
        return
    if any(k in q for k in CREATOR_KEYWORDS):
        await msg.reply_text(CREATOR_REPLY, disable_web_page_preview=True)
        return

    if not db.get_chat(chat.id)["ai_enabled"]:
        await msg.reply_text("🤖 پاسخگویی هوشمند در این گروه خاموش است.")
        return

    # ۱) اولویت با FAQ (بدون کسر امتیاز)
    faq = db.find_faq(chat.id, question)
    if faq:
        await msg.reply_text(faq)
        return

    # ۲) بررسی اعتبار
    if not is_owner(user.id) and db.get_credits(user.id) <= 0:
        await msg.reply_text(INSUFFICIENT)
        return

    # ۳) بررسی وجود API فعال
    api = db.get_active_api()
    if not api:
        await msg.reply_text("⚠️ هیچ API فعالی تنظیم نشده. ادمین اصلی با /set_api و /activate_api تنظیم کند.")
        return

    # ۴) نمایش وضعیت در حال فکر کردن 💻
    status = await msg.reply_text(f"در حال فکر کردن {config.THINKING_EMOJI}...")
    system_prompt = db.get_setting("system_prompt", config.DEFAULT_SYSTEM_PROMPT)
    persona = db.get_personality()
    if persona:
        system_prompt = f"شخصیت و لحن تو: {persona}\n\n{system_prompt}"

    try:
        answer, tokens = await call_ai(api, system_prompt, question)
    except Exception as e:
        await status.edit_text(f"⚠️ خطا در ارتباط با API: {e}")
        return

    # ۵) محاسبه هزینه و کسر اعتبار (به‌جز ادمین اصلی)
    cost = db.compute_cost(tokens)
    if not is_owner(user.id):
        db.change_credits(user.id, -cost)
    remaining = db.get_credits(user.id)

    note = f"💳 امتیاز باقی‌مانده: {remaining} (هزینه این پیام: {cost}"
    note += f" | توکن: {tokens})" if tokens is not None else ")"
    await status.edit_text(f"{config.DONE_EMOJI} {answer}\n\n{note}")


async def credit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from app.handlers.common import resolve_target
    target_id, _ = await resolve_target(update, context)
    if target_id is None:
        target_id = update.effective_user.id
    await update.effective_message.reply_text(f"💳 امتیاز: {db.get_credits(target_id)}")


async def give_credit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _change_credit(update, context, sign=+1)


async def take_credit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _change_credit(update, context, sign=-1)


async def _change_credit(update, context, sign):
    from app.handlers.common import resolve_target
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی می‌تواند امتیاز را تغییر دهد.")
        return
    target_id, name = await resolve_target(update, context)
    amount = None
    for a in context.args:
        if a.lstrip("-").isdigit():
            amount = int(a)
    if target_id is None or amount is None:
        await update.effective_message.reply_text("فرمت: /give_credit @user 10  (یا روی پیام فرد ریپلای کن)")
        return
    new_val = db.change_credits(target_id, sign * abs(amount))
    db.log_action(update.effective_chat.id, update.effective_user.id,
                  "give_credit" if sign > 0 else "take_credit", target_id, {"amount": amount})
    await update.effective_message.reply_text(f"✅ امتیاز {name} اکنون: {new_val}")


async def set_prompt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    prompt = update.effective_message.text.partition(" ")[2].strip()
    if not prompt:
        await update.effective_message.reply_text(f"پرامپت فعلی:\n{db.get_setting('system_prompt', config.DEFAULT_SYSTEM_PROMPT)}")
        return
    db.set_setting("system_prompt", prompt)
    await update.effective_message.reply_text("✅ پرامپت سیستمی ذخیره شد.")


async def set_default_credits_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعیین اعتبار اولیه اعضای جدید (فقط ادمین اصلی)."""
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    if not context.args or not context.args[0].lstrip("-").isdigit():
        await update.effective_message.reply_text(
            f"اعتبار اولیه فعلی: {db.get_default_credits()}\nفرمت: /set_default_credits 100")
        return
    db.set_default_credits(int(context.args[0]))
    await update.effective_message.reply_text(f"✅ اعتبار اولیه اعضای جدید: {db.get_default_credits()}")


async def set_cost_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعیین هزینه هر پیام: ثابت یا بر اساس توکن (فقط ادمین اصلی)."""
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    args = context.args
    if not args:
        mode, per_msg, tpc = db.get_cost_config()
        await update.effective_message.reply_text(
            f"حالت هزینه: {mode}\nهزینه ثابت هر پیام: {per_msg}\nتوکن به ازای هر ۱ امتیاز: {tpc}\n\n"
            "نمونه‌ها:\n/set_cost fixed 1\n/set_cost tokens 1000")
        return
    mode = args[0].lower()
    if mode == "fixed" and len(args) >= 2 and args[1].isdigit():
        db.set_setting("cost_mode", "fixed")
        db.set_setting("cost_per_message", args[1])
        await update.effective_message.reply_text(f"✅ حالت ثابت: هر پیام {args[1]} امتیاز.")
    elif mode == "tokens" and len(args) >= 2 and args[1].isdigit():
        db.set_setting("cost_mode", "tokens")
        db.set_setting("tokens_per_credit", args[1])
        await update.effective_message.reply_text(f"✅ حالت توکنی: هر {args[1]} توکن = ۱ امتیاز.")
    else:
        await update.effective_message.reply_text("فرمت: /set_cost fixed <عدد>  یا  /set_cost tokens <عدد>")


async def set_personality_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شخصیت/لحن ربات را تعیین می‌کند (فقط ادمین اصلی). این متن به ابتدای پرامپت سیستمی اضافه می‌شود."""
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    text = update.effective_message.text.partition(" ")[2].strip()
    if not text:
        cur = db.get_personality()
        await update.effective_message.reply_text(
            ("شخصیت فعلی ربات:\n" + cur) if cur else
            "هنوز شخصیتی تنظیم نشده.\nمثال:\n/set_personality یک دوست خودمونی و شوخ که کوتاه و صمیمی جواب می‌ده.\nبرای پاک کردن: /set_personality off")
        return
    if text.lower() == "off":
        db.set_personality("")
        await update.effective_message.reply_text("✅ شخصیت ربات پاک شد (حالت پیش‌فرض).")
        return
    db.set_personality(text)
    await update.effective_message.reply_text("✅ شخصیت ربات ذخیره شد.")


async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # سوال از هوش مصنوعی با /ask — هم با نوشتن سوال بعد از دستور، هم با ریپلای روی هر پیام
    msg = update.effective_message
    question = msg.text.partition(" ")[2].strip()
    if not question and msg.reply_to_message and msg.reply_to_message.text:
        question = msg.reply_to_message.text.strip()
    if not question:
        await msg.reply_text("سوالت رو بعد از دستور بنویس یا روی یک پیام ریپلای کن.\nمثال:\n/ask پایتخت ایران کجاست؟")
        return
    await handle_ai_question(update, context, question)