from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
import re
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "request_comment")
async def comment_request(callback: CallbackQuery, bot):
    # Убираем inline-кнопки
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    # Извлекаем user_id из текста заявки
    content = callback.message.caption or callback.message.text or ""
    match = re.search(r"user_id:\s*(\d+)", content)
    if not match:
        await callback.answer("user_id не найден", show_alert=True)
        return

    user_id = match.group(1)
    
    # Извлекаем ID заявки из текста сообщения
    request_id_match = re.search(r"ID заявки: ([^\n]+)", content)
    request_id = ""
    if request_id_match:
        request_id = request_id_match.group(1)
        logger.info(f"Извлечен ID заявки: {request_id}")
    else:
        logger.warning("Не удалось извлечь ID заявки из сообщения")

    try:
        await bot.send_message(
            chat_id=callback.message.chat.id,
            reply_to_message_id=callback.message.message_id,
            text=f"✏️ Ответьте на ЭТО сообщение, чтобы отправить комментарий\n\nuser_id: {user_id}\nrequest_id: {request_id}"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")

    await callback.answer()