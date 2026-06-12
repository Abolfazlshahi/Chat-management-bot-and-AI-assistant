import re

from telegram import Update
from telegram.ext import ContextTypes

from app import config, db


async def notify_log(context: ContextTypes.DEFAULT_TYPE, text: str):
    channel = db.get_log_channel()
    if channel:
        try:
            await context.bot.send_message(channel, text)
        except Exception:
            pass


async def resolve_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کاربر هدف را از ریپلای، آی‌دی عددی یا منشن متنی پیدا می‌کند."""
    msg = update.effective_message
    if msg.reply_to_message:
        u = msg.reply_to_message.from_user
        return u.id, (u.username or u.full_name)
    # text_mention (کاربر بدون یوزرنیم که تگ شده)
    for ent in (msg.entities or []):
        if ent.type == "text_mention" and ent.user:
            return ent.user.id, ent.user.full_name
    if context.args:
        arg = context.args[0]
        if arg.lstrip("-").isdigit():
            return int(arg), arg
    return None, None


DURATION_RE = re.compile(r"^(\d+)([smhd])$")


def parse_duration(text: str):
    """'10m' -> ثانیه. پشتیبانی s/m/h/d."""
    m = DURATION_RE.match(text.strip().lower())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    return n * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]