from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from config import ADMINS

router = Router()

@router.message(F.text == "/show_logs")
async def show_logs(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("У вас нет доступа к этой команде.")
        return

    try:
        file = FSInputFile("logs.txt")
        await message.answer_document(file, caption="Файл логов:")
    except FileNotFoundError:
        await message.answer("Файл логов не найден.")