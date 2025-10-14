from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from create_bot import pg_db
from aiogram.fsm.context import FSMContext
from handlers.wish_handler import start_add_wish, show_wish_edit_menu
from handlers.register import show_edit_menu
from keyboards.wishlist_keyboards import (
    get_edit_wish_keyboard,
    get_num_wish_keyboards,
    get_edit_wishlist_keyboard,
)
from keyboards.user_keyboards import get_edit_user_keyboard
from keyboards.main_menu_keyboards import (
    get_service_chat_keyboard,
    BUTTON_MY_WISHES,
    BUTTON_ADD_WISH,
    BUTTON_MY_DATA,
    BUTTON_SERVICE_CHAT,
    BUTTON_CANCEL,
)
from states.user_states import UserDataStates, WishStates
import logging
from db_handler.models import User

logger = logging.getLogger(__name__)
main_menu_router = Router()


# =============== Обработка кнопок главного меню ===============
@main_menu_router.message(F.text == BUTTON_MY_DATA)
async def show_user_data(message: Message, state: FSMContext, user: User):
    """Показать данные пользователя"""
    try:
        await state.update_data(
            data={
                "last_name": user.last_name,
                "first_name": user.first_name,
                "patronymic": user.patronymic,
                "birth_date": user.birth_date,
            }
        )
        user_text = (
            f"📋 <b>Ваши данные:</b>\n\n"
            f"Фамилия: <b>{user.last_name}</b>\n"
            f"Имя: <b>{user.first_name}</b>\n"
            f"Отчество: <b>{user.patronymic}</b>\n\n"
            f"📅 Дата рождения: {user.birth_date.strftime('%d.%m.%Y')}"
        )

        await message.answer(user_text, reply_markup=get_edit_user_keyboard())

    except Exception as e:
        logger.error(f"Ошибка при получении данных пользователя: {e}")
        await message.answer("❌ Ошибка загрузки данных")
        await state.clear()


@main_menu_router.message(F.text == BUTTON_MY_WISHES)
async def show_wishlist(message: Message, state: FSMContext):
    """Показать wishlist пользователя"""
    try:
        wish_list = await pg_db.get_wish_list(message.from_user.id)
        if not wish_list:
            await message.answer("🎯 Ваш WishList пуст.")
            return

        user_text = f"🎯 <b>Ваш WishList:</b>\n\n"

        # Передаем список wish_id в state
        wish_list_id = [wish.id for wish in wish_list]
        await state.update_data(wish_list_id=wish_list_id)

        for i, wish in enumerate(wish_list, 1):
            if wish.wish_url:
                user_text += f"{i}. <a href='{wish.wish_url}'>{wish.wish_text}</a>\n"
            else:
                user_text += f"{i}. {wish.wish_text}\n"

        await message.answer(
            user_text,
            reply_markup=get_edit_wishlist_keyboard(),
            disable_web_page_preview=True,
        )

    except Exception as e:
        await message.answer("Ошибка загрузки данных 😵")
        state.clear()


@main_menu_router.message(F.text == BUTTON_ADD_WISH)
async def add_wish_from_menu(message: Message, state: FSMContext):
    """Добавить желание через кнопку меню"""
    await start_add_wish(message, state)


@main_menu_router.message(F.text == BUTTON_SERVICE_CHAT)
async def show_support(message: Message):
    """Показать контакты тех. поддержки"""
    await message.answer(
        "Если у вас возникли вопросы ⚠️❔, \nпожалуйста свяжитесь с Александром 🦸‍♂️:",
        reply_markup=await get_service_chat_keyboard(),
    )


@main_menu_router.message(F.text == BUTTON_CANCEL)
async def cancel(message: Message, state: FSMContext):
    """Отменить ввод чего либо"""
    await state.clear()
    await message.answer("✅ Ввод отменен")


# =============== Обработка кнопок редактирования ===============
# Редактирование данных пользователя
@main_menu_router.callback_query(F.data == "edit_user_data")
async def process_edit_user_data(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки редактирования данных пользователя"""
    await state.set_state(UserDataStates.confirmation)
    await show_edit_menu(callback, state)


# Редактирование списка желаний
@main_menu_router.callback_query(F.data == "edit_wishlist")
async def process_edit_wishlist(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки редактирования желания"""
    data = await state.get_data()
    wish_id_list = data.get("wish_list_id")

    if not wish_id_list:
        logger.error(
            f"Ошибка: wish_list_id не найден. Пользователь {callback.from_user.id}"
        )
        await callback.message.answer("Неизвестная Ошибка 😵")
        return

    await callback.message.edit_reply_markup(
        reply_markup=get_num_wish_keyboards(wish_id_list)
    )
    await callback.answer("Выберите какой wish редактировать")


# Подготовка к редактированию выбранного wish
@main_menu_router.callback_query(F.data.startswith("select_wish:"))
async def process_select_wish(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки выбора wish для редактирования"""
    wish_id = callback.data.split(":")[1]
    await state.update_data(wish_id=wish_id)
    await callback.message.edit_reply_markup(reply_markup=get_edit_wish_keyboard())


@main_menu_router.callback_query(F.data == "edit_wish")
async def process_edit_wish(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    wish_id = data.get("wish_id")
    try:
        wish = await pg_db.get_wish(wish_id)
    except:
        logger.error(
            f"Ошибка получения: Wish с id {wish_id} для пользователя {callback.from_user.id}"
        )
        await callback.message.answer("Неизвестная Ошибка 😵")
        await state.clear()
        return
    await state.update_data(wish_text=wish.wish_text, wish_url=wish.wish_url)
    await state.set_state(WishStates.confirmation)
    await show_wish_edit_menu(callback, state)


# Удаление желания
@main_menu_router.callback_query(F.data == "delete_wish")
async def process_delete_wish(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки удаления wish"""
    data = await state.get_data()
    wish_id = data.get("wish_id")
    try:
        await pg_db.delete_wish(wish_id, callback.from_user.id)
    except:
        logger.error(
            f"Ошибка удаления: Wish с id {wish_id} для пользователя {callback.from_user.id}"
        )
        await callback.message.answer("Неизвестная Ошибка 😵")
        await state.clear()
        return
    await callback.message.edit_text("✅ Желание удалено")
    await state.clear()
