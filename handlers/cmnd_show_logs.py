from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from config import ADMINS
import os
import re

router = Router()

@router.message(lambda message: re.match(r"^\/show_logs(@\w+)?$", message.text))
async def show_logs(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("У вас нет доступа к этой команде.")
        return

    if not os.path.exists("logs.txt"):
        await message.answer("Файл логов не найден.")
        return

    if os.path.getsize("logs.txt") == 0:
        await message.answer("Файл логов пуст.")
        return

    file = FSInputFile("logs.txt")
    await message.answer_document(file, caption="Файл логов:")