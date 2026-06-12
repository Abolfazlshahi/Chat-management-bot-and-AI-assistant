from telegram import Update
from telegram.ext import ContextTypes

from app import config


def is_owner(user_id: int) -> bool:
    return user_id == config.OWNER_ID


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if user is None:
        return False
    if is_owner(user.id):
        return True
    if chat.type == "private":
        return True
    member = await context.bot.get_chat_member(chat.id, user.id)
    return member.status in ("administrator", "creator")