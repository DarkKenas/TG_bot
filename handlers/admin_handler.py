from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging
import asyncio

from db_handler import PostgresHandler
from keyboards.main_menu_keyboards import BUTTON_ADMIN_PANEL, get_main_menu_keyboard
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
async def process_active_collector(
    message: Message, state: FSMContext, db: PostgresHandler
):
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
                # Обновляем меню пользователя, чтобы появилась кнопка панели коллектора
                try:
                    # Небольшая задержка, чтобы БД успела обновиться
                    await asyncio.sleep(0.1)

                    updated_user = await db.get_user(target_id)
                    is_collector = updated_user.is_collector
                    logger.info(
                        f"Обновление меню для пользователя {target_id}: "
                        f"is_admin={updated_user.is_admin}, is_collector={is_collector}, "
                        f"collector exists={updated_user.collector is not None}"
                    )

                    if not is_collector:
                        logger.warning(
                            f"⚠️ Пользователь {target_id} не определяется как коллектор после назначения! "
                            f"collector={updated_user.collector}"
                        )

                    await callback.bot.send_message(
                        target_id,
                        "🔔 Ваше меню обновлено! Теперь доступна 💰Сбор панель",
                        reply_markup=await get_main_menu_keyboard(
                            is_admin=updated_user.is_admin,
                            is_collector=is_collector,
                        ),
                    )
                except Exception as e:
                    logger.exception(
                        f"Не удалось обновить меню пользователя {target_id}: {e}"
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


# =============== Закрепление сообщений ===============


@admin_router.message(Command("pin_message"))
async def pin_message_start(message: Message, state: FSMContext):
    """Начало процесса закрепления сообщения"""
    await message.answer(
        "📌 Введите сообщение, которое нужно закрепить и разослать всем пользователям:"
    )
    await state.set_state(AdminStates.waiting_for_pin_message)


@admin_router.message(AdminStates.waiting_for_pin_message)
async def process_pin_message(
    message: Message, state: FSMContext, db: PostgresHandler
):
    """Обработка сообщения для закрепления и рассылки"""
    try:
        bot = message.bot
        # Получаем текст сообщения
        message_text = message.text or message.caption or ""
        if not message_text and not message.photo and not message.document:
            await message.answer("❌ Сообщение не может быть пустым.")
            return

        # Получаем всех зарегистрированных пользователей
        users = await db.get_all_users()
        if not users:
            await message.answer("❌ Нет зарегистрированных пользователей.")
            await state.clear()
            return

        # Рассылаем сообщение всем пользователям
        success_count = 0
        failed_count = 0
        pinned_count = 0

        for user in users:
            try:
                # Отправляем сообщение
                if message.photo:
                    sent_msg = await bot.send_photo(
                        chat_id=user.user_id,
                        photo=message.photo[-1].file_id,
                        caption=message_text if message_text else None,
                    )
                elif message.document:
                    sent_msg = await bot.send_document(
                        chat_id=user.user_id,
                        document=message.document.file_id,
                        caption=message_text if message_text else None,
                    )
                else:
                    sent_msg = await bot.send_message(
                        chat_id=user.user_id, text=message_text
                    )

                # Пытаемся закрепить сообщение (работает только в группах/каналах)
                # В личных чатах закрепление невозможно через Bot API
                try:
                    await bot.pin_chat_message(
                        chat_id=user.user_id, message_id=sent_msg.message_id
                    )
                    pinned_count += 1
                except Exception:
                    # Игнорируем ошибки закрепления (например, в личных чатах)
                    pass

                success_count += 1
            except Exception as e:
                failed_count += 1
                error_msg = str(e).lower()
                if "blocked" in error_msg or "chat not found" in error_msg:
                    logger.warning(
                        f"Пользователь {user.user_id} заблокировал бота или чат не найден"
                    )
                elif "forbidden" in error_msg:
                    logger.warning(f"Нет доступа к пользователю {user.user_id}")
                else:
                    logger.exception(
                        f"Ошибка отправки сообщения пользователю {user.user_id}: {e}"
                    )

        # Отправляем отчет админу
        report = (
            f"✅ Сообщение разослано:\n"
            f"📤 Успешно отправлено: {success_count}\n"
            f"❌ Ошибок: {failed_count}\n"
            f"📌 Закреплено: {pinned_count}"
        )
        await message.answer(report)
        await state.clear()

    except Exception as e:
        logger.exception(f"Ошибка при рассылке сообщения: {e}")
        await message.answer("❌ Произошла ошибка при рассылке сообщения.")
        await state.clear()


@admin_router.message(Command("unpin"))
async def unpin_message(message: Message, db: PostgresHandler):
    """Открепить все закрепленные сообщения у всех пользователей"""
    try:
        bot = message.bot
        users = await db.get_all_users()
        if not users:
            await message.answer("❌ Нет зарегистрированных пользователей.")
            return

        success_count = 0
        failed_count = 0

        for user in users:
            try:
                await bot.unpin_all_chat_messages(chat_id=user.user_id)
                success_count += 1
            except Exception as e:
                failed_count += 1
                error_msg = str(e).lower()
                if "blocked" in error_msg or "chat not found" in error_msg:
                    logger.warning(
                        f"Пользователь {user.user_id} заблокировал бота или чат не найден"
                    )
                elif "forbidden" in error_msg:
                    logger.warning(f"Нет доступа к пользователю {user.user_id}")
                else:
                    logger.exception(
                        f"Ошибка открепления сообщений у пользователя {user.user_id}: {e}"
                    )

        report = (
            f"✅ Сообщения откреплены:\n"
            f"📌 Успешно откреплено: {success_count}\n"
            f"❌ Ошибок: {failed_count}"
        )
        await message.answer(report)

    except Exception as e:
        logger.exception(f"Ошибка при откреплении сообщений: {e}")
        await message.answer("❌ Произошла ошибка при откреплении сообщений.")
