from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import logging

from config import get_settings
from db_handler import PostgresHandler
from keyboards.main_menu_keyboards import get_main_menu_keyboard
from states.user_states import RoleStates
from db_handler.models import User
from exceptions import RecordAlreadyExists

role_router = Router()
logger = logging.getLogger(__name__)
settings = get_settings()

MSG_ERROR_GET_CODE_PHRASE = "❌ Кодовая фраза недоступна"
MSG_ERROR_RIGHTS = "❌ Ошибка выдачи прав"


# === Обработка установки прав Администратора ===

@role_router.message(Command("get_admin"))
async def get_admin(message: Message, state: FSMContext):
    """Получение пользователем прав администратора"""
    await message.answer(
        "👨‍💻 Для получения прав администратора\nВведите кодовую фразу ✏️:"
    )
    await state.set_state(RoleStates.waiting_for_admin_phrase)


@role_router.message(RoleStates.waiting_for_admin_phrase)
async def confirm_admin_code_phrase(
    message: Message, state: FSMContext, user: User, db: PostgresHandler
):
    """Проверка введенной кодовой фразы"""
    if message.text == settings.admin_secret_code:
        try:
            await db.add_administrator(user_id=message.from_user.id)
            await message.answer(
                "✅ <b>Права получены!</b>\n\n🔐 Доступна Админ панель в основном меню",
                reply_markup=await get_main_menu_keyboard(
                    is_admin=True,
                    is_collector=user.is_collector,
                ),
            )
            await state.clear()
            logger.info(f"✅ Добавлен новый админ: user_id={message.from_user.id}")
        except RecordAlreadyExists:
            await message.answer("<b>Ваш пользователь уже имеет права администратора ☺️</b>")
            await state.clear()
        except Exception as e:
            await message.answer(MSG_ERROR_RIGHTS)
            logger.exception(f"Ошибка при добавлении администратора:\n{e}")
            await state.clear()
    else:
        await message.answer("❌ Неверная кодовая фраза\nПовторите ввод ✏️:")


# === Обработка установки прав ServiceUser ===

@role_router.message(Command("get_service_user"))
async def get_service(message: Message, state: FSMContext):
    """Получение пользователем прав service_user"""
    await message.answer(
        "👨‍💻 Для получения прав сервисного пользователя\nВведите кодовую фразу ✏️:"
    )
    await state.set_state(RoleStates.waiting_for_service_phrase)


@role_router.message(RoleStates.waiting_for_service_phrase)
async def confirm_service_code_phrase(message: Message, state: FSMContext, db: PostgresHandler):
    """Проверка введенной кодовой фразы"""
    if message.text == settings.service_secret_code:
        try:
            await db.set_service_user(user_id=message.from_user.id)
            await message.answer(
                "✅ <b>Права получены!</b>\n\n"
                "Для управления списком админов используйте\n<b>/admin_list</b>",
            )
            await state.clear()
            logger.info(f"✅ Установлен service_user: user_id={message.from_user.id}")
        except RecordAlreadyExists:
            await message.answer("<b>Ваш пользователь уже имеет права сервисного пользователя ☺️</b>")
            await state.clear()
        except Exception as e:
            await message.answer(MSG_ERROR_RIGHTS)
            logger.exception(f"Ошибка при установки service_user:\n{e}")
            await state.clear()
    else:
        await message.answer("❌ Неверная кодовая фраза\nПовторите ввод ✏️:")
