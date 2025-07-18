from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMINS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

router = Router()

# Название таблицы (должно совпадать с названием в google_sheets.py)
SPREADSHEET_NAME = "Бот АХО / Заявки"

# Статусы заявок
STATUSES = {
    "new": "Новая",
    "in_progress": "В работе",
    "completed": "Завершена",
    "rejected": "Отклонена"
}

@router.message(F.text == "/status_list")
async def cmd_status_list(message: Message):
    """
    Обработчик команды /status_list
    Отправляет пользователю кнопки для выбора статуса заявок
    """
    # Проверка прав доступа
    if message.from_user.id not in ADMINS:
        await message.answer("У вас нет доступа к этой команде.")
        return
        
    # Создаем клавиатуру с кнопками статусов
    builder = InlineKeyboardBuilder()
    builder.button(text="Новая", callback_data=f"status_new")
    builder.button(text="В работе", callback_data=f"status_in_progress")
    builder.button(text="Завершена", callback_data=f"status_completed")
    builder.button(text="Отклонена", callback_data=f"status_rejected")
    builder.adjust(2)  # Размещаем кнопки в 2 столбца
    
    # Отправляем сообщение с клавиатурой
    await message.answer("Заявки с каким статусом вы хотите посмотреть?", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("status_"))
async def process_status_selection(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку выбора статуса
    """
    # Проверка прав доступа
    if callback.from_user.id not in ADMINS:
        await callback.answer("У вас нет доступа к этой команде.", show_alert=True)
        return
    
    # Получаем выбранный статус из callback_data
    # Удаляем префикс "status_" и получаем ключ статуса
    status_key = callback.data.replace("status_", "", 1)
    status_value = STATUSES.get(status_key)
    
    if not status_value:
        await callback.answer("Неизвестный статус", show_alert=True)
        return
    
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
        
        # Фильтруем записи по статусу
        filtered_records = [record for record in all_records if record.get('Статус') == status_value]
        
        if not filtered_records:
            await callback.message.edit_text(f"Заявок со статусом \"{status_value}\" не найдено.")
            return
        
        # Формируем сообщение с заявками
        message_parts = [f"Заявки со статусом \"{status_value}\":"]
        
        for record in filtered_records:
            request_id = record.get('ID заявки', 'Нет ID')
            date = record.get('Дата', 'Нет даты')
            department = record.get('Отдел', 'Нет отдела')
            address = record.get('Точка', 'Нет адреса')
            problem = record.get('Текст заявки', 'Нет описания')
            
            # Ограничиваем длину проблемы для читаемости
            if len(problem) > 100:
                problem = problem[:97] + "..."
            
            message_parts.append(f"ID: {request_id}\nДата: {date}\nОтдел: {department}\nАдрес: {address}\nПроблема: {problem}\n")
        
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
            
            # Отправляем первую часть, редактируя исходное сообщение
            await callback.message.edit_text(chunks[0])
            
            # Отправляем остальные части как новые сообщения
            for chunk in chunks[1:]:
                await callback.message.answer(chunk)
        else:
            # Если сообщение помещается целиком, отправляем его
            await callback.message.edit_text(message_text)
        
    except Exception as e:
        logger.error(f"Ошибка при получении заявок: {e}")
        await callback.message.edit_text(f"Ошибка при получении заявок: {e}")