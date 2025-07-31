from aiogram import Router, Bot
from aiogram.types import Message
import re
from aiogram.exceptions import TelegramBadRequest
import logging
from datetime import datetime
from google_sheets import update_request_status

router = Router()
logger = logging.getLogger(__name__)

@router.message(lambda m: m.reply_to_message and m.reply_to_message.text and "Ответьте на ЭТО сообщение" in m.reply_to_message.text)
async def handle_comment_reply(message: Message, bot: Bot):
    logger.info("💬 Получен ответ на сообщение-подсказку")

    # user_id теперь в подсказке
    content = message.reply_to_message.text
    match = re.search(r"user_id:\s*(\d+)", content)
    if not match:
        logger.warning("❌ user_id не найден в подсказке")
        return

    user_id = int(match.group(1))
    logger.info(f"📨 Отправляем комментарий пользователю user_id={user_id}")
    
    # Извлекаем ID заявки из подсказки
    request_id_match = re.search(r"request_id:\s*([^\n]+)", content)
    if request_id_match and request_id_match.group(1).strip():
        request_id = request_id_match.group(1).strip()
        logger.info(f"📝 Найден ID заявки: {request_id}")
        
        # Обновляем статус заявки на "Отклонена"
        success = update_request_status(request_id, "Отклонена")
        if success:
            logger.info(f"✅ Статус заявки {request_id} обновлен на 'Отклонена'")
        else:
            logger.error(f"❌ Не удалось обновить статус заявки {request_id}")
    else:
        logger.warning("❌ ID заявки не найден в подсказке или пустой")

    try:
        await bot.send_message(user_id, f"Комментарий по вашей заявке:\n\n{message.text}")
        # Send confirmation message to the department chat
        await bot.send_message(message.chat.id, "✅ Комментарий отправлен")
        logger.info("✅ Комментарий отправлен")
        
        # Логирование комментария в logs.txt
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        sender_name = f"{message.from_user.first_name}"
        if message.from_user.last_name:
            sender_name += f" {message.from_user.last_name}"
        if message.from_user.username:
            sender_name += f" (@{message.from_user.username})"
            
        log_text = f"Комментарий к заявке {now}\n"
        log_text += f"Текст комментария: {message.text}\n\n"
        log_text += f"Информация об отправителе\n"
        log_text += f"Отправитель: {sender_name}\n"
        log_text += f"user_id: {message.from_user.id}\n\n"
        log_text += f"Получатель: user_id {user_id}\n\n"
        
        with open("logs.txt", "a", encoding="utf-8") as log_file:
            log_file.write(log_text + "\n" + "-" * 50 + "\n\n")
    except TelegramBadRequest as e:
        logger.error(f"❌ Ошибка при отправке комментария: {e}")