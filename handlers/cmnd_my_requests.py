from aiogram import Router, F
from aiogram.types import Message
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

router = Router()

# Название таблицы (должно совпадать с названием в google_sheets.py)
SPREADSHEET_NAME = "Бот АХО / Заявки"

@router.message(F.text == "/my_requests")
async def cmd_my_requests(message: Message):
    """
    Обработчик команды /my_requests
    Отправляет пользователю список всех заявок, которые он создал
    """
    user_id = message.from_user.id
    
    try:
        # Авторизация и подключение к Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("google_creds.json", scope)
        client = gspread.authorize(creds)
        
        # Получаем объект таблицы
        spreadsheet = client.open(SPREADSHEET_NAME)
        sheet = spreadsheet.sheet1
        
        # Получаем все записи
        all_records = sheet.get_all_records()
        
        # Фильтруем записи по ID отправителя
        user_records = [record for record in all_records if str(record.get('ID отправителя', '')) == str(user_id)]
        
        if not user_records:
            await message.answer("У вас пока нет созданных заявок.")
            return
        
        # Формируем сообщение с заявками
        message_parts = [f"Ваши заявки ({len(user_records)}):"]
        
        for record in user_records:
            request_id = record.get('ID заявки', 'Нет ID')
            date = record.get('Дата', 'Нет даты')
            department = record.get('Отдел', 'Нет отдела')
            address = record.get('Точка', 'Нет адреса')
            problem = record.get('Текст заявки', 'Нет описания')
            status = record.get('Статус', 'Нет статуса')
            
            # Ограничиваем длину проблемы для читаемости
            if len(problem) > 100:
                problem = problem[:97] + "..."
            
            message_parts.append(f"ID: {request_id}\nДата: {date}\nОтдел: {department}\nАдрес: {address}\nПроблема: {problem}\nСтатус: {status}\n")
        
        # Объединяем части сообщения
        message_text = "\n".join(message_parts)
        
        # Если сообщение слишком длинное, разбиваем его на части
        if len(message_text) > 4000:
            chunks = []
            current_chunk = message_parts[0] + "\n"
            
            for part in message_parts[1:]:
                if len(current_chunk) + len(part) + 1 > 4000:
                    chunks.append(current_chunk)
                    current_chunk = part + "\n"
                else:
                    current_chunk += "\n" + part
            
            if current_chunk:
                chunks.append(current_chunk)
            
            # Отправляем части как отдельные сообщения
            for chunk in chunks:
                await message.answer(chunk)
        else:
            # Если сообщение помещается целиком, отправляем его
            await message.answer(message_text)
        
    except Exception as e:
        logger.error(f"Ошибка при получении заявок пользователя: {e}")
        await message.answer(f"Ошибка при получении ваших заявок: {e}")