from aiogram import Router
from aiogram.types import Message
import re

router = Router()


@router.message(lambda message: message.text and re.match(r"^\/my_id(@\w+)?$", message.text))
async def cmd_my_id(message: Message):
    user_id = message.from_user.id if message.from_user else "unknown"
    chat_id = message.chat.id if message.chat else "unknown"
    await message.answer(f"Ваш ID: {user_id}\nID чата: {chat_id}")
