import re
import time

from telegram import (ChatPermissions, InlineKeyboardButton,
                      InlineKeyboardMarkup, Update)
from telegram.ext import ContextTypes

from app import config, db
from app.handlers.ai_chat import handle_ai_question

URL_RE = re.compile(r"(https?://|www\.|t\.me/|@[\w_]{4,})", re.IGNORECASE)
DOMAIN_RE = re.compile(r"https?://([\w.-]+)", re.IGNORECASE)


# ---------- ورود/خروج اعضا ----------
async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    settings = db.get_chat(chat.id)
    for member in update.effective_message.new_chat_members:
        if member.is_bot:
            continue
        db.ensure_user(member.id, member.username)
        welcome = settings["welcome_text"] or "👋 {name} خوش آمدی به گروه!"
        await update.effective_message.reply_text(welcome.replace("{name}", member.full_name))

        # وریفای (پیش‌فرض خاموش)
        if settings["verify_enabled"]:
            await context.bot.restrict_chat_member(chat.id, member.id, ChatPermissions(can_send_messages=False))
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ من انسان هستم", callback_data=f"verify:{member.id}")]])
            await update.effective_message.reply_text(
                f"{member.full_name} برای ارسال پیام، تایید کن که ربات نیستی:", reply_markup=kb)


async def left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = db.get_chat(update.effective_chat.id)
    left = update.effective_message.left_chat_member
    if left and not left.is_bot:
        goodbye = settings["goodbye_text"] or "👋 {name} گروه را ترک کرد."
        await update.effective_message.reply_text(goodbye.replace("{name}", left.full_name))


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, _, uid = query.data.partition(":")
    if str(query.from_user.id) != uid:
        await query.answer("این دکمه برای تو نیست.", show_alert=True)
        return
    await context.bot.restrict_chat_member(
        query.message.chat.id, query.from_user.id,
        ChatPermissions(can_send_messages=True, can_send_other_messages=True,
                        can_send_polls=True, can_add_web_page_previews=True),
    )
    await query.answer("تایید شد ✅")
    await query.edit_message_text(f"✅ {query.from_user.full_name} تایید شد.")


async def set_welcome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.effective_message.text.partition(" ")[2].strip()
    db.update_chat(update.effective_chat.id, welcome_text=text)
    await update.effective_message.reply_text("✅ پیام خوش‌آمد ذخیره شد. (از {name} برای نام استفاده کن)")


async def set_goodbye_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.effective_message.text.partition(" ")[2].strip()
    db.update_chat(update.effective_chat.id, goodbye_text=text)
    await update.effective_message.reply_text("✅ پیام خداحافظی ذخیره شد.")


# ---------- پردازنده اصلی پیام‌های گروه ----------
async def group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.text:
        return
    chat = update.effective_chat
    user = update.effective_user
    settings = db.get_chat(chat.id)
    db.ensure_user(user.id, user.username)
    db.inc_msg_count(user.id)

    is_admin_user = (await context.bot.get_chat_member(chat.id, user.id)).status in ("administrator", "creator") \
        or user.id == config.OWNER_ID

    if not is_admin_user:
        # ۱) ضد اسپم
        if settings["antispam_enabled"] and await _is_spam(context, chat.id, user.id):
            try:
                await msg.delete()
            except Exception:
                pass
            return
        # ۲) فیلتر کلمات
        text_low = msg.text.lower()
        for w in db.list_filters(chat.id):
            if w in text_low:
                try:
                    await msg.delete()
                except Exception:
                    pass
                from app.handlers.moderation import enforce_warn
                count = await enforce_warn(context, chat.id, user.id, user.full_name, f"کلمه ممنوعه: {w}")
                if count < settings["warn_limit"]:
                    await context.bot.send_message(chat.id, f"⚠️ {user.full_name} کلمه ممنوعه فرستاد. وارن {count}/{settings['warn_limit']}")
                return
        # ۳) سیاست لینک
        if _violates_link_policy(settings, msg.text):
            try:
                await msg.delete()
            except Exception:
                pass
            await context.bot.send_message(chat.id, f"🔗 {user.full_name} ارسال لینک مجاز نیست.")
            return

    # ۴) تریگر هوش مصنوعی: با منشن ربات، یا ریپلای روی پیامِ خودِ ربات.
    # ریپلای روی پیام کاربرهای دیگر پاسخ AI نمی‌گیرد (تا توکن الکی مصرف نشود).
    bot_user = await context.bot.get_me()
    bot_username = bot_user.username
    mentioned = bool(bot_username) and f"@{bot_username}".lower() in msg.text.lower()
    is_reply_to_bot = bool(
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.id == bot_user.id
    )
    if mentioned or is_reply_to_bot:
        question = msg.text.replace(f"@{bot_username}", "").strip() if bot_username else msg.text.strip()
        if question:
            await handle_ai_question(update, context, question)


async def private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if msg and msg.text:
        await handle_ai_question(update, context, msg.text.strip())


# ---------- کمک‌کننده‌های ضداسپم/لینک ----------
async def _is_spam(context, chat_id, user_id):
    max_messages, window_seconds = db.get_antispam_rate()
    bucket = context.chat_data.setdefault("spam", {})
    now = time.time()
    times = [t for t in bucket.get(user_id, []) if now - t < window_seconds]
    times.append(now)
    bucket[user_id] = times
    return len(times) > max_messages


def _violates_link_policy(settings, text):
    if not URL_RE.search(text):
        return False
    policy = settings["link_policy"]
    if policy == "allow_all":
        return False
    if policy == "block_all":
        return True
    # whitelist
    import json
    allowed = json.loads(settings["link_whitelist"] or "[]")
    for domain in DOMAIN_RE.findall(text):
        if not any(domain.endswith(a) for a in allowed):
            return True
    return False