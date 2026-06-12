import json
import time

from telegram import Update
from telegram.ext import ContextTypes

from app import config, db
from app.ai_provider import call_ai
from app.permissions import is_admin, is_owner
from app.handlers.common import parse_duration


# ---------- مدیریت API (فقط ادمین اصلی) ----------
async def set_api_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    msg = update.effective_message
    raw = msg.text.partition(" ")[2].strip()
    if not raw and msg.reply_to_message and msg.reply_to_message.text:
        raw = msg.reply_to_message.text.strip()
    if not raw:
        await msg.reply_text(
            "JSON تنظیمات API را یا بعد از دستور بفرست، یا روی یک پیام JSON ریپلای کن.\n"
            "نمونه:\n"
            "/set_api {\"name\":\"freemodel\",\"endpoint\":\"https://api.freemodel.dev/v1/chat/completions\",\"method\":\"POST\",\"headers\":{\"Authorization\":\"Bearer YOUR_KEY\",\"Content-Type\":\"application/json\"},\"body_template\":{\"model\":\"gpt-4o-mini\",\"max_tokens\":150,\"temperature\":0.2,\"messages\":[{\"role\":\"system\",\"content\":\"{system_prompt}\"},{\"role\":\"user\",\"content\":\"{user_message}\"}]},\"response_path\":\"choices.0.message.content\",\"usage_path\":\"usage.total_tokens\"}"
        )
        return
    try:
        cfg = json.loads(raw)
    except Exception as e:
        await msg.reply_text(f"JSON نامعتبره داداش:\n{e}")
        return
    missing = [k for k in ("name", "endpoint", "response_path") if not cfg.get(k)]
    if missing:
        await msg.reply_text("این فیلدها اجباری‌اند: " + ", ".join(missing))
        return
    db.set_api(cfg)
    await msg.reply_text(f"✅ API '{cfg['name']}' ذخیره شد.\nحالا بزن: /activate_api {cfg['name']}")


async def list_apis_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db.list_apis()
    if not rows:
        await update.effective_message.reply_text("هیچ API ثبت نشده.")
        return
    text = "\n".join(f"{'🟢' if r['enabled'] else '⚪'} {r['name']}" for r in rows)
    await update.effective_message.reply_text("لیست APIها:\n" + text)


async def activate_api_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    if not context.args:
        await update.effective_message.reply_text("فرمت: /activate_api <name>")
        return
    ok = db.activate_api(context.args[0])
    await update.effective_message.reply_text("✅ فعال شد." if ok else "❌ چنین APIای وجود ندارد.")


async def test_api_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    api = db.get_active_api()
    if not api:
        await update.effective_message.reply_text("هیچ API فعالی وجود ندارد.")
        return
    try:
        ans, tokens = await call_ai(api, "تو یک ربات تست هستی.", "سلام، یک جمله کوتاه بگو.")
        extra = f"\n\n(توکن مصرفی: {tokens})" if tokens is not None else ""
        await update.effective_message.reply_text(f"✅ اتصال موفق:\n{ans}{extra}")
    except Exception as e:
        await update.effective_message.reply_text(f"❌ خطا: {e}")


# ---------- اعلامیه (broadcast) فقط ادمین اصلی ----------
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    text = update.effective_message.text.partition(" ")[2].strip()
    if not text:
        await update.effective_message.reply_text("فرمت: /broadcast متن پیام")
        return
    sent, failed = 0, 0
    for r in db.top_users(limit=100000):
        try:
            await context.bot.send_message(r["user_id"], f"📢 {text}")
            sent += 1
        except Exception:
            failed += 1
    await update.effective_message.reply_text(f"ارسال شد به {sent} کاربر (ناموفق: {failed}).")


# ---------- آمار ----------
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db.top_users(10)
    lines = [f"{i+1}. {r['username'] or r['user_id']} — {r['msg_count']} پیام" for i, r in enumerate(rows)]
    await update.effective_message.reply_text("📊 فعال‌ترین کاربران:\n" + ("\n".join(lines) or "خالی"))


# ---------- نظرسنجی ----------
async def poll_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.effective_message.text.partition(" ")[2]
    parts = [p.strip() for p in raw.split("|") if p.strip()]
    if len(parts) < 3:
        await update.effective_message.reply_text("فرمت: /poll سوال | گزینه۱ | گزینه۲ ...")
        return
    await context.bot.send_poll(update.effective_chat.id, parts[0], parts[1:], is_anonymous=False)


# ---------- یادآور ----------
async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # فرمت: /remind me 10m متن کار
    args = context.args
    if len(args) < 2:
        await update.effective_message.reply_text("فرمت: /remind me 10m متن یادآوری")
        return
    idx = 1 if args[0].lower() in ("me", "من") else 0
    secs = parse_duration(args[idx])
    if secs is None:
        await update.effective_message.reply_text("زمان نامعتبر. نمونه: 30s, 10m, 2h, 1d")
        return
    text = " ".join(args[idx + 1:]) or "یادآوری"
    due = int(time.time()) + secs
    rid = db.add_reminder(update.effective_user.id, update.effective_chat.id, due, text)
    context.job_queue.run_once(_fire_reminder, secs, data={"rid": rid, "chat_id": update.effective_chat.id,
                                                            "user_id": update.effective_user.id, "text": text})
    await update.effective_message.reply_text(f"⏰ یادآوری تنظیم شد ({args[idx]}).")


async def _fire_reminder(context: ContextTypes.DEFAULT_TYPE):
    d = context.job.data
    await context.bot.send_message(d["chat_id"], f"⏰ یادآوری: {d['text']}")
    db.mark_reminder_fired(d["rid"])


# ---------- تنظیمات روشن/خاموش گروه ----------
def make_toggle(field, on_text, off_text):
    # سازندهٔ همگام هندلر روشن/خاموش (on/off) برای یک فیلد گروه
    async def _inner(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await is_admin(update, context):
            await update.effective_message.reply_text("⛔ فقط ادمین‌ها.")
            return
        arg = (context.args[0].lower() if context.args else "")
        if arg not in ("on", "off"):
            cur = db.get_chat(update.effective_chat.id)[field]
            await update.effective_message.reply_text(f"وضعیت فعلی: {'on' if cur else 'off'} — فرمت: on/off")
            return
        db.update_chat(update.effective_chat.id, **{field: 1 if arg == "on" else 0})
        await update.effective_message.reply_text(on_text if arg == "on" else off_text)
    return _inner


# ---------- تنظیمات سراسری اونر (قابل تنظیم در ربات) ----------
async def set_log_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    if not context.args:
        await update.effective_message.reply_text(
            f"کانال لاگ فعلی: {db.get_log_channel() or 'تنظیم نشده'}\nفرمت: /set_log_channel -1001234567890  (یا off)")
        return
    if context.args[0].lower() == "off":
        db.set_log_channel("")
        await update.effective_message.reply_text("✅ لاگ خاموش شد.")
        return
    db.set_log_channel(context.args[0])
    await update.effective_message.reply_text(f"✅ کانال لاگ تنظیم شد: {context.args[0]}")


async def set_antispam_rate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    mx, win = db.get_antispam_rate()
    if len(context.args) < 2 or not context.args[0].isdigit() or not context.args[1].isdigit():
        await update.effective_message.reply_text(
            f"نرخ فعلی ضداسپم: حداکثر {mx} پیام در {win} ثانیه\nفرمت: /set_antispam_rate 5 3")
        return
    db.set_antispam_rate(int(context.args[0]), int(context.args[1]))
    await update.effective_message.reply_text(f"✅ ضداسپم: حداکثر {context.args[0]} پیام در {context.args[1]} ثانیه.")


# ---------- بکاپ خودکار دیتابیس در کانال (هر ۶ ساعت) ----------
async def _send_backup(context: ContextTypes.DEFAULT_TYPE, channel):
    db.checkpoint()
    try:
        with open(config.DATABASE_PATH, "rb") as f:
            await context.bot.send_document(
                channel, document=f, filename="bot.sqlite3",
                caption=f"🗄️ بکاپ دیتابیس pythash bot\n⏱ {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return True, None
    except Exception as e:
        return False, e


async def backup_job(context: ContextTypes.DEFAULT_TYPE):
    # توسط JobQueue هر ۶ ساعت یک‌بار صدا زده می‌شود
    channel = db.get_backup_channel()
    if not channel:
        return
    ok, err = await _send_backup(context, channel)
    if not ok:
        try:
            await context.bot.send_message(channel, f"⚠️ بکاپ خودکار ناموفق بود: {err}")
        except Exception:
            pass


async def set_backup_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    if not context.args:
        cur = db.get_setting("backup_channel_id") or (db.get_log_channel() or "تنظیم نشده")
        await update.effective_message.reply_text(
            f"کانال بکاپ/لاگ فعلی: {cur}\n"
            "فرمت: /set_backup_channel -1001234567890  (یا off)\n"
            "اول ربات را در کانال ادمین کن و دسترسی «ارسال پیام» بده.")
        return
    if context.args[0].lower() == "off":
        db.set_backup_channel("")
        await update.effective_message.reply_text("✅ بکاپ خودکار خاموش شد.")
        return
    db.set_backup_channel(context.args[0])
    await update.effective_message.reply_text(
        f"✅ کانال بکاپ تنظیم شد: {context.args[0]}\nهر ۶ ساعت یک‌بار فایل دیتابیس آنجا فرستاده می‌شود.")


async def backup_now_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    channel = db.get_backup_channel()
    if not channel:
        await update.effective_message.reply_text("اول با /set_backup_channel یک کانال تنظیم کن.")
        return
    ok, err = await _send_backup(context, channel)
    await update.effective_message.reply_text("✅ بکاپ فرستاده شد." if ok else f"❌ خطا: {err}")