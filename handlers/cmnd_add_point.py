from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re
import logging

import data_lookup
from config import ADMINS, CHAT_IDS, SENDER_DATA_XLSX_PATH

router = Router()
logger = logging.getLogger(__name__)


class AddPointStates(StatesGroup):
    WaitingForXlsxFile = State()


@router.message(lambda message: message.text and re.match(r"^\/add_point(@\w+)?$", message.text))
async def cmd_add_point(message: Message, state: FSMContext):
    if message.chat.id in CHAT_IDS.values():
        await message.answer("Эта команда доступна только в личном чате с ботом.")
        return

    if message.from_user.id not in ADMINS:
        await message.answer("У вас нет доступа к этой команде.")
        return

    await state.set_state(AddPointStates.WaitingForXlsxFile)
    await message.answer("📎 Отправьте xlsx-файл с данными точек для замены текущего реестра.")


@router.message(AddPointStates.WaitingForXlsxFile, F.document)
async def receive_xlsx_file(message: Message, state: FSMContext):
    document = message.document

    if not document.file_name or not document.file_name.lower().endswith(".xlsx"):
        await message.answer("❌ Пожалуйста, отправьте файл в формате .xlsx")
        return

    try:
        await message.bot.download(document.file_id, destination=SENDER_DATA_XLSX_PATH)
        data_lookup.reload_data()

        # Load new data to get record count
        from data_lookup import _load_data, _cache
        _load_data()
        count = len(_cache["by_id"])

        await message.answer(f"✅ Реестр точек обновлён. Загружено записей: {count}")
        logger.info(f"Файл реестра точек обновлён пользователем {message.from_user.id}, записей: {count}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при загрузке файла: {e}")
        logger.exception(f"Ошибка при обновлении реестра точек: {e}")

    await state.clear()


@router.message(AddPointStates.WaitingForXlsxFile)
async def receive_wrong_input(message: Message):
    await message.answer("❌ Пожалуйста, отправьте файл в формате .xlsx")
