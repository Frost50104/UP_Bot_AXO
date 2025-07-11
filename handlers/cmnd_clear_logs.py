from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMINS
import os

router = Router()

@router.message(F.text == "/clear_logs")
async def clear_logs_prompt(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("У вас нет доступа к этой команде.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="clear_logs_confirm")
    builder.button(text="❌ Отмена", callback_data="clear_logs_cancel")
    await message.answer("Вы точно хотите очистить логи?", reply_markup=builder.as_markup())

@router.callback_query(F.data == "clear_logs_confirm")
async def confirm_clear_logs(callback: CallbackQuery):
    try:
        with open("logs.txt", "w", encoding="utf-8") as f:
            f.write("")
        await callback.message.edit_text("✅ Логи успешно очищены.")
    except Exception as e:
        await callback.message.edit_text(f"Ошибка при очистке: {e}")
    await callback.answer()

@router.callback_query(F.data == "clear_logs_cancel")
async def cancel_clear_logs(callback: CallbackQuery):
    await callback.message.edit_text("❌ Очистка логов отменена.")
    await callback.answer()