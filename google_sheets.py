import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Авторизация и подключение к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google_creds.json", scope)
client = gspread.authorize(creds)

# Название таблицы или её ключ (можно взять из URL)
SPREADSHEET_NAME = "Бот АХО / Заявки"
sheet = client.open(SPREADSHEET_NAME).sheet1

# Функция логирования
def log_request(date, department, address, phone, problem, status="Новая", request_id="", sender_name="", sender_id=""):
    """
    Логирует заявку в Google Sheets с указанными параметрами.
    
    Параметры:
    - date: Дата и время заявки
    - department: Отдел, куда направлена заявка
    - address: Адрес точки
    - phone: Телефон
    - problem: Текст заявки
    - status: Статус заявки (по умолчанию "Новая")
    - request_id: ID заявки (если есть)
    - sender_name: Имя отправителя
    - sender_id: ID отправителя
    """
    # Формируем строку для добавления в таблицу
    row = [date, department, address, phone, problem, status, request_id, sender_name, str(sender_id)]
    sheet.append_row(row, value_input_option='USER_ENTERED')

def update_request_status(request_id, new_status):
    """
    Обновляет статус заявки в Google Sheets по её ID.
    
    Параметры:
    - request_id: ID заявки для поиска
    - new_status: Новый статус заявки ("Новая", "В работе", "Завершена", "Отклонена")
    
    Возвращает:
    - True, если обновление прошло успешно
    - False, если заявка не найдена или произошла ошибка
    """
    try:
        # Получаем все записи
        all_records = sheet.get_all_records()
        
        # Ищем индекс строки с нужным request_id
        # +2 потому что: +1 для заголовка таблицы и +1 потому что индексация в Google Sheets начинается с 1
        for i, record in enumerate(all_records):
            if record.get('ID заявки') == request_id:
                row_index = i + 2
                # Предполагаем, что столбец статуса - шестой (индекс 5, колонка F)
                status_column = 6
                sheet.update_cell(row_index, status_column, new_status)
                logger.info(f"Статус заявки {request_id} обновлен на '{new_status}'")
                return True
        
        logger.warning(f"Заявка с ID {request_id} не найдена")
        return False
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса заявки: {e}")
        return False

def update_request_department(request_id, new_department):
    """
    Обновляет отдел заявки в Google Sheets по её ID.
    
    Параметры:
    - request_id: ID заявки для поиска
    - new_department: Новое название отдела
    
    Возвращает:
    - True, если обновление прошло успешно
    - False, если заявка не найдена или произошла ошибка
    """
    try:
        # Получаем все записи
        all_records = sheet.get_all_records()
        
        # Ищем индекс строки с нужным request_id
        # +2 потому что: +1 для заголовка таблицы и +1 потому что индексация в Google Sheets начинается с 1
        for i, record in enumerate(all_records):
            if record.get('ID заявки') == request_id:
                row_index = i + 2
                # Предполагаем, что столбец отдела - второй (индекс 1, колонка B)
                department_column = 2
                sheet.update_cell(row_index, department_column, new_department)
                logger.info(f"Отдел заявки {request_id} обновлен на '{new_department}'")
                return True
        
        logger.warning(f"Заявка с ID {request_id} не найдена")
        return False
    except Exception as e:
        logger.error(f"Ошибка при обновлении отдела заявки: {e}")
        return False