import logging

from telegram import Update
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, MessageHandler, filters)

from app import config, db
from app.handlers import ai_chat, admin_tools, moderation, events, donations

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


async def start_cmd(update: Update, context):
    await update.effective_message.reply_text(
        "🤖 سلام! من pythash bot هستم.\n"
        "در پیوی هر سوالی بپرس، در گروه منشنم کن یا روی پیامم ریپلای بزن.\n"
        "دستورات: /help"
    )


async def help_cmd(update: Update, context):
    await update.effective_message.reply_text(
        "╭─── 🤖 **راهنمای pythash bot** ───╮\n\n"
        "🔹 **هوش مصنوعی**\n"
        "• در گروه: ربات را منشن کن، روی پیامش ریپلای بزن، یا /ask بزن\n"
        "• /ask <سوال>  (یا روی هر پیام ریپلای کن و /ask بزن)\n"
        "• /set_personality (تعیین شخصیت و لحن ربات)\n"
        "• /set_prompt (پرامپت سیستمی)\n"
        "• /credit\n"
        "• /give_credit\n"
        "• /take_credit\n"
        "• /set_default_credits\n"
        "• /set_cost\n\n"
        "🛡️ **مدیریت گروه**\n"
        "• /warn /unwarn /ban /unban /kick\n"
        "• /mute /unmute /purge\n"
        "• /del (ریپلای روی پیام برای حذف آن، حتی پیام ادمین)\n"
        "• /pin /unpin /lock /unlock\n\n"
        "🔗 **فیلتر و لینک**\n"
        "• /add_filter /remove_filter /filters\n"
        "• /link_mode\n"
        "• /whitelist_domain\n\n"
        "👥 **تنظیمات گروه**\n"
        "• /set_rules /rules /info /admins\n"
        "• /set_title /set_description\n"
        "• /set_welcome /set_goodbye\n"
        "• /ai on|off\n"
        "• /verify on|off\n"
        "• /antispam on|off\n"
        "• /set_warn_limit\n"
        "• /set_warn_action\n"
        "• /set_language\n"
        "• /set_antispam_rate\n"
        "• /set_log_channel\n"
        "• /set_backup_channel (بکاپ خودکار دیتابیس هر ۶ ساعت + لاگ‌ها)\n"
        "• /backup_now (بکاپ فوری دیتابیس)\n\n"
        "⚙️ **API**\n"
        "• /set_api\n"
        "• /list_apis\n"
        "• /activate_api\n"
        "• /test_api\n\n"
        "💝 **دونیت**\n"
        "• /donate\n"
        "• /set_donation_mode\n"
        "• /set_rial\n"
        "• /add_wallet /remove_wallet /list_wallets\n"
        "• /set_donation_text\n\n"
        "🧰 **ابزارها**\n"
        "• /poll\n"
        "• /remind\n"
        "• /stats\n"
        "• /broadcast\n"
        "• /add_faq\n\n"
        "╰──────────────────────────╯"
    )


def main():
    db.init_db()
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN در فایل .env تنظیم نشده است.")

    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # عمومی
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))

    # اعتبار / AI
    app.add_handler(CommandHandler("credit", ai_chat.credit_cmd))
    app.add_handler(CommandHandler("give_credit", ai_chat.give_credit_cmd))
    app.add_handler(CommandHandler("take_credit", ai_chat.take_credit_cmd))
    app.add_handler(CommandHandler("set_prompt", ai_chat.set_prompt_cmd))
    app.add_handler(CommandHandler("set_default_credits", ai_chat.set_default_credits_cmd))
    app.add_handler(CommandHandler("set_cost", ai_chat.set_cost_cmd))
    app.add_handler(CommandHandler("ask", ai_chat.ask_cmd))
    app.add_handler(CommandHandler("set_personality", ai_chat.set_personality_cmd))

    # تنظیمات سراسری اونر (قابل تنظیم در ربات)
    app.add_handler(CommandHandler("set_log_channel", admin_tools.set_log_channel_cmd))
    app.add_handler(CommandHandler("set_antispam_rate", admin_tools.set_antispam_rate_cmd))
    app.add_handler(CommandHandler("set_backup_channel", admin_tools.set_backup_channel_cmd))
    app.add_handler(CommandHandler("backup_now", admin_tools.backup_now_cmd))

    # دونیت
    app.add_handler(CommandHandler("donate", donations.donate_cmd))
    app.add_handler(CommandHandler("set_donation_mode", donations.set_donation_mode_cmd))
    app.add_handler(CommandHandler("set_rial", donations.set_rial_cmd))
    app.add_handler(CommandHandler("set_donation_text", donations.set_donation_text_cmd))
    app.add_handler(CommandHandler("add_wallet", donations.add_wallet_cmd))
    app.add_handler(CommandHandler("remove_wallet", donations.remove_wallet_cmd))
    app.add_handler(CommandHandler("list_wallets", donations.list_wallets_cmd))

    # مدیریت API + ابزارها
    app.add_handler(CommandHandler("set_api", admin_tools.set_api_cmd))
    app.add_handler(CommandHandler("list_apis", admin_tools.list_apis_cmd))
    app.add_handler(CommandHandler("activate_api", admin_tools.activate_api_cmd))
    app.add_handler(CommandHandler("test_api", admin_tools.test_api_cmd))
    app.add_handler(CommandHandler("broadcast", admin_tools.broadcast_cmd))
    app.add_handler(CommandHandler("stats", admin_tools.stats_cmd))
    app.add_handler(CommandHandler("poll", admin_tools.poll_cmd))
    app.add_handler(CommandHandler("remind", admin_tools.remind_cmd))

    # روشن/خاموش‌ها (هندلرهای همگام، بدون asyncio.run)
    app.add_handler(CommandHandler("ai", admin_tools.make_toggle("ai_enabled", "🤖 هوش مصنوعی روشن شد.", "هوش مصنوعی خاموش شد.")))
    app.add_handler(CommandHandler("verify", admin_tools.make_toggle("verify_enabled", "✅ وریفای روشن شد.", "وریفای خاموش شد.")))
    app.add_handler(CommandHandler("antispam", admin_tools.make_toggle("antispam_enabled", "🛡️ ضداسپم روشن شد.", "ضداسپم خاموش شد.")))

    # مدیریت گروه
    for name, fn in {
        "warn": moderation.warn_cmd, "unwarn": moderation.unwarn_cmd,
        "ban": moderation.ban_cmd, "unban": moderation.unban_cmd, "kick": moderation.kick_cmd,
        "mute": moderation.mute_cmd, "unmute": moderation.unmute_cmd,
        "purge": moderation.purge_cmd, "del": moderation.del_cmd, "pin": moderation.pin_cmd, "unpin": moderation.unpin_cmd,
        "lock": moderation.lock_cmd, "unlock": moderation.unlock_cmd,
        "add_filter": moderation.add_filter_cmd, "remove_filter": moderation.remove_filter_cmd,
        "filters": moderation.list_filters_cmd, "link_mode": moderation.link_mode_cmd,
        "whitelist_domain": moderation.whitelist_domain_cmd,
        "set_rules": moderation.set_rules_cmd, "rules": moderation.rules_cmd,
        "info": moderation.info_cmd, "admins": moderation.admins_cmd,
        "set_title": moderation.set_title_cmd, "set_description": moderation.set_description_cmd,
        "add_faq": moderation.add_faq_cmd,
        "set_warn_limit": moderation.set_warn_limit_cmd, "set_warn_action": moderation.set_warn_action_cmd,
        "set_language": moderation.set_language_cmd,
        "set_welcome": events.set_welcome_cmd, "set_goodbye": events.set_goodbye_cmd,
    }.items():
        app.add_handler(CommandHandler(name, fn))

    # رویدادها
    app.add_handler(CallbackQueryHandler(events.verify_callback, pattern=r"^verify:"))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, events.new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, events.left_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUPS), events.group_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, events.private_message))

    # بکاپ خودکار دیتابیس هر ۶ ساعت یک‌بار در کانال تعیین‌شده (/set_backup_channel)
    if app.job_queue:
        app.job_queue.run_repeating(admin_tools.backup_job, interval=6 * 3600, first=120)

    logging.info("pythash bot started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
