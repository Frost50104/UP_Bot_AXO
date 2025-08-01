from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re
import logging

from config import ADMINS

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "/delete_admin")
async def cmd_delete_admin(message: Message):
    # Check if user is admin
    if message.from_user.id not in ADMINS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    
    # Get admin usernames
    admin_names = []
    admin_info = []  # Store both ID and username
    
    for admin_id in ADMINS:
        try:
            # Try to get user info from Telegram
            admin = await message.bot.get_chat(admin_id)
            admin_name = admin.username or f"ID: {admin_id}"
            admin_names.append(admin_name)
            admin_info.append((admin_id, admin_name))
        except Exception as e:
            logger.error(f"Error getting admin info for ID {admin_id}: {e}")
            admin_names.append(f"ID: {admin_id}")
            admin_info.append((admin_id, f"ID: {admin_id}"))
    
    # Create message with admin list
    admin_list = "\n".join([f"• @{name}" if not name.startswith("ID: ") else f"• {name}" for name in admin_names])
    message_text = f"Текущий список администраторов:\n{admin_list}\n\nХотите удалить администратора?"
    
    # Create inline keyboard with buttons for each admin
    builder = InlineKeyboardBuilder()
    
    for admin_id, admin_name in admin_info:
        display_name = admin_name if admin_name.startswith("ID: ") else f"@{admin_name}"
        builder.button(text=display_name, callback_data=f"delete_admin_{admin_id}")
    
    builder.adjust(1)  # One button per row
    
    await message.answer(message_text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("delete_admin_"))
async def delete_admin_callback(callback: CallbackQuery):
    # Extract admin ID from callback data
    admin_id_str = callback.data.split("_")[2]
    admin_id = int(admin_id_str)
    
    # Check if the user who clicked is an admin
    if callback.from_user.id not in ADMINS:
        await callback.answer("У вас нет доступа к этой команде.", show_alert=True)
        return
    
    # Check if the admin ID exists in the list
    if admin_id not in ADMINS:
        await callback.answer("Этот администратор уже удален.", show_alert=True)
        return
    
    # Don't allow deleting the last admin
    if len(ADMINS) <= 1:
        await callback.message.edit_text("Нельзя удалить последнего администратора.")
        await callback.answer()
        return
    
    # Update the ADMINS list in config.py
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
            
            # Remove the admin ID from the list
            admin_id_pattern = r"(,\s*)?{}(,\s*)?".format(admin_id)
            
            # Handle different cases of admin ID position in the list
            if re.search(r"^\s*{}\s*,".format(admin_id), current_admins):  # At the beginning
                new_admins = re.sub(r"^\s*{}\s*,\s*".format(admin_id), "", current_admins)
            elif re.search(r",\s*{}\s*$".format(admin_id), current_admins):  # At the end
                new_admins = re.sub(r",\s*{}\s*$".format(admin_id), "", current_admins)
            else:  # In the middle
                new_admins = re.sub(r",\s*{}\s*,".format(admin_id), ", ", current_admins)
            
            # Replace the old admin list with the new one
            new_config = re.sub(admins_pattern, f"ADMINS = [{new_admins}]", config_content, flags=re.DOTALL)
            
            # Write the updated config back to the file
            with open("config.py", "w", encoding="utf-8") as config_file:
                config_file.write(new_config)
            
            # Update the ADMINS list in memory
            ADMINS.remove(admin_id)
            
            # Get updated admin usernames
            admin_names = []
            for remaining_admin_id in ADMINS:
                try:
                    # Try to get user info from Telegram
                    admin = await callback.bot.get_chat(remaining_admin_id)
                    admin_name = admin.username or f"ID: {remaining_admin_id}"
                    admin_names.append(admin_name)
                except Exception as e:
                    logger.error(f"Error getting admin info for ID {remaining_admin_id}: {e}")
                    admin_names.append(f"ID: {remaining_admin_id}")
            
            # Create message with updated admin list
            admin_list = "\n".join([f"• @{name}" if not name.startswith("ID: ") else f"• {name}" for name in admin_names])
            confirmation_text = f"Администратор успешно удален!\n\nОбновленный список администраторов:\n{admin_list}"
            
            await callback.message.edit_text(confirmation_text)
            logger.info(f"Removed admin with ID {admin_id}")
        else:
            await callback.answer("Ошибка: не удалось найти список администраторов в конфигурационном файле.", show_alert=True)
            logger.error("Could not find ADMINS list in config.py")
    except Exception as e:
        await callback.answer(f"Произошла ошибка при удалении администратора.", show_alert=True)
        logger.exception(f"Error removing admin: {e}")
    
    await callback.answer()