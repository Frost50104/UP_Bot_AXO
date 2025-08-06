from aiogram import Router, F
from aiogram.types import Message
from config import ADMINS
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials

router = Router()

# Название таблицы (должно совпадать с названием в google_sheets.py)
SPREADSHEET_NAME = "Бот АХО / Заявки"

@router.message(lambda message: re.match(r"^\/show_crm(@\w+)?$", message.text))
async def show_crm(message: Message):
    """
    Обработчик команды /show_crm
    Отправляет пользователю ссылку на Google таблицу с заявками
    """
    # Проверка прав доступа
    if message.from_user.id not in ADMINS:
        await message.answer("У вас нет доступа к этой команде.")
        return
        
    try:
        # Авторизация и подключение к Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("google_creds.json", scope)
        client = gspread.authorize(creds)
        
        # Получаем объект таблицы
        spreadsheet = client.open(SPREADSHEET_NAME)
        
        # Получаем URL таблицы
        spreadsheet_url = spreadsheet.url
        
        # Отправляем ссылку пользователю
        await message.answer(f"Ссылка на таблицу с заявками: {spreadsheet_url}")
    except Exception as e:
        await message.answer(f"Ошибка при получении ссылки на таблицу: {e}")