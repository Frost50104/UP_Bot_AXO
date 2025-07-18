import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

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