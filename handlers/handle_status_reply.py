from aiogram import Router, Bot
from aiogram.types import Message
import re
import logging
from google_sheets import update_request_status
from config import CHAT_IDS

router = Router()
logger = logging.getLogger(__name__)

@router.message(lambda m: m.reply_to_message and m.chat.id in CHAT_IDS.values())
async def handle_status_reply(message: Message, bot: Bot):
    """
    Обрабатывает ответы на сообщения бота в чатах отделов.
    Если ответ содержит "Завершено", статус заявки меняется на "Завершена".
    Если ответ содержит "Отклонить", статус заявки меняется на "Отклонена".
    Если ответ содержит "Принято" или "В работе", статус заявки меняется на "В работе".
    """
    # Проверяем, что сообщение отправлено ботом
    if not message.reply_to_message.from_user or not message.reply_to_message.from_user.is_bot:
        return
    
    # Проверяем содержимое ответа
    reply_text = message.text.strip().lower() if message.text else ""
    
    # Определяем новый статус на основе текста ответа
    new_status = None
    if "завершено" in reply_text:
        new_status = "Завершена"
        logger.info(f"Получен ответ 'Завершено' от пользователя {message.from_user.id}")
    elif "отклонить" in reply_text or "отклонено" in reply_text:
        new_status = "Отклонена"
        logger.info(f"Получен ответ 'Отклонить/Отклонено' от пользователя {message.from_user.id}")
    elif "принято" in reply_text or "в работе" in reply_text:
        new_status = "В работе"
        logger.info(f"Получен ответ 'Принято/В работе' от пользователя {message.from_user.id}")
    else:
        # Если ответ не содержит нужных ключевых слов, игнорируем его
        return
    
    # Извлекаем ID заявки и user_id из оригинального сообщения
    original_text = message.reply_to_message.text or message.reply_to_message.caption or ""
    request_id_match = re.search(r"ID заявки: ([^\n]+)", original_text)
    user_id_match = re.search(r"user_id: (\d+)", original_text)
    
    # Особая логика для отдела thoughts: для статуса "Завершена" сначала запрашиваем комментарий
    if new_status == "Завершена" and message.chat.id == CHAT_IDS.get("thoughts"):
        if not (request_id_match and user_id_match):
            logger.error("Для завершения в thoughts не удалось извлечь request_id или user_id")
            await message.reply("Не удалось подготовить завершение: отсутствуют данные заявки.")
            return
        request_id = request_id_match.group(1)
        user_id = user_id_match.group(1)
        try:
            await bot.send_message(
                chat_id=message.chat.id,
                reply_to_message_id=message.reply_to_message.message_id,
                text=(
                    "✏️ Ответьте на ЭТО сообщение, чтобы отправить комментарий\n\n"
                    f"user_id: {user_id}\n"
                    f"request_id: {request_id}\n"
                    f"status_after_comment: Завершена"
                )
            )
            logger.info(f"В чате thoughts запрошен комментарий для завершения заявки {request_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке подсказки для комментария: {e}")
            await message.reply("Не удалось отправить подсказку для комментария.")
        return

    if request_id_match:
        request_id = request_id_match.group(1)
        # Обновляем статус заявки
        success = update_request_status(request_id, new_status)
        if success:
            logger.info(f"Статус заявки {request_id} обновлен на '{new_status}'")
            # Отправляем уведомление пользователю
            if user_id_match:
                user_id = int(user_id_match.group(1))
                try:
                    if new_status == "Завершена":
                        status_message = "завершена"
                    elif new_status == "Отклонена":
                        status_message = "отклонена"
                    elif new_status == "В работе":
                        status_message = "принята в работу"
                    else:
                        status_message = f"изменен на '{new_status}'"
                    
                    await bot.send_message(user_id, f"Ваша заявка {request_id} {status_message}.")
                    logger.info(f"Уведомление о смене статуса отправлено пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления пользователю: {e}")
            
            # Если статус "Завершена" или "Отклонена", убираем inline-кнопки из оригинального сообщения
            if new_status in ["Завершена", "Отклонена"]:
                try:
                    await message.reply_to_message.edit_reply_markup(reply_markup=None)
                    logger.info(f"Inline-кнопки удалены из заявки {request_id} со статусом '{new_status}'")
                except Exception as e:
                    logger.error(f"Ошибка при удалении inline-кнопок: {e}")
            
            # Отправляем подтверждение в чат
            await message.reply(f"Статус заявки {request_id} изменен на '{new_status}'")
        else:
            logger.error(f"Не удалось обновить статус заявки {request_id}")
            await message.reply(f"Не удалось обновить статус заявки {request_id}")
    else:
        logger.error("Не удалось извлечь ID заявки из сообщения")
        await message.reply("Не удалось определить ID заявки в сообщении")