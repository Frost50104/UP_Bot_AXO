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
    
    # Извлекаем ID заявки и желаемый статус после комментария из подсказки
    request_id_match = re.search(r"request_id:\s*([^\n]+)", content)
    request_id = request_id_match.group(1).strip() if (request_id_match and request_id_match.group(1).strip()) else None
    if request_id:
        logger.info(f"📝 Найден ID заявки: {request_id}")
    else:
        logger.warning("❌ ID заявки не найден в подсказке или пустой")

    status_after_match = re.search(r"status_after_comment:\s*([^\n]+)", content)
    status_after_comment = status_after_match.group(1).strip() if status_after_match else None

    try:
        await bot.send_message(user_id, f"Комментарий по вашей заявке:\n\n{message.text}")
        # Отправка комментария успешна — теперь обновляем статус, если требуется
        status_update_note = ""
        if status_after_comment and request_id:
            success = update_request_status(request_id, status_after_comment)
            if success:
                status_update_note = f" Статус заявки {request_id} изменен на '{status_after_comment}'."
                logger.info(f"✅ Статус заявки {request_id} обновлен на '{status_after_comment}' после комментария")
            else:
                logger.error(f"❌ Не удалось обновить статус заявки {request_id} на '{status_after_comment}' после комментария")
        elif request_id:
            # Старое поведение: если специального статуса нет, трактуем как отклонение
            success = update_request_status(request_id, "Отклонена")
            if success:
                status_update_note = f" Статус заявки {request_id} изменен на 'Отклонена'."
                logger.info(f"✅ Статус заявки {request_id} обновлен на 'Отклонена'")
            else:
                logger.error(f"❌ Не удалось обновить статус заявки {request_id}")

        # Попробуем убрать inline-кнопки у исходного сообщения, если это возможно (когда статус изменён)
        try:
            if status_after_comment or (request_id and status_update_note):
                # исходное сообщение — это то, на которое бот отправил подсказку
                # подсказка была ответом на исходное сообщение, попробуем снять клавиатуру у исходного
                original = getattr(message.reply_to_message, "reply_to_message", None)
                if original:
                    await bot.edit_message_reply_markup(chat_id=message.chat.id, message_id=original.message_id, reply_markup=None)
        except Exception as e:
            logger.error(f"❌ Не удалось удалить inline-кнопки исходного сообщения: {e}")

        # Подтверждение в чат отдела
        await bot.send_message(message.chat.id, f"✅ Комментарий отправлен.{status_update_note}".strip())
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
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке комментария: {e}")