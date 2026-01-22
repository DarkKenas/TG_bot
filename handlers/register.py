import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import get_settings
from states.user_states import UserDataStates
from db_handler import PostgresHandler
from keyboards.register_keyboards import (
    get_userdata_edit_keyboard,
    get_registration_keyboard,
)
from keyboards.main_menu_keyboards import get_main_menu_keyboard
from exceptions import RecordAlreadyExists, RecordNotFound
from handlers.services.service_register import (
    handle_last_name,
    handle_first_name,
    handle_patronymic,
    handle_birth_date,
    handle_confirmation,
)

register_router = Router()
logger = logging.getLogger(__name__)
settings = get_settings()


# ========== Обработчики регистрации ==========

@register_router.callback_query(F.data == "register")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    """Начало регистрации"""
    await callback.message.edit_text(
        text="📝 Начинаем регистрацию.\n\nВведите вашу фамилию 👤:",
    )
    await state.update_data(is_register=True)
    await state.set_state(UserDataStates.waiting_for_last_name)


@register_router.message(UserDataStates.waiting_for_last_name)
async def process_last_name(message: Message, state: FSMContext):
    """Обработка фамилии"""
    if not await handle_last_name(message, state):
        return

    data = await state.get_data()
    if data.get("is_edit"):
        await handle_confirmation(message, state)
    else:
        await message.answer("Теперь введите ваше имя 👤:")
        await state.set_state(UserDataStates.waiting_for_first_name)


@register_router.message(UserDataStates.waiting_for_first_name)
async def process_first_name(message: Message, state: FSMContext):
    """Обработка имени"""
    if not await handle_first_name(message, state):
        return

    data = await state.get_data()
    if data.get("is_edit"):
        await handle_confirmation(message, state)
    else:
        await message.answer("Введите ваше отчество 👤:")
        await state.set_state(UserDataStates.waiting_for_patronymic)


@register_router.message(UserDataStates.waiting_for_patronymic)
async def process_patronymic(message: Message, state: FSMContext):
    """Обработка отчества"""
    if not await handle_patronymic(message, state):
        return

    data = await state.get_data()
    if data.get("is_edit"):
        await handle_confirmation(message, state)
    else:
        await message.answer("Введите вашу дату рождения в формате ДД.ММ.ГГГГ 📅:")
        await state.set_state(UserDataStates.waiting_for_birth_date)


@register_router.message(UserDataStates.waiting_for_birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    """Обработка даты рождения"""
    if not await handle_birth_date(message, state):
        return

    await handle_confirmation(message, state)


# ========== Обработчики подтверждения данных ==========

@register_router.callback_query(F.data == "confirm_yes", UserDataStates.confirmation)
async def confirm_data(callback: CallbackQuery, state: FSMContext, db: PostgresHandler):
    """Подтверждение данных"""
    data = await state.get_data()
    user_data_dict = {
        "user_id": callback.from_user.id,
        "username": callback.from_user.username,
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "patronymic": data["patronymic"],
        "birth_date": data["birth_date"],
    }

    try:
        if data.get("is_register"):
            operation_type = "сохранении"
            await db.add_user(**user_data_dict)
        else:
            operation_type = "обновлении"
            await db.update_user(**user_data_dict)

    except RecordAlreadyExists as e:
        logger.warning(e)
        await callback.message.edit_text("<b>Вы уже зарегистрированы ☺️</b>")
        await state.clear()
        return

    except RecordNotFound as e:
        logger.warning(e)
        await callback.message.edit_text(
            "<b>Ваш пользователь не найден 😥</b>\n\n"
            "📝 Пожалуйста, выполните регистрацию",
            reply_markup=get_registration_keyboard(),
        )
        await state.clear()
        return

    except Exception as e:
        logger.exception(
            f"Ошибка при {operation_type} пользователя {callback.from_user.id}: {e}"
        )
        await callback.message.edit_text(
            f"<b>Неожиданная ошибка при {operation_type} данных 😵</b>"
        )
        await state.clear()
        return

    success_text = (
        f"✅ <b>Данные сохранены!</b>\n\n"
        f"👤 {data['last_name']} {data['first_name']} {data['patronymic']}\n"
        f"📅 {data['birth_date'].strftime('%d.%m.%Y')}"
    )

    # Автоматически назначаем права service_user при регистрации,
    # если user_id совпадает с default_service_user_id
    if data.get("is_register") and callback.from_user.id == settings.default_service_user_id:
        try:
            await db.set_service_user(user_id=callback.from_user.id)
            success_text += "\n\n🔐 <b>Вам автоматически назначены права сервисного пользователя!</b>"
            logger.info(
                f"✅ Автоматически назначен service_user при регистрации: {callback.from_user.id}"
            )
        except Exception as e:
            logger.warning(
                f"Не удалось автоматически назначить service_user для {callback.from_user.id}: {e}"
            )

    await state.clear()
    await callback.message.edit_text(success_text)

    if data.get("is_register"):
        # Загружаем пользователя заново, чтобы получить актуальные данные о ролях
        try:
            user = await db.get_user(callback.from_user.id)
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text="Можете пополнять свой WishList 🤗",
                reply_markup=await get_main_menu_keyboard(
                    is_admin=user.is_admin,
                    is_collector=user.is_collector,
                ),
            )
        except Exception as e:
            logger.exception(f"Ошибка при отправке меню после регистрации: {e}")
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text="Можете пополнять свой WishList 🤗",
                reply_markup=await get_main_menu_keyboard(),
            )


# ========== Редактирование данных ==========

@register_router.callback_query(F.data == "confirm_no", UserDataStates.confirmation)
async def show_edit_menu(callback: CallbackQuery, state: FSMContext):
    """Показать меню редактирования"""
    await callback.answer()  # Убираем индикатор загрузки
    await callback.message.edit_reply_markup(reply_markup=get_userdata_edit_keyboard())
    await state.update_data(is_edit=True)


@register_router.callback_query(F.data == "edit_last_name", UserDataStates.confirmation)
async def edit_last_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Убираем индикатор загрузки
    await callback.message.edit_reply_markup()
    await callback.message.answer("Введите фамилию 👤:")
    await state.set_state(UserDataStates.waiting_for_last_name)


@register_router.callback_query(F.data == "edit_first_name", UserDataStates.confirmation)
async def edit_first_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Убираем индикатор загрузки
    await callback.message.edit_reply_markup()
    await callback.message.answer("Введите имя 👤:")
    await state.set_state(UserDataStates.waiting_for_first_name)


@register_router.callback_query(F.data == "edit_patronymic", UserDataStates.confirmation)
async def edit_patronymic(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Убираем индикатор загрузки
    await callback.message.edit_reply_markup()
    await callback.message.answer("Введите отчество 👤:")
    await state.set_state(UserDataStates.waiting_for_patronymic)


@register_router.callback_query(F.data == "edit_birth_date", UserDataStates.confirmation)
async def edit_birth_date(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Убираем индикатор загрузки
    await callback.message.edit_reply_markup()
    await callback.message.answer("Введите дату рождения в формате ДД.ММ.ГГГГ 📅:")
    await state.set_state(UserDataStates.waiting_for_birth_date)
