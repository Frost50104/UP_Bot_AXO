import logging
import sys
import re
import asyncio
import hashlib
import time
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from aiogram import types
from aiogram.enums import ContentType
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
from config import TOKEN, CHAT_IDS
from states import RequestStates
from handlers import cmnd_show_logs
from handlers import cmnd_clear_logs
from handlers import cmnd_bot_events
from handlers import cmnd_clear_bot_events
from handlers import callback_accept_request
from handlers import callback_comment_request
from handlers import callback_transfer_request
from handlers import handle_comment_reply
from handlers import handle_status_reply
from handlers import cmnd_show_crm
from handlers import cmnd_status_list
from handlers import cmnd_my_requests
from handlers import cmnd_add_admin
from handlers import cmnd_delete_admin
from handlers import cmnd_my_id
from handlers import cmnd_add_point
from google_sheets import log_request
from data_lookup import get_sender_extra_info


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler("bot_events.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Антидубликат: храним недавние обработанные заявки
# По ID заявки: request_id -> timestamp
PROCESSED_REQUESTS: dict[str, float] = {}
# По содержимому: content_key -> (timestamp, request_id)
PROCESSED_CONTENT: dict[str, tuple[float, str]] = {}
# Сколько секунд держим заявку в памяти (по умолчанию 10 минут)
DEDUP_TTL_SECONDS = 10 * 60
# Максимальный размер кэша, чтобы не разрастался бесконечно
DEDUP_MAX_SIZE = 2000

# Подключение роутера
dp.include_router(cmnd_show_logs.router)
dp.include_router(cmnd_clear_logs.router)
dp.include_router(cmnd_bot_events.router)
dp.include_router(cmnd_clear_bot_events.router)
dp.include_router(callback_accept_request.router)
dp.include_router(callback_comment_request.router)
dp.include_router(callback_transfer_request.router)
dp.include_router(handle_comment_reply.router)
dp.include_router(handle_status_reply.router)
dp.include_router(cmnd_show_crm.router)
dp.include_router(cmnd_status_list.router)
dp.include_router(cmnd_my_requests.router)
dp.include_router(cmnd_add_admin.router)
dp.include_router(cmnd_delete_admin.router)
dp.include_router(cmnd_my_id.router)
dp.include_router(cmnd_add_point.router)

async def main():
    logger.info("🚀 Бот запускается...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"❌ Ошибка в боте: {e}")
    finally:
        logger.info("⛔️ Бот остановлен.")

start_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="НОВАЯ ЗАЯВКА")]],
    resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="ОТМЕНА")]],
    resize_keyboard=True
)

departments = {
    "Интернет": "internet",
    "Касса/iiko": "iiko",
    "Камеры наблюдения": "cameras",
    "Холодильники / кондиционеры": "cold",
    "Компьютер / мышка / клавиатура": "pc",
    "Что-то другое сломалось": "other",
    "Баристика": "barista",
    "Буква": "letter",
    "Мысли": "thoughts"
}

def department_kb():
    builder = ReplyKeyboardBuilder()
    for name in departments.keys():
        builder.button(text=name)
    builder.button(text="ОТМЕНА")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(lambda message: message.text and re.match(r"^\/start(@\w+)?$", message.text))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Привет, я бот UPPETIT 2.0, если у Вас появилась проблема - я помогу её решить", reply_markup=start_kb)

@dp.message(F.text == "НОВАЯ ЗАЯВКА")
async def new_request(message: Message, state: FSMContext):
    # Проверяем, что заявка не создается в чате отдела
    if message.chat.id in CHAT_IDS.values():
        await message.answer("Создание новых заявок в чатах отделов запрещено. Пожалуйста, используйте личный чат с ботом для создания заявок.")
        return
    
    await message.answer("В какой отдел отправляем заявку?", reply_markup=department_kb())
    await state.set_state(RequestStates.ChoosingDepartment)

@dp.message(RequestStates.ChoosingDepartment, F.photo | F.video | F.document | F.voice | F.sticker | F.animation)
async def choose_department_media(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, выберите отдел из списка, нажав на соответствующую кнопку", reply_markup=department_kb())

@dp.message(RequestStates.ChoosingDepartment)
async def choose_department(message: Message, state: FSMContext):
    if message.text is None:
        await message.answer("Пожалуйста, выберите отдел из списка, нажав на соответствующую кнопку", reply_markup=department_kb())
        return
        
    text = message.text.strip()
    if text == "ОТМЕНА":
        await cmd_start(message, state)
        return
    if text not in departments:
        await message.answer("Пожалуйста, выберите отдел из списка")
        return
    await state.update_data(department=departments[text])
    await message.answer("Укажите адрес точки", reply_markup=cancel_kb)
    await state.set_state(RequestStates.EnterAddress)

@dp.message(RequestStates.EnterAddress, F.photo | F.video | F.document | F.voice | F.sticker | F.animation)
async def address_step_media(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, введите адрес точки текстом", reply_markup=cancel_kb)

@dp.message(RequestStates.EnterAddress)
async def address_step(message: Message, state: FSMContext):
    if message.text is None:
        await message.answer("Пожалуйста, введите адрес точки текстом", reply_markup=cancel_kb)
        return
        
    text = message.text.strip()
    if text == "ОТМЕНА":
        await cmd_start(message, state)
        return
    if not re.fullmatch(r"[А-Яа-яA-Za-z0-9\s\-]+", text):
        await message.answer("Адрес указан некорректно, введите правильный адрес", reply_markup=cancel_kb)
        return
    await state.update_data(address=text)
    user_data = await state.get_data()
    if user_data.get("department") == "letter":
        await message.answer("Укажите ИП точки", reply_markup=cancel_kb)
        await state.set_state(RequestStates.EnterIP)
    else:
        await message.answer("Укажите рабочий номер телефона точки", reply_markup=cancel_kb)
        await state.set_state(RequestStates.EnterPhone)

@dp.message(RequestStates.EnterIP, F.photo | F.video | F.document | F.voice | F.sticker | F.animation)
async def enter_ip_media(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, введите ИП точки текстом", reply_markup=cancel_kb)

@dp.message(RequestStates.EnterIP)
async def enter_ip(message: Message, state: FSMContext):
    if message.text is None:
        await message.answer("Пожалуйста, введите ИП точки текстом", reply_markup=cancel_kb)
        return
        
    text = message.text.strip()
    if text == "ОТМЕНА":
        await cmd_start(message, state)
        return
    # Validate IP format - simple check for non-empty string with alphanumeric characters
    if not re.fullmatch(r"[А-Яа-яA-Za-z0-9\s\-]+", text):
        await message.answer("ИП указан некорректно, введите правильный ИП", reply_markup=cancel_kb)
        return
    await state.update_data(ip=text)
    await message.answer("Укажите рабочий номер телефона точки", reply_markup=cancel_kb)
    await state.set_state(RequestStates.EnterPhone)

@dp.message(RequestStates.EnterPhone, F.photo | F.video | F.document | F.voice | F.sticker | F.animation)
async def phone_step_media(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, введите номер телефона текстом", reply_markup=cancel_kb)

@dp.message(RequestStates.EnterPhone)
async def phone_step(message: Message, state: FSMContext):
    if message.text is None:
        await message.answer("Пожалуйста, введите номер телефона текстом", reply_markup=cancel_kb)
        return
        
    text = message.text.strip()
    if text == "ОТМЕНА":
        await cmd_start(message, state)
        return
    if not re.fullmatch(r"\+?\d{7,15}", text):
        await message.answer("Укажите корректный номер телефона", reply_markup=cancel_kb)
        return
    await state.update_data(phone=text)
    user_data = await state.get_data()
    dep = user_data.get("department")
    if dep == "letter":
        prompt = "Что необходимо сделать?"
    elif dep == "thoughts":
        prompt = "Что скажете?"
    else:
        prompt = "Опишите проблему"
    await message.answer(prompt, reply_markup=cancel_kb)
    await state.set_state(RequestStates.DescribeProblem)

@dp.message(RequestStates.DescribeProblem, F.photo | F.video | F.document | F.voice | F.sticker | F.animation)
async def description_step_media(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, опишите проблему текстом", reply_markup=cancel_kb)

@dp.message(RequestStates.DescribeProblem)
async def description_step(message: Message, state: FSMContext):
    if message.text is None:
        await message.answer("Пожалуйста, опишите проблему текстом", reply_markup=cancel_kb)
        return
        
    text = message.text.strip()
    if text == "ОТМЕНА":
        await cmd_start(message, state)
        return
    # Validate that problem description is not empty
    if not text:
        await message.answer("Пожалуйста, опишите проблему", reply_markup=cancel_kb)
        return
    await state.update_data(problem=text)
    user_data = await state.get_data()
    if user_data["department"] in ("internet", "thoughts"):
        await finish_request(message, state, with_photo=False)
    else:
        await message.answer("Прикрепите одну фотографию (видео нельзя, только фото)", reply_markup=cancel_kb)
        await state.set_state(RequestStates.WaitPhoto)

@dp.message(RequestStates.WaitPhoto, F.photo)
async def photo_step(message: Message, state: FSMContext):
    photo = message.photo[-1]
    await state.update_data(photo=photo.file_id)
    await finish_request(message, state, with_photo=True)

@dp.message(RequestStates.WaitPhoto, F.text == "ОТМЕНА")
async def cancel_photo(message: Message, state: FSMContext):
    await cmd_start(message, state)

@dp.message(RequestStates.WaitPhoto, F.video | F.document | F.voice | F.sticker | F.animation)
async def wait_photo_media(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, прикрепите одно фото (видео и другие типы файлов не поддерживаются)", reply_markup=cancel_kb)

@dp.message(RequestStates.WaitPhoto)
async def invalid_photo(message: Message, state: FSMContext):
    await message.answer("Прикрепите одно фото (видео нельзя, только фото)", reply_markup=cancel_kb)

async def finish_request(message: Message, state: FSMContext, with_photo: bool):
    try:
        data = await state.get_data()
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        user_info = f"{message.from_user.first_name}\n@{message.from_user.username or 'без username'}"
        parts = [f"Новая заявка {now}\n"]

        # Check if required data exists
        department = data.get("department")
        if not department:
            logger.error("Missing department in request data")
            await message.answer("Ошибка: не указан отдел. Пожалуйста, начните заново.", reply_markup=start_kb)
            await state.clear()
            return

        if department == "letter":
            ip = data.get("ip")
            if not ip:
                logger.error("Missing IP in request data for letter department")
                await message.answer("Ошибка: не указан ИП. Пожалуйста, начните заново.", reply_markup=start_kb)
                await state.clear()
                return
            parts.append(f"ИП: {ip}")

        address = data.get("address")
        if not address:
            logger.error("Missing address in request data")
            await message.answer("Ошибка: не указан адрес. Пожалуйста, начните заново.", reply_markup=start_kb)
            await state.clear()
            return
        parts.append(f"Адрес точки: {address}")

        phone = data.get("phone")
        if not phone:
            logger.error("Missing phone in request data")
            await message.answer("Ошибка: не указан телефон. Пожалуйста, начните заново.", reply_markup=start_kb)
            await state.clear()
            return
        parts.append(f"Номер телефона: {phone}\n")

        problem = data.get("problem")
        if not problem:
            logger.error("Missing problem description in request data")
            await message.answer("Ошибка: не указана проблема. Пожалуйста, начните заново.", reply_markup=start_kb)
            await state.clear()
            return
        parts.append(f"Текст заявки: {problem}")

        # Сформируем ключ содержимого без времени — для защиты от мгновенных повторов
        content_key = f"{message.from_user.id}|{department}|{address}|{phone}|{problem}"

        # Антидубликат по содержимому: если такая заявка уже была недавно — не дублируем
        ts_now = time.time()
        # Ленивая очистка кэшей
        if (len(PROCESSED_REQUESTS) + len(PROCESSED_CONTENT)) > DEDUP_MAX_SIZE:
            # Удаляем просроченные записи
            for rid, ts in list(PROCESSED_REQUESTS.items()):
                if ts_now - ts > DEDUP_TTL_SECONDS:
                    PROCESSED_REQUESTS.pop(rid, None)
            for ckey, (ts, _) in list(PROCESSED_CONTENT.items()):
                if ts_now - ts > DEDUP_TTL_SECONDS:
                    PROCESSED_CONTENT.pop(ckey, None)

        if content_key in PROCESSED_CONTENT:
            ts_prev, prev_id = PROCESSED_CONTENT[content_key]
            if ts_now - ts_prev <= DEDUP_TTL_SECONDS:
                logger.info(f"Duplicate request (by content) suppressed: {prev_id}")
                await message.answer(
                    "Похоже, такая же заявка уже была отправлена недавно. "
                    f"Дубликат не создаём.\n\nID существующей заявки: {prev_id}",
                    reply_markup=start_kb
                )
                await state.clear()
                return

        # Генерируем стабильный ID заявки на основе даты (день), пользователя и содержимого заявки (включая минуту)
        day_str = datetime.now().strftime('%Y%m%d')
        minute_str = datetime.now().strftime('%Y%m%d%H%M')
        key_str = f"{message.from_user.id}|{department}|{address}|{phone}|{problem}|{minute_str}"
        digest = int.from_bytes(hashlib.sha1(key_str.encode('utf-8')).digest(), 'big')
        suffix = str(digest % 10**10)  # 10-значный числовой хвост
        request_id = f"{day_str}-{message.from_user.id}-{suffix}"

        # Зафиксируем как обработанную заявку
        PROCESSED_REQUESTS[request_id] = ts_now
        PROCESSED_CONTENT[content_key] = (ts_now, request_id)
        
        parts.append(f"\nID заявки: {request_id}")
        parts.append("\nИнформация об отправителе")
        parts.append(f"Отправитель: {user_info}")
        parts.append(f"user_id: {message.from_user.id}")

        # Добавим ИП, почту и ИНН из файла по user_id, если доступны
        try:
            extra = get_sender_extra_info(str(message.from_user.id))
        except Exception as e:
            extra = None
            logger.warning(f"Не удалось получить доп. данные отправителя: {e}")
        if extra:
            ip_val = extra.get("ip")
            email_val = extra.get("email")
            inn_val = extra.get("inn")
            if any([ip_val, email_val, inn_val]):
                parts.append("\nДоп. данные отправителя")
                if ip_val:
                    parts.append(f"ИП: {ip_val}")
                if email_val:
                    parts.append(f"Почта: {email_val}")
                if inn_val:
                    parts.append(f"ИНН: {inn_val}")

        text = "\n".join(parts)
        # Сообщение пользователю об успешной отправке
        if department == "thoughts":
            success_text = (
                "✅ Готово! Ваше предложение отправлено в офис.\n"
                "Спасибо, что делитесь идеями — это помогает нам делать UPPETIT лучше 💛"
            )
        else:
            success_text = "Заявка успешно сформирована и отправлена!"
        await message.answer(f"{success_text}\n\nID заявки: {request_id}", reply_markup=start_kb)

        target_chat = CHAT_IDS.get(department)
        if not target_chat:
            logger.error(f"Missing target chat for department {department}")
            target_chat = CHAT_IDS.get("all", "")  # Fallback to "all" chat or empty string

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Принять", callback_data=f"accept_{message.from_user.id}")
        builder.button(text="❌ Коммент", callback_data="request_comment")
        builder.button(text="↪️ Передать", callback_data="transfer_request")
        markup = builder.as_markup()

        if with_photo:
            photo = data.get("photo")
            if not photo:
                logger.error("Missing photo in request data")
                await message.answer("Ошибка: фото не найдено. Отправляем заявку без фото.")
                try:
                    sent1 = await bot.send_message(target_chat, text, reply_markup=markup)
                except Exception as e:
                    logger.error(f"Error sending message to target chat: {e}")
                    # If target chat is not available, send to "all" chat with markup
                    sent1 = await bot.send_message(CHAT_IDS["all"], text, reply_markup=markup)
                sent2 = await bot.send_message(CHAT_IDS["all"], text)
            else:
                try:
                    sent1 = await bot.send_photo(target_chat, photo=photo, caption=text, reply_markup=markup)
                except Exception as e:
                    logger.error(f"Error sending photo to target chat: {e}")
                    # If sending photo fails, try sending as message
                    try:
                        sent1 = await bot.send_message(target_chat, text, reply_markup=markup)
                        # Try to send photo separately
                        await bot.send_photo(target_chat, photo=photo)
                    except Exception as e2:
                        logger.error(f"Error sending message to target chat: {e2}")
                        # If target chat is not available, send to "all" chat with markup
                        sent1 = await bot.send_message(CHAT_IDS["all"], text, reply_markup=markup)
                try:
                    sent2 = await bot.send_photo(CHAT_IDS["all"], photo=photo, caption=text)
                except Exception as e:
                    logger.error(f"Error sending photo to all chat: {e}")
                    sent2 = await bot.send_message(CHAT_IDS["all"], text)
        else:
            try:
                sent1 = await bot.send_message(target_chat, text, reply_markup=markup)
            except Exception as e:
                logger.error(f"Error sending message to target chat: {e}")
                # If target chat is not available, send to "all" chat with markup
                sent1 = await bot.send_message(CHAT_IDS["all"], text, reply_markup=markup)
            sent2 = await bot.send_message(CHAT_IDS["all"], text)
        # перед state.clear()
        with open("logs.txt", "a", encoding="utf-8") as log_file:
            log_file.write(text + "\n\n" + "-" * 50 + "\n\n")
            
        # Логирование заявки в Google Sheets
        try:
            # Получаем название отдела для отображения
            department_name = next((name for name, code in departments.items() if code == department), department)
            
            # Формируем имя отправителя
            sender_name = f"{message.from_user.first_name}"
            if message.from_user.last_name:
                sender_name += f" {message.from_user.last_name}"
            if message.from_user.username:
                sender_name += f" (@{message.from_user.username})"
                
            # ID заявки уже сгенерирован выше
            
            # Логируем заявку
            log_request(
                date=now,
                department=department_name,
                address=address,
                phone=phone,
                problem=problem,
                status="Новая",
                request_id=request_id,
                sender_name=sender_name,
                sender_id=message.from_user.id
            )
            logger.info(f"Request logged to Google Sheets: {request_id}")
        except Exception as e:
            logger.error(f"Error logging request to Google Sheets: {e}")
    except Exception as e:
        logger.exception(f"Error in finish_request: {e}")
        await message.answer("Произошла ошибка при отправке заявки. Пожалуйста, попробуйте еще раз.", reply_markup=start_kb)
        await state.clear()
        return

    await state.clear()

if __name__ == "__main__":
    print("✅ Бот запущен!")
    asyncio.run(main())
