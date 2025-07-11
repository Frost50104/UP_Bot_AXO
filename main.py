import logging
import sys
import re
import asyncio
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

# Подключение роутера
dp.include_router(cmnd_show_logs.router)
dp.include_router(cmnd_clear_logs.router)
dp.include_router(cmnd_bot_events.router)
dp.include_router(cmnd_clear_bot_events.router)
dp.include_router(callback_accept_request.router)

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

departments = {
    "Интернет": "internet",
    "Касса/iiko": "iiko",
    "Камеры наблюдения": "cameras",
    "Холодильники / кондиционеры": "cold",
    "Компьютер / мышка / клавиатура": "pc",
    "Что-то другое сломалось": "other",
    "Баристика": "barista",
    "Буква": "letter"
}

def department_kb():
    builder = ReplyKeyboardBuilder()
    for name in departments.keys():
        builder.button(text=name)
    builder.button(text="ОТМЕНА")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Привет, я бот UPPETIT 2.0, если у Вас появилась проблема - я помогу её решить", reply_markup=start_kb)

@dp.message(F.text == "НОВАЯ ЗАЯВКА")
async def new_request(message: Message, state: FSMContext):
    await message.answer("В какой отдел отправляем заявку?", reply_markup=department_kb())
    await state.set_state(RequestStates.ChoosingDepartment)

@dp.message(RequestStates.ChoosingDepartment)
async def choose_department(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "ОТМЕНА":
        await cmd_start(message, state)
        return
    if text not in departments:
        await message.answer("Пожалуйста, выберите отдел из списка")
        return
    await state.update_data(department=departments[text])
    await message.answer("Укажите адрес точки", reply_markup=ReplyKeyboardRemove())
    await state.set_state(RequestStates.EnterAddress)

@dp.message(RequestStates.EnterAddress)
async def address_step(message: Message, state: FSMContext):
    if not re.fullmatch(r"[А-Яа-яA-Za-z0-9\s\-]+", message.text.strip()):
        await message.answer("Адрес указан некорректно, введите правильный адрес")
        return
    await state.update_data(address=message.text.strip())
    user_data = await state.get_data()
    if user_data.get("department") == "letter":
        await message.answer("Укажите ИП точки")
        await state.set_state(RequestStates.EnterIP)
    else:
        await message.answer("Укажите рабочий номер телефона точки")
        await state.set_state(RequestStates.EnterPhone)

@dp.message(RequestStates.EnterIP)
async def enter_ip(message: Message, state: FSMContext):
    await state.update_data(ip=message.text.strip())
    await message.answer("Укажите рабочий номер телефона точки")
    await state.set_state(RequestStates.EnterPhone)

@dp.message(RequestStates.EnterPhone)
async def phone_step(message: Message, state: FSMContext):
    if not re.fullmatch(r"\+?\d{7,15}", message.text.strip()):
        await message.answer("Укажите корректный номер телефона")
        return
    await state.update_data(phone=message.text.strip())
    user_data = await state.get_data()
    text = "Что необходимо сделать?" if user_data.get("department") == "letter" else "Опишите проблему"
    await message.answer(text)
    await state.set_state(RequestStates.DescribeProblem)

@dp.message(RequestStates.DescribeProblem)
async def description_step(message: Message, state: FSMContext):
    await state.update_data(problem=message.text.strip())
    user_data = await state.get_data()
    if user_data["department"] == "internet":
        await finish_request(message, state, with_photo=False)
    else:
        await message.answer("Прикрепите одну фотографию (видео нельзя, только фото)")
        await state.set_state(RequestStates.WaitPhoto)

@dp.message(RequestStates.WaitPhoto, F.photo)
async def photo_step(message: Message, state: FSMContext):
    photo = message.photo[-1]
    await state.update_data(photo=photo.file_id)
    await finish_request(message, state, with_photo=True)

@dp.message(RequestStates.WaitPhoto)
async def invalid_photo(message: Message, state: FSMContext):
    await message.answer("Прикрепите одно фото (видео нельзя, только фото)")

async def finish_request(message: Message, state: FSMContext, with_photo: bool):
    data = await state.get_data()
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    user_info = f"{message.from_user.first_name}\n@{message.from_user.username or 'без username'}"
    parts = [f"Новая заявка {now}"]

    if data.get("department") == "letter":
        parts.append(f"ИП: {data['ip']}")
    parts.append(f"Адрес точки: {data['address']}")
    parts.append(f"Номер телефона: {data['phone']}")
    parts.append(f"Текст заявки: {data['problem']}")
    parts.append("\nИнформация об отправителе")
    parts.append(f"Отправитель: {user_info}")

    text = "\n".join(parts)
    await message.answer("Заявка успешно сформирована и отправлена!", reply_markup=start_kb)

    target_chat = CHAT_IDS.get(data["department"])
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"accept_{message.from_user.id}")
    markup = builder.as_markup()

    if with_photo:
        sent1 = await bot.send_photo(target_chat, photo=data["photo"], caption=text, reply_markup=markup)
        sent2 = await bot.send_photo(CHAT_IDS["all"], photo=data["photo"], caption=text)
    else:
        sent1 = await bot.send_message(target_chat, text, reply_markup=markup)
        sent2 = await bot.send_message(CHAT_IDS["all"], text)

    # перед state.clear()
    with open("logs.txt", "a", encoding="utf-8") as log_file:
        log_file.write(text + "\n\n" + "-" * 50 + "\n\n")

    await state.clear()

if __name__ == "__main__":
    print("✅ Бот запущен!")
    asyncio.run(main())