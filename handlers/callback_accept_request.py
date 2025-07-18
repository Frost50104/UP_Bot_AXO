from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
import re
import logging
from google_sheets import update_request_status

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("accept_"))
async def accept_request(callback: CallbackQuery, bot):
    user_id = int(callback.data.replace("accept_", ""))

    # Извлекаем ID заявки из текста сообщения
    message_text = callback.message.text or callback.message.caption or ""
    request_id_match = re.search(r"ID заявки: ([^\n]+)", message_text)
    
    if request_id_match:
        request_id = request_id_match.group(1)
        # Обновляем статус заявки на "В работе"
        success = update_request_status(request_id, "В работе")
        if success:
            logger.info(f"Статус заявки {request_id} обновлен на 'В работе'")
        else:
            logger.error(f"Не удалось обновить статус заявки {request_id}")
    else:
        logger.error("Не удалось извлечь ID заявки из сообщения")

    try:
        await bot.send_message(user_id, "Заявка принята в работу")
    except TelegramBadRequest:
        pass  # пользователь, возможно, удалил чат с ботом

    # Удаляем inline-кнопку
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    await callback.answer("Заявка принята.")