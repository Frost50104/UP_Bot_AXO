from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

router = Router()

@router.callback_query(F.data.startswith("accept_"))
async def accept_request(callback: CallbackQuery, bot):
    user_id = int(callback.data.replace("accept_", ""))

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