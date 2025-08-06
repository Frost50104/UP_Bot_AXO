from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
import re

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

@router.message(lambda message: re.match(r"^\/my_requests(@\w+)?$", message.text))
async def cmd_my_requests(message: Message):
    """
    Обработчик команды /my_requests
    Отправляет пользователю кнопки для выбора статуса заявок
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
        
        # Создаем клавиатуру с кнопками статусов
        builder = InlineKeyboardBuilder()
        builder.button(text="Новая", callback_data=f"my_status_new_{user_id}")
        builder.button(text="В работе", callback_data=f"my_status_in_progress_{user_id}")
        builder.button(text="Завершена", callback_data=f"my_status_completed_{user_id}")
        builder.button(text="Отклонена", callback_data=f"my_status_rejected_{user_id}")
        builder.button(text="Последние 3 заявки", callback_data=f"my_last_three_{user_id}")
        builder.adjust(2)  # Размещаем кнопки в 2 столбца
        
        # Отправляем сообщение с клавиатурой
        await message.answer("Заявки с каким статусом вы хотите посмотреть?", reply_markup=builder.as_markup())
        
    except Exception as e:
        logger.error(f"Ошибка при получении заявок пользователя: {e}")
        await message.answer(f"Ошибка при получении ваших заявок: {e}")

@router.callback_query(F.data.startswith("my_last_three_"))
async def process_last_three_requests(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку "Последние 3 заявки"
    Показывает последние 3 заявки пользователя независимо от статуса
    """
    # Получаем ID пользователя из callback_data
    # Формат: my_last_three_USER_ID
    if not callback.data.startswith("my_last_three_"):
        await callback.answer("Некорректный формат данных", show_alert=True)
        return
        
    user_id = callback.data[len("my_last_three_"):]
    
    # Проверяем, что пользователь запрашивает свои заявки
    if str(callback.from_user.id) != str(user_id):
        await callback.answer("Вы можете просматривать только свои заявки", show_alert=True)
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
        
        # Фильтруем записи по ID отправителя
        user_records = [
            record for record in all_records 
            if str(record.get('ID отправителя', '')) == str(user_id)
        ]
        
        if not user_records:
            await callback.message.edit_text("У вас пока нет созданных заявок.")
            return
        
        # Сортируем записи по дате (предполагая, что дата в формате, который можно сортировать)
        # Если дата в нестандартном формате, может потребоваться дополнительная обработка
        # Берем последние 3 заявки (или меньше, если их меньше 3)
        last_three_records = sorted(user_records, key=lambda x: x.get('Дата', ''), reverse=True)[:3]
        
        # Формируем сообщение с заявками
        message_parts = [f"Ваши последние 3 заявки ({len(last_three_records)}):\n"]
        
        for record in last_three_records:
            request_id = record.get('ID заявки', 'Нет ID')
            date = record.get('Дата', 'Нет даты')
            department = record.get('Отдел', 'Нет отдела')
            address = record.get('Точка', 'Нет адреса')
            problem = record.get('Текст заявки', 'Нет описания')
            status = record.get('Статус', 'Нет статуса')
            
            # Ограничиваем длину проблемы для читаемости
            if len(problem) > 100:
                problem = problem[:97] + "..."
            
            message_parts.append(f"ID: {request_id}\nДата: {date}\nСтатус: {status}\nОтдел: {department}\nАдрес: {address}\nПроблема: {problem}\n")
        
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
        logger.error(f"Ошибка при получении последних заявок пользователя: {e}")
        await callback.message.edit_text(f"Ошибка при получении ваших заявок: {e}")

@router.callback_query(F.data.startswith("my_status_"))
async def process_my_status_selection(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку выбора статуса для своих заявок
    """
    # Получаем данные из callback_data
    # Формат: my_status_STATUS_KEY_USER_ID
    # Извлекаем префикс "my_status_" и оставшуюся часть
    if not callback.data.startswith("my_status_"):
        await callback.answer("Некорректный формат данных", show_alert=True)
        return
        
    remaining_data = callback.data[len("my_status_"):]
    
    # Находим все возможные ключи статусов
    status_key = None
    for key in STATUSES.keys():
        if remaining_data.startswith(key + "_"):
            status_key = key
            # Извлекаем ID пользователя (все, что после ключа статуса и символа "_")
            user_id = remaining_data[len(key) + 1:]
            break
    
    if not status_key or not user_id:
        await callback.answer("Некорректный формат данных", show_alert=True)
        return
    
    # Проверяем, что пользователь запрашивает свои заявки
    if str(callback.from_user.id) != str(user_id):
        await callback.answer("Вы можете просматривать только свои заявки", show_alert=True)
        return
    
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
        
        # Фильтруем записи по ID отправителя и статусу
        filtered_records = [
            record for record in all_records 
            if str(record.get('ID отправителя', '')) == str(user_id) and record.get('Статус') == status_value
        ]
        
        if not filtered_records:
            await callback.message.edit_text(f"У вас нет заявок со статусом \"{status_value}\".")
            return
        
        # Формируем сообщение с заявками
        message_parts = [f"Ваши заявки со статусом \"{status_value}\" ({len(filtered_records)}):\n"]
        
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
        logger.error(f"Ошибка при получении заявок пользователя: {e}")
        await callback.message.edit_text(f"Ошибка при получении ваших заявок: {e}")