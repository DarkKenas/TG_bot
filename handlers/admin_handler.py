from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging

from db_handler import PostgresHandler
from keyboards.main_menu_keyboards import BUTTON_ADMIN_PANEL
from keyboards.admin_keyboards import (
    get_admin_main_keyboard,
    get_confirm_action_keyboard,
    DELETE_USER,
    SET_ACTIVE_COLLECTOR,
)
from keyboards.collector_keyboards import get_collector_create_keyboard
from states.user_states import AdminStates
from db_handler.models import Collector
from exceptions import RecordNotFound, StateDataError
from .services.service_user_list import get_user_dict_from_state, get_user_id_by_num

admin_router = Router()
logger = logging.getLogger(__name__)

MSG_NO_ADMIN = "❌ У вас нет прав администратора"
MSG_SESSION_EXPIRED = "❌ Сессия админ панели устарела"
MSG_INVALID_NUMBER = "❌ Неверный номер. Введите число из списка:\n{nums}"
MSG_USER_NOT_FOUND = "❌ Пользователь не найден в БД.\nПопробуйте ещё раз ввести номер:"
MSG_USER_LIST_EMPTY = "📋 <b>Список пользователей пуст</b>"
MSG_ERROR_CREATING_LIST = "❌ Ошибка при создании списка пользователей"
MSG_ERROR_ASSIGN_COLLECTOR = "❌ Ошибка при назначении ответственного за сбор"
MSG_ERROR_DELETE_USER = "❌ Ошибка при удалении пользователя"


# =============== Главное меню админ панели ===============

@admin_router.message(F.text == BUTTON_ADMIN_PANEL)
async def show_admin_panel(
    message: Message,
    state: FSMContext,
    active_collector: Collector | None,
    db: PostgresHandler,
):
    """Показ главной админ панели"""
    try:
        users = await db.get_all_users()
        if not users:
            await message.answer("📋 <b>Список пользователей пуст</b>")
            return

        users.sort(key=lambda user: user.last_name)
        users_text = "📋 <b>Список всех пользователей:</b>\n"

        user_dict = {}
        for num, user in enumerate(users, 1):
            users_text += f"  {num}. {user.full_name}\n"
            user_dict[num] = user.user_id

        await state.update_data(user_dict=user_dict)

        if active_collector is not None:
            users_text += (
                "\n\n  Ответственный за сбор средств:\n"
                f"🟢 {active_collector.user.initials}"
            )

        await message.answer(
            "🔐 <b>Админ панель</b>\n"
            "👥 Управление пользователями\n\n" + users_text + "\nВыберите действие:",
            reply_markup=get_admin_main_keyboard(),
        )

    except Exception as e:
        logger.exception(f"Ошибка при создании списка пользователей: {e}")
        await message.answer("❌ Ошибка при создании списка пользователей")


# =============== Назначение активного коллектора ===============

@admin_router.callback_query(F.data == SET_ACTIVE_COLLECTOR)
async def set_active_collector(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "👤 Для назначения ответственного за сбор введите его номер согласно админ панели"
    )
    await state.set_state(AdminStates.waiting_for_collector_user_num)


@admin_router.message(AdminStates.waiting_for_collector_user_num)
async def process_active_collector(message: Message, state: FSMContext, db: PostgresHandler):
    try:
        user_dict = await get_user_dict_from_state(state)
    except StateDataError as e:
        logger.exception(e)
        await message.answer(MSG_SESSION_EXPIRED)
        await state.clear()
        return

    try:
        user_id = get_user_id_by_num(user_dict, message.text.strip())
        user = await db.get_user(user_id)
        await message.answer(
            f"Вы уверены, что хотите назначить <b>{user.full_name}</b> ответственным за сбор?",
            reply_markup=get_confirm_action_keyboard("set_collector", user_id),
        )
        await state.clear()
        return
    except ValueError:
        await message.answer(
            MSG_INVALID_NUMBER.format(nums=", ".join(map(str, user_dict.keys())))
        )
        return
    except RecordNotFound:
        await message.answer(MSG_USER_NOT_FOUND)
        return
    except Exception as e:
        logger.exception(f"Ошибка при назначении коллектора: {e}")
        await message.answer(MSG_ERROR_ASSIGN_COLLECTOR)
    await state.clear()


# =============== Удаление пользователя ===============

@admin_router.callback_query(F.data == DELETE_USER)
async def delete_user_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "👤 Для удаления пользователя введите его номер согласно админ панели"
    )
    await state.set_state(AdminStates.waiting_for_delete_user_num)


@admin_router.message(AdminStates.waiting_for_delete_user_num)
async def process_delete_user(message: Message, state: FSMContext, db: PostgresHandler):
    try:
        user_dict = await get_user_dict_from_state(state)
    except StateDataError as e:
        logger.exception(e)
        await message.answer(MSG_SESSION_EXPIRED)
        await state.clear()
        return

    try:
        user_id = get_user_id_by_num(user_dict, message.text.strip())
        user = await db.get_user(user_id)
        if user.administrator or user.service_user:
            await message.answer("🛑 Вы не можете удалить данного пользователя")
            await state.clear()
            return
        await message.answer(
            f"Вы уверены, что хотите удалить пользователя <b>{user.full_name}</b>?",
            reply_markup=get_confirm_action_keyboard("delete_user", user_id),
        )
        await state.clear()
        return
    except ValueError:
        await message.answer(
            MSG_INVALID_NUMBER.format(nums=", ".join(map(str, user_dict.keys())))
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

@admin_router.callback_query(F.data.regexp(r"^confirm_(\w+):(\d+)$"))
async def confirm_action_callback(
    callback: CallbackQuery, state: FSMContext, db: PostgresHandler
):
    import re

    match = re.match(r"^confirm_(\w+):(\d+)$", callback.data)
    if not match:
        await callback.answer("Некорректный запрос", show_alert=True)
        return

    action_type, target_id = match.group(1), int(match.group(2))

    if action_type == "delete_user":
        try:
            user = await db.get_user(target_id)
            await db.delete_user(target_id)
            await callback.message.edit_text(
                f"🗑 Пользователь <b>{user.full_name}</b> успешно удалён."
            )
        except RecordNotFound:
            await callback.message.edit_text(MSG_USER_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Ошибка при удалении пользователя: {e}")
            await callback.message.edit_text(MSG_ERROR_DELETE_USER)

    elif action_type == "set_collector":
        try:
            user = await db.get_user(target_id)
            try:
                active_collector = await db.set_active_collector(target_id)
                await callback.message.edit_text(
                    f"✅ Пользователь: <b>{user.full_name}</b>\n"
                    "Назначен ответственным за сбор средств 💰\n\n"
                    "Новые данные для перевода:\n"
                    f"📱 Телефон: <code>{active_collector.phone_number}</code>\n"
                    f"🏦 Банк: {active_collector.bank_name or 'не указан'}"
                )
            except RecordNotFound:
                await callback.bot.send_message(
                    target_id,
                    "🔧 Администратор назначил Вас ответственным за сбор средств 💰 на подарки 🎁\n\n"
                    "Пожалуйста, укажите реквизиты для переводов:",
                    reply_markup=get_collector_create_keyboard(),
                )
                await callback.message.edit_text(
                    f"👤 Пользователю <b>{user.full_name}</b> отправлен запрос "
                    "на регистрацию данных для сбора средств\n\n"
                    "⏰ Вам придет уведомление, когда данные будут получены..."
                )
        except Exception as e:
            logger.exception(f"Ошибка при назначении коллектора: {e}")
            await callback.message.edit_text(MSG_ERROR_ASSIGN_COLLECTOR)
    else:
        await callback.answer(
            f"Действие '{action_type}' не поддерживается", show_alert=True
        )
    await state.clear()


@admin_router.callback_query(F.data == "cancel")
async def cancel_action_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Действие отменено.")
    await state.clear()
