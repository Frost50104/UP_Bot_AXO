from aiogram import Router, Bot
from aiogram.types import Message
import re
from aiogram.exceptions import TelegramBadRequest
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(lambda m: m.reply_to_message and m.reply_to_message.text and "Ответьте на это сообщение" in m.reply_to_message.text)
async def handle_comment_reply(message: Message, bot: Bot):
    logger.info("💬 Получен ответ на сообщение-подсказку")

    # user_id теперь в подсказке
    content = message.reply_to_message.text
    match = re.search(r"user_id:\s*(\d+)", content)
    if not match:
        logger.warning("❌ user_id не найден в подсказке")
        return

    user_id = int(match.group(1))
    logger.info(f"📨 Отправляем комментарий пользователю user_id={user_id}")

    try:
        await bot.send_message(user_id, f"Комментарий по вашей заявке:\n\n{message.text}")
        logger.info("✅ Комментарий отправлен")
    except TelegramBadRequest as e:
        logger.error(f"❌ Ошибка при отправке комментария: {e}")