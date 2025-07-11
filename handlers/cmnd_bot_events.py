from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from config import ADMINS
import os

router = Router()

@router.message(F.text == "/bot_events")
async def send_bot_logs(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("У вас нет доступа к этой команде.")
        return

    log_path = "bot_events.log"

    if not os.path.exists(log_path):
        await message.answer("Файл логов бота не найден.")
        return

    if os.path.getsize(log_path) == 0:
        await message.answer("Файл логов бота пуст.")
        return

    file = FSInputFile(log_path)
    await message.answer_document(file, caption="Логи событий и ошибок бота:")