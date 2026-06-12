from telegram import Update
from telegram.ext import ContextTypes

from app import db
from app.permissions import is_owner


async def donate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # نمایش راه‌های حمایت به کاربران
    mode = db.get_donation_mode()
    if mode == "off":
        await update.effective_message.reply_text("💝 در حال حاضر امکان حمایت فعال نیست.")
        return
    lines = [db.get_donation_text() or "💝 از حمایت شما سپاسگزاریم!"]
    if mode in ("rial", "both"):
        rial = db.get_rial_info()
        if rial:
            lines.append(f"\n💳 پرداخت ریالی:\n{rial}")
    if mode in ("crypto", "both"):
        wallets = db.list_wallets()
        if wallets:
            lines.append("\n🪙 کیف‌پول‌های کریپتو:")
            for w in wallets:
                net = f" ({w['network']})" if w["network"] else ""
                lines.append(f"• {w['coin']}{net}:\n`{w['address']}`")
    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")


# ---------- دستورات اونر برای پیکربندی دونیت ----------
async def set_donation_mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    arg = context.args[0].lower() if context.args else ""
    if arg not in ("off", "crypto", "rial", "both"):
        await update.effective_message.reply_text(
            f"حالت فعلی دونیت: {db.get_donation_mode()}\nفرمت: /set_donation_mode off|crypto|rial|both")
        return
    db.set_donation_mode(arg)
    await update.effective_message.reply_text(f"✅ حالت دونیت: {arg}")


async def set_rial_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    info = update.effective_message.text.partition(" ")[2].strip()
    if not info:
        await update.effective_message.reply_text("فرمت: /set_rial شماره کارت یا شبا + نام صاحب حساب")
        return
    db.set_rial_info(info)
    await update.effective_message.reply_text("✅ اطلاعات پرداخت ریالی ذخیره شد.")


async def set_donation_text_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    text = update.effective_message.text.partition(" ")[2].strip()
    db.set_donation_text(text)
    await update.effective_message.reply_text("✅ متن دونیت ذخیره شد.")


async def add_wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    if len(context.args) < 2:
        await update.effective_message.reply_text(
            "فرمت: /add_wallet <ارز> <آدرس> [شبکه]\nمثال: /add_wallet USDT TXxxxxxxxx TRC20")
        return
    coin = context.args[0]
    address = context.args[1]
    network = context.args[2] if len(context.args) > 2 else None
    db.add_wallet(coin, address, network)
    await update.effective_message.reply_text(f"✅ کیف‌پول {coin.upper()} اضافه شد.")


async def remove_wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.effective_message.reply_text("⛔ فقط ادمین اصلی.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text("فرمت: /remove_wallet <شناسه>  (شناسه را از /list_wallets بگیر)")
        return
    db.remove_wallet(int(context.args[0]))
    await update.effective_message.reply_text("✅ کیف‌پول حذف شد.")


async def list_wallets_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallets = db.list_wallets()
    if not wallets:
        await update.effective_message.reply_text("هیچ کیف‌پولی ثبت نشده.")
        return
    lines = [f"#{w['id']} — {w['coin']}" + (f" ({w['network']})" if w["network"] else "") + f": {w['address']}" for w in wallets]
    await update.effective_message.reply_text("🪙 کیف‌پول‌ها:\n" + "\n".join(lines))