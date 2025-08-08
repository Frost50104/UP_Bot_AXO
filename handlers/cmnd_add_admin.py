from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re
import logging
import os

from config import ADMINS, CHAT_IDS

router = Router()
logger = logging.getLogger(__name__)

# Define states for adding admin
class AddAdminStates(StatesGroup):
    WaitingForAdminID = State()

@router.message(lambda message: message.text and re.match(r"^\/add_admin(@\w+)?$", message.text))
async def cmd_add_admin(message: Message):
    # Check if command is executed in a department chat
    if message.chat.id in CHAT_IDS.values():
        await message.answer("Эта операция доступна только внутри самого бота")
        return
        
    # Check if user is admin
    if message.from_user.id not in ADMINS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    
    # Get admin usernames
    admin_names = []
    for admin_id in ADMINS:
        try:
            # Try to get user info from Telegram
            admin = await message.bot.get_chat(admin_id)
            admin_name = admin.username or f"ID: {admin_id}"
            admin_names.append(admin_name)
        except Exception as e:
            logger.error(f"Error getting admin info for ID {admin_id}: {e}")
            admin_names.append(f"ID: {admin_id}")
    
    # Create message with admin list
    admin_list = "\n".join([f"• @{name}" if not name.startswith("ID: ") else f"• {name}" for name in admin_names])
    message_text = f"Текущий список администраторов:\n{admin_list}\n\nХотите добавить нового администратора?"
    
    # Create inline keyboard with Yes/No buttons
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data="add_admin_yes")
    builder.button(text="❌ Нет", callback_data="add_admin_no")
    builder.adjust(2)  # Two buttons in one row
    
    await message.answer(message_text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "add_admin_no")
async def cancel_add_admin(callback: CallbackQuery):
    await callback.message.edit_text("Добавление нового администратора отменено")
    await callback.answer()

@router.callback_query(F.data == "add_admin_yes")
async def confirm_add_admin(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ Укажите ID нового администратора:")
    await state.set_state(AddAdminStates.WaitingForAdminID)
    await callback.answer()

@router.message(AddAdminStates.WaitingForAdminID)
async def process_admin_id(message: Message, state: FSMContext):
    # Get the admin ID from the message
    admin_id_text = message.text.strip()
    
    # Validate that the ID consists only of digits
    if not re.fullmatch(r"\d+", admin_id_text):
        await message.answer("ID должен состоять только из цифр. Пожалуйста, укажите корректный ID.")
        return
    
    # Convert to integer
    new_admin_id = int(admin_id_text)
    
    # Check if the ID is already in the admin list
    if new_admin_id in ADMINS:
        await message.answer(f"ID {new_admin_id} уже есть в списке администраторов.")
        await state.clear()
        return
    
    # Add the new admin ID to the ADMINS list in config.py
    try:
        # Read the current config file
        with open("config.py", "r", encoding="utf-8") as config_file:
            config_content = config_file.read()
        
        # Find the ADMINS list in the config
        admins_pattern = r"ADMINS\s*=\s*\[(.*?)\]"
        admins_match = re.search(admins_pattern, config_content, re.DOTALL)
        
        if admins_match:
            # Get the current admin list content
            current_admins = admins_match.group(1)
            
            # Add the new admin ID to the list
            if current_admins.strip():
                # If there are existing admins, add a comma and the new ID
                new_admins = current_admins + f", {new_admin_id}"
            else:
                # If the list is empty, just add the new ID
                new_admins = str(new_admin_id)
            
            # Replace the old admin list with the new one
            new_config = re.sub(admins_pattern, f"ADMINS = [{new_admins}]", config_content, flags=re.DOTALL)
            
            # Write the updated config back to the file
            with open("config.py", "w", encoding="utf-8") as config_file:
                config_file.write(new_config)
            
            # Update the ADMINS list in memory
            ADMINS.append(new_admin_id)
            
            # Get updated admin usernames
            admin_names = []
            for admin_id in ADMINS:
                try:
                    # Try to get user info from Telegram
                    admin = await message.bot.get_chat(admin_id)
                    admin_name = admin.username or f"ID: {admin_id}"
                    admin_names.append(admin_name)
                except Exception as e:
                    logger.error(f"Error getting admin info for ID {admin_id}: {e}")
                    admin_names.append(f"ID: {admin_id}")
            
            # Create message with updated admin list
            admin_list = "\n".join([f"• @{name}" if not name.startswith("ID: ") else f"• {name}" for name in admin_names])
            confirmation_text = f"Администратор с ID {new_admin_id} успешно добавлен!\n\nОбновленный список администраторов:\n{admin_list}"
            
            await message.answer(confirmation_text)
            logger.info(f"Added new admin with ID {new_admin_id}")
        else:
            await message.answer("Ошибка: не удалось найти список администраторов в конфигурационном файле.")
            logger.error("Could not find ADMINS list in config.py")
    except Exception as e:
        await message.answer(f"Произошла ошибка при добавлении администратора: {str(e)}")
        logger.exception(f"Error adding new admin: {e}")
    
    # Clear the state
    await state.clear()