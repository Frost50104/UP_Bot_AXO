from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
import re
import logging
from config import CHAT_IDS
from google_sheets import update_request_department

router = Router()
logger = logging.getLogger(__name__)

# Dictionary of departments with their display names and identifiers
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

@router.callback_query(F.data == "transfer_request")
async def transfer_request(callback: CallbackQuery):
    """Handle the transfer button click by showing department selection buttons"""
    try:
        # Create inline keyboard with department buttons
        builder = InlineKeyboardBuilder()
        for name, code in departments.items():
            builder.button(text=name, callback_data=f"dept_{code}")
        markup = builder.adjust(2).as_markup()
        
        # Edit the message to show department selection buttons
        await callback.message.edit_reply_markup(reply_markup=markup)
        await callback.answer("Выберите отдел для передачи заявки")
    except Exception as e:
        logger.error(f"Error in transfer_request: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data.startswith("dept_"))
async def forward_to_department(callback: CallbackQuery, bot):
    """Handle department selection and forward the request to the selected department"""
    try:
        # Extract department code from callback data
        dept_code = callback.data.replace("dept_", "")
        target_chat_id = CHAT_IDS.get(dept_code)
        
        if not target_chat_id:
            await callback.answer(f"Чат для отдела {dept_code} не найден", show_alert=True)
            return
        
        # Get the original message content
        content = callback.message.caption or callback.message.text or ""
        
        # Create accept and comment buttons for the forwarded message
        builder = InlineKeyboardBuilder()
        
        # Extract user_id from the message
        user_id_match = re.search(r"user_id:\s*(\d+)", content)
        if user_id_match:
            user_id = user_id_match.group(1)
            builder.button(text="✅ Принять", callback_data=f"accept_{user_id}")
        else:
            # Fallback if user_id not found
            builder.button(text="✅ Принять", callback_data="accept_0")
            
        builder.button(text="❌ Коммент", callback_data="request_comment")
        markup = builder.as_markup()
        
        # Extract request_id from the message
        request_id_match = re.search(r"ID заявки: ([^\n]+)", content)
        if request_id_match:
            request_id = request_id_match.group(1)
            # Get department name for Google Sheets update
            dept_name = next((name for name, code in departments.items() if code == dept_code), dept_code)
            
            # Update department in Google Sheets
            success = update_request_department(request_id, dept_name)
            if success:
                logger.info(f"Отдел заявки {request_id} обновлен на '{dept_name}'")
            else:
                logger.error(f"Не удалось обновить отдел заявки {request_id}")
        else:
            logger.error("Не удалось извлечь ID заявки из сообщения")
        
        # Forward the message to the selected department
        if callback.message.photo:
            # Get the largest photo (best quality)
            photo = callback.message.photo[-1]
            # Forward with photo
            await bot.send_photo(
                chat_id=target_chat_id,
                photo=photo.file_id,
                caption=content,
                reply_markup=markup
            )
        else:
            # Forward as text
            await bot.send_message(
                chat_id=target_chat_id,
                text=content,
                reply_markup=markup
            )
        
        # Update the original message to remove buttons
        await callback.message.edit_reply_markup(reply_markup=None)
        
        # Get department name for the confirmation message
        dept_name = next((name for name, code in departments.items() if code == dept_code), dept_code)
        await callback.answer(f"Заявка передана в отдел: {dept_name}", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error in forward_to_department: {e}")
        await callback.answer("Произошла ошибка при передаче заявки", show_alert=True)