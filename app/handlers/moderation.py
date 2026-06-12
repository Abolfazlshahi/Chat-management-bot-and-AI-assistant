import time

from telegram import ChatPermissions, Update
from telegram.ext import ContextTypes

from app import config, db
from app.permissions import is_admin
from app.handlers.common import resolve_target, parse_duration, notify_log

MUTED = ChatPermissions(can_send_messages=False)
UNMUTED = ChatPermissions(
    can_send_messages=True, can_send_polls=True, can_send_other_messages=True,
    can_add_web_page_previews=True, can_invite_users=True,
)


async def _require_admin(update, context):
    if not await is_admin(update, context):
        await update.effective_message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.")
        return False
    return True


async def _reject_if_target_is_admin(update, context, target_id):
    if target_id == config.OWNER_ID:
        await update.effective_message.reply_text("شرمندم داداچ ایشون ادمینه!")
        return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, target_id)
        if member.status in ("administrator", "creator"):
            await update.effective_message.reply_text("شرمندم داداچ ایشون ادمینه!")
            return True
    except Exception:
        pass
    return False


async def enforce_warn(context, chat_id, target_id, name, reason, actor_id=None):
    """یک وارن ثبت می‌کند و اگر به سقف رسید، طبق تنظیم گروه کیک/بن می‌کند. شمارهٔ وارن را برمی‌گرداند."""
    count = db.add_warning(chat_id, target_id, reason)
    settings = db.get_chat(chat_id)
    limit = settings["warn_limit"]
    action = settings["warn_action"]
    if actor_id is not None:
        db.log_action(chat_id, actor_id, "warn", target_id, {"count": count})
    if count >= limit:
        try:
            if action == "ban":
                await context.bot.ban_chat_member(chat_id, target_id)
                verb = "بن شد"
            else:
                # kick = ban سپس unban فوری
                await context.bot.ban_chat_member(chat_id, target_id)
                await context.bot.unban_chat_member(chat_id, target_id)
                verb = "اخراج شد"
            db.reset_warning(chat_id, target_id)
            await context.bot.send_message(chat_id, f"🚫 {name} به دلیل رسیدن به {limit} وارن {verb}.")
        except Exception as e:
            await context.bot.send_message(
                chat_id,
                f"⚠️ {name} به سقف {limit} وارن رسید ولی نشد اعمالش کنم: {e}\n"
                "ربات باید ادمین باشد و دسترسی «بن/اخراج کاربر» داشته باشد.")
    return count


async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    chat = update.effective_chat
    target_id, name = await resolve_target(update, context)
    if target_id is None:
        await update.effective_message.reply_text("روی پیام فرد ریپلای کن یا آی‌دی بده.")
        return
    if await _reject_if_target_is_admin(update, context, target_id):
        return
    reason = " ".join(a for a in context.args if not a.lstrip('-').isdigit()) or "بدون دلیل"
    count = await enforce_warn(context, chat.id, target_id, name, reason, actor_id=update.effective_user.id)
    limit = db.get_chat(chat.id)["warn_limit"]
    if count < limit:
        await update.effective_message.reply_text(f"⚠️ وارن {count}/{limit} برای {name}. دلیل: {reason}")


async def unwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    target_id, name = await resolve_target(update, context)
    if target_id is None:
        await update.effective_message.reply_text("روی پیام فرد ریپلای کن.")
        return
    db.reset_warning(update.effective_chat.id, target_id)
    await update.effective_message.reply_text(f"✅ وارن‌های {name} پاک شد.")


async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    target_id, name = await resolve_target(update, context)
    if target_id is None:
        return await update.effective_message.reply_text("هدف مشخص نیست.")
    if await _reject_if_target_is_admin(update, context, target_id):
        return
    await context.bot.ban_chat_member(update.effective_chat.id, target_id)
    db.log_action(update.effective_chat.id, update.effective_user.id, "ban", target_id)
    await update.effective_message.reply_text(f"🚫 {name} بن شد.")


async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    target_id, name = await resolve_target(update, context)
    if target_id is None:
        return await update.effective_message.reply_text("هدف مشخص نیست.")
    await context.bot.unban_chat_member(update.effective_chat.id, target_id)
    await update.effective_message.reply_text(f"✅ {name} آنبن شد.")


async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    target_id, name = await resolve_target(update, context)
    if target_id is None:
        return await update.effective_message.reply_text("هدف مشخص نیست.")
    if await _reject_if_target_is_admin(update, context, target_id):
        return
    await context.bot.ban_chat_member(update.effective_chat.id, target_id)
    await context.bot.unban_chat_member(update.effective_chat.id, target_id)
    await update.effective_message.reply_text(f"👢 {name} اخراج شد.")


async def del_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # حذف هر پیامی (حتی پیام ادمین‌ها) با ریپلای روی آن و زدن /del
    if not await _require_admin(update, context):
        return
    msg = update.effective_message
    if not msg.reply_to_message:
        return await msg.reply_text("روی پیامی که می‌خوای پاک بشه ریپلای کن، بعد /del بزن.")
    try:
        await context.bot.delete_message(update.effective_chat.id, msg.reply_to_message.message_id)
        await msg.delete()
    except Exception as e:
        await msg.reply_text(
            f"نشد پاکش کنم: {e}\nمطمئن شو ربات ادمینه و دسترسی «حذف پیام‌ها» را دارد.")


async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    target_id, name = await resolve_target(update, context)
    if target_id is None:
        return await update.effective_message.reply_text("هدف مشخص نیست.")
    if await _reject_if_target_is_admin(update, context, target_id):
        return
    until = None
    for a in context.args:
        secs = parse_duration(a)
        if secs:
            until = int(time.time()) + secs
    await context.bot.restrict_chat_member(update.effective_chat.id, target_id, MUTED, until_date=until)
    await update.effective_message.reply_text(f"🔇 {name} سایلنس شد." + (" (موقت)" if until else ""))


async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    target_id, name = await resolve_target(update, context)
    if target_id is None:
        return await update.effective_message.reply_text("هدف مشخص نیست.")
    if await _reject_if_target_is_admin(update, context, target_id):
        return
    await context.bot.restrict_chat_member(update.effective_chat.id, target_id, UNMUTED)
    await update.effective_message.reply_text(f"🔊 {name} آنسایلنس شد.")


async def purge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    n = int(context.args[0]) if context.args and context.args[0].isdigit() else 10
    n = min(n, 100)
    last_id = update.effective_message.message_id
    deleted = 0
    for mid in range(last_id, last_id - n - 1, -1):
        try:
            await context.bot.delete_message(update.effective_chat.id, mid)
            deleted += 1
        except Exception:
            pass
    await context.bot.send_message(update.effective_chat.id, f"🧹 {deleted} پیام حذف شد.")


async def pin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    if update.effective_message.reply_to_message:
        await context.bot.pin_chat_message(update.effective_chat.id,
                                            update.effective_message.reply_to_message.message_id)
        await update.effective_message.reply_text("📌 پین شد.")
    else:
        await update.effective_message.reply_text("روی پیام موردنظر ریپلای کن.")


async def unpin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    await context.bot.unpin_chat_message(update.effective_chat.id)
    await update.effective_message.reply_text("📍 آنپین شد.")


async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    db.update_chat(update.effective_chat.id, lock_enabled=1)
    await context.bot.set_chat_permissions(update.effective_chat.id, MUTED)
    await update.effective_message.reply_text("🔒 گروه قفل شد (فقط ادمین‌ها).")


async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    db.update_chat(update.effective_chat.id, lock_enabled=0)
    await context.bot.set_chat_permissions(update.effective_chat.id, UNMUTED)
    await update.effective_message.reply_text("🔓 قفل گروه باز شد.")


# ---------- فیلتر کلمات ----------
async def add_filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    if not context.args:
        return await update.effective_message.reply_text("فرمت: /add_filter کلمه")
    for w in context.args:
        db.add_filter(update.effective_chat.id, w)
    await update.effective_message.reply_text("✅ به فیلتر اضافه شد.")


async def remove_filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    if not context.args:
        return await update.effective_message.reply_text("فرمت: /remove_filter کلمه")
    for w in context.args:
        db.remove_filter(update.effective_chat.id, w)
    await update.effective_message.reply_text("✅ حذف شد.")


async def list_filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    words = db.list_filters(update.effective_chat.id)
    await update.effective_message.reply_text("🚫 کلمات فیلترشده:\n" + (", ".join(words) or "خالی"))


# ---------- لینک‌ها ----------
async def link_mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    if not context.args or context.args[0] not in ("block_all", "allow_all", "whitelist"):
        return await update.effective_message.reply_text("فرمت: /link_mode block_all|allow_all|whitelist")
    db.update_chat(update.effective_chat.id, link_policy=context.args[0])
    await update.effective_message.reply_text(f"✅ سیاست لینک: {context.args[0]}")


async def whitelist_domain_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    chat_id = update.effective_chat.id
    if not context.args:
        return await update.effective_message.reply_text("فرمت: /whitelist_domain add|remove|list [domain]")
    action = context.args[0]
    domains = db.get_whitelist(chat_id)
    if action == "list":
        return await update.effective_message.reply_text("وایت‌لیست:\n" + (", ".join(domains) or "خالی"))
    if len(context.args) < 2:
        return await update.effective_message.reply_text("دامنه را هم بده. مثال: /whitelist_domain add github.com")
    d = context.args[1].lower()
    if action == "add" and d not in domains:
        domains.append(d)
    elif action == "remove" and d in domains:
        domains.remove(d)
    db.set_whitelist(chat_id, domains)
    await update.effective_message.reply_text(f"✅ به‌روزرسانی شد: {d}")


# ---------- قوانین / اطلاعات ----------
async def set_rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    rules = update.effective_message.text.partition(" ")[2].strip()
    db.update_chat(update.effective_chat.id, rules=rules)
    await update.effective_message.reply_text("✅ قوانین ذخیره شد.")


async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules = db.get_chat(update.effective_chat.id)["rules"]
    await update.effective_message.reply_text(rules or "📜 هنوز قوانینی تنظیم نشده.")


async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_id, name = await resolve_target(update, context)
    if target_id is None:
        target_id, name = update.effective_user.id, update.effective_user.full_name
    u = db.get_user(target_id)
    warns = db.get_warning(update.effective_chat.id, target_id)
    credits = u["credits"] if u else 0
    msgs = u["msg_count"] if u else 0
    await update.effective_message.reply_text(
        f"👤 {name}\n🆔 {target_id}\n💳 امتیاز: {credits}\n⚠️ وارن: {warns}\n💬 پیام‌ها: {msgs}")


async def admins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    lines = [f"• {a.user.full_name}" + (" (سازنده)" if a.status == "creator" else "") for a in admins]
    await update.effective_message.reply_text("👮 ادمین‌ها:\n" + "\n".join(lines))


async def set_title_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    title = update.effective_message.text.partition(" ")[2].strip()
    await context.bot.set_chat_title(update.effective_chat.id, title)
    await update.effective_message.reply_text("✅ عنوان تغییر کرد.")


async def set_description_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    desc = update.effective_message.text.partition(" ")[2].strip()
    await context.bot.set_chat_description(update.effective_chat.id, desc)
    await update.effective_message.reply_text("✅ توضیحات تغییر کرد.")


# ---------- FAQ (افزودن) ----------
async def add_faq_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    raw = update.effective_message.text.partition(" ")[2]
    if "|" not in raw:
        return await update.effective_message.reply_text("فرمت: /add_faq الگو | پاسخ")
    pattern, _, answer = raw.partition("|")
    db.add_faq(update.effective_chat.id, pattern.strip(), answer.strip())
    await update.effective_message.reply_text("✅ به FAQ اضافه شد.")


# ---------- تنظیمات گروه (قابل تنظیم در ربات) ----------
async def set_warn_limit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    if not context.args or not context.args[0].isdigit():
        cur = db.get_chat(update.effective_chat.id)["warn_limit"]
        return await update.effective_message.reply_text(f"سقف وارن فعلی: {cur}\nفرمت: /set_warn_limit 3")
    db.update_chat(update.effective_chat.id, warn_limit=int(context.args[0]))
    await update.effective_message.reply_text(f"✅ سقف وارن: {context.args[0]}")


async def set_warn_action_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    if not context.args or context.args[0].lower() not in ("kick", "ban"):
        cur = db.get_chat(update.effective_chat.id)["warn_action"]
        return await update.effective_message.reply_text(f"عمل فعلی پس از وارن: {cur}\nفرمت: /set_warn_action kick|ban")
    db.update_chat(update.effective_chat.id, warn_action=context.args[0].lower())
    await update.effective_message.reply_text(f"✅ عمل پس از رسیدن به سقف وارن: {context.args[0].lower()}")


async def set_language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update, context):
        return
    if not context.args or context.args[0].lower() not in ("fa", "en"):
        cur = db.get_chat(update.effective_chat.id)["language"]
        return await update.effective_message.reply_text(f"زبان فعلی: {cur}\nفرمت: /set_language fa|en")
    db.update_chat(update.effective_chat.id, language=context.args[0].lower())
    await update.effective_message.reply_text(f"✅ زبان گروه: {context.args[0].lower()}")
