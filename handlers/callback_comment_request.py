from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
import re

router = Router()

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

    try:
        await bot.send_message(
            chat_id=callback.message.chat.id,
            reply_to_message_id=callback.message.message_id,
            text=f"Ответьте на это сообщение, чтобы отправить комментарий\nuser_id: {user_id}"
        )
    except:
        pass

    await callback.answer()