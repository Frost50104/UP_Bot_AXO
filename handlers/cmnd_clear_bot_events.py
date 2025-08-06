from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMINS
import os
import re

router = Router()

@router.message(lambda message: re.match(r"^\/clear_bot_events(@\w+)?$", message.text))
async def clear_bot_events_prompt(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("У вас нет доступа к этой команде.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_clear_bot_events")
    builder.button(text="❌ Отмена", callback_data="cancel_clear_bot_events")
    await message.answer("Вы точно хотите очистить логи событий бота?", reply_markup=builder.as_markup())

@router.callback_query(F.data == "confirm_clear_bot_events")
async def confirm_clear_bot_events(callback: CallbackQuery):
    try:
        with open("bot_events.log", "w", encoding="utf-8") as f:
            f.write("")
        await callback.message.edit_text("✅ Логи событий бота успешно очищены.")
    except Exception as e:
        await callback.message.edit_text(f"Ошибка при очистке: {e}")
    await callback.answer()

@router.callback_query(F.data == "cancel_clear_bot_events")
async def cancel_clear_bot_events(callback: CallbackQuery):
    await callback.message.edit_text("❌ Очистка логов событий отменена.")
    await callback.answer()