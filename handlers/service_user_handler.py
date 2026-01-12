from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging

from db_handler import PostgresHandler
from keyboards.admin_keyboards import get_confirm_action_keyboard
from states.user_states import ServiceStates
from exceptions import RecordNotFound, StateDataError
from .services.service_user_list import get_user_dict_from_state, get_user_id_by_num

service_user_router = Router()
logger = logging.getLogger(__name__)

MSG_SESSION_EXPIRED = "❌ Сессия админ панели устарела"
MSG_INVALID_NUMBER = "❌ Неверный номер. Введите число из списка:\n{nums}"
MSG_USER_NOT_FOUND = "❌ Админ не найден в БД.\nПопробуйте ещё раз ввести номер:"
MSG_ERROR_DELETE_USER = "❌ Ошибка при удалении админа"


@service_user_router.message(Command("admin_list"))
async def show_admin_list(message: Message, state: FSMContext, db: PostgresHandler):
    """Показ списка админов"""
    try:
        admins = await db.get_all_administrators()
        if not admins:
            await message.answer("📋 <b>Список админов пуст</b>")
            return

        admins.sort(key=lambda admin: admin.user.last_name)
        admins_text = "📋 <b>Список всех админов:</b>\n"

        admin_dict = {}
        for num, admin in enumerate(admins, 1):
            admins_text += f"  {num}. {admin.user.full_name}\n"
            admin_dict[num] = admin.user_id

        await state.update_data(user_dict=admin_dict)

        await message.answer(
            "👥 Управление админами\n\n" + admins_text + "\nДля удаления админа введите номер согласно списка",
        )
        await state.set_state(ServiceStates.waiting_for_delete_admin_num)

    except Exception as e:
        logger.exception(f"Ошибка при создании списка админов: {e}")
        await message.answer("❌ Ошибка при создании списка админов")


@service_user_router.message(ServiceStates.waiting_for_delete_admin_num)
async def process_delete_user(message: Message, state: FSMContext, db: PostgresHandler):
    try:
        admin_dict = await get_user_dict_from_state(state)
    except StateDataError as e:
        logger.exception(e)
        await message.answer(MSG_SESSION_EXPIRED)
        await state.clear()
        return

    try:
        admin_id = get_user_id_by_num(admin_dict, message.text.strip())
        admin = await db.get_administrator(admin_id)
        await message.answer(
            f"Вы уверены, что хотите забрать права админа <b>{admin.user.full_name}</b>?",
            reply_markup=get_confirm_action_keyboard("delete_admin", admin_id, role="service_"),
        )
        await state.clear()
        return
    except ValueError:
        await message.answer(
            MSG_INVALID_NUMBER.format(nums=", ".join(map(str, admin_dict.keys())))
        )
        return
    except RecordNotFound:
        await message.answer(MSG_USER_NOT_FOUND)
        return
    except Exception as e:
        logger.exception(f"Ошибка при удалении пользователя: {e}")
        await message.answer(MSG_ERROR_DELETE_USER)
    await state.clear()


# =============== Подтверждение действий ===============

@service_user_router.callback_query(F.data.regexp(r"^service_confirm_(\w+):(\d+)$"))
async def confirm_action_callback(
    callback: CallbackQuery, state: FSMContext, db: PostgresHandler
):
    import re

    match = re.match(r"^service_confirm_(\w+):(\d+)$", callback.data)
    if not match:
        await callback.answer("Некорректный запрос", show_alert=True)
        return

    action_type, target_id = match.group(1), int(match.group(2))

    if action_type == "delete_admin":
        try:
            admin = await db.get_administrator(target_id)
            await db.delete_administrator(target_id)
            await callback.message.edit_text(
                f"🗑 Права админа <b>{admin.user.full_name}</b> успешно удалены."
            )
        except RecordNotFound:
            await callback.message.edit_text(MSG_USER_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Ошибка при удалении пользователя: {e}")
            await callback.message.edit_text(MSG_ERROR_DELETE_USER)
    else:
        await callback.answer(
            f"Действие '{action_type}' не поддерживается", show_alert=True
        )
    await state.clear()


@service_user_router.callback_query(F.data == "cancel")
async def cancel_action_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Действие отменено.")
    await state.clear()
