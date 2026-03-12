from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from db_handler import PostgresHandler
from handlers.register import show_edit_menu
from keyboards.wishlist_keyboards import (
    get_edit_wish_keyboard,
    get_my_wishlist_keyboard,
    get_num_wish_keyboards,
    get_url_keyboard,
)
from handlers.wish_handler import start_add_wish
from keyboards.user_keyboards import get_edit_user_keyboard
from keyboards.register_keyboards import get_userdata_edit_keyboard
from keyboards.main_menu_keyboards import (
    get_service_chat_keyboard,
    BUTTON_MY_WISHES,
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
        birth_date_text = (
            user.birth_date.strftime("%d.%m.%Y") if user.birth_date else "не указана"
        )
        user_text = (
            f"📋 <b>Ваши данные:</b>\n\n"
            f"Фамилия: {user.last_name}\n"
            f"Имя: {user.first_name}\n"
            f"Отчество: {user.patronymic}\n\n"
            f"📅 Дата рождения: {birth_date_text}\n\n"
        )

        await message.answer(user_text, reply_markup=get_edit_user_keyboard())

    except Exception as e:
        logger.error(f"Ошибка при получении данных пользователя: {e}")
        await message.answer("❌ Ошибка загрузки данных")
        await state.clear()


@main_menu_router.message(F.text == BUTTON_MY_WISHES)
async def show_wishlist(message: Message, state: FSMContext, db: PostgresHandler):
    """Показать wishlist пользователя"""
    try:
        wish_list = await db.get_wish_list(message.from_user.id)

        user_text = "❤️ <b>Ваш вишлист:</b>\n\n"

        if not wish_list:
            user_text += "Ваш список желаний пуст."
        else:
            wish_list_id = [wish.id for wish in wish_list]
            await state.update_data(wish_list_id=wish_list_id)

            for i, wish in enumerate(wish_list, 1):
                if wish.wish_url:
                    user_text += (
                        f"{i}. <a href='{wish.wish_url}'>{wish.wish_text}</a>\n"
                    )
                else:
                    user_text += f"{i}. {wish.wish_text}\n"

        keyboard = get_my_wishlist_keyboard(has_wishes=bool(wish_list))

        await message.answer(
            user_text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

    except Exception as e:
        await message.answer("Ошибка загрузки данных 😵")
        await state.clear()


@main_menu_router.callback_query(F.data == "add_wish_from_list")
async def add_wish_from_list(callback: CallbackQuery, state: FSMContext):
    """Добавить желание через кнопку из списка вишлиста"""
    await callback.answer()
    await start_add_wish(callback.message, state)


@main_menu_router.message(F.text == BUTTON_SERVICE_CHAT)
async def show_support(message: Message, db: PostgresHandler):
    """Показать контакты тех. поддержки"""
    try:
        service_user = await db.get_service_user()
        await message.answer(
            "Если у вас возникли вопросы ⚠️❔, \nпожалуйста свяжитесь с сервисным специалистом 🦸‍♂️:",
            reply_markup=await get_service_chat_keyboard(service_user.user_id),
        )
    except Exception as e:
        await message.answer("Ошибка получения сервисного чата 😵")


@main_menu_router.message(F.text == BUTTON_CANCEL)
async def cancel(message: Message, state: FSMContext):
    """Отменить ввод чего либо"""
    await state.clear()
    await message.answer("✅ Ввод отменен")


# =============== Обработка кнопок редактирования ===============


@main_menu_router.callback_query(F.data == "edit_user_data")
async def process_edit_user_data(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки редактирования данных пользователя"""
    await callback.answer()  # Убираем индикатор загрузки
    
    # Получаем текущий текст сообщения и добавляем строку "Редактировать:"
    current_text = callback.message.text or callback.message.caption or ""
    updated_text = f"{current_text}\n\n<b>Редактировать:</b>"
    
    # Редактируем сообщение с новым текстом и клавиатурой
    await callback.message.edit_text(
        updated_text,
        reply_markup=get_userdata_edit_keyboard()
    )
    
    await state.set_state(UserDataStates.confirmation)
    await state.update_data(is_edit=True)


@main_menu_router.callback_query(F.data == "edit_wishlist")
async def process_edit_wishlist(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки редактирования желания"""
    await callback.answer()  # Убираем индикатор загрузки
    data = await state.get_data()
    wish_id_list = data.get("wish_list_id")

    if not wish_id_list:
        logger.error(
            f"Ошибка: wish_list_id не найден. Пользователь {callback.from_user.id}"
        )
        await callback.message.answer("Неизвестная Ошибка 😵")
        return

    # Получаем текущий текст сообщения и добавляем подпись
    current_text = callback.message.text or callback.message.caption or ""
    updated_text = (
        f"{current_text}\n\n✏️ Выберите, какое из желаний хотите отредактировать:"
    )

    await callback.message.edit_text(
        updated_text,
        reply_markup=get_num_wish_keyboards(wish_id_list),
        disable_web_page_preview=True,
    )


@main_menu_router.callback_query(F.data.startswith("select_wish:"))
async def process_select_wish(
    callback: CallbackQuery, state: FSMContext, db: PostgresHandler
):
    """Обработка кнопки выбора wish для редактирования"""
    await callback.answer()  # Убираем индикатор загрузки
    wish_id = callback.data.split(":")[1]
    await state.update_data(wish_id=wish_id)

    # Сразу показываем выбор действия: Изменить текст/ссылку/Удалить
    await callback.message.edit_reply_markup(reply_markup=get_edit_wish_keyboard())


@main_menu_router.callback_query(F.data == "edit_wish_text_direct")
async def process_edit_wish_text_direct(
    callback: CallbackQuery, state: FSMContext, db: PostgresHandler
):
    """Обработка кнопки 'Изменить текст' - прямой переход к редактированию"""
    await callback.answer()
    data = await state.get_data()
    wish_id = data.get("wish_id")
    try:
        wish = await db.get_wish(wish_id)
    except Exception:
        logger.error(
            f"Ошибка получения: Wish с id {wish_id} для пользователя {callback.from_user.id}"
        )
        await callback.message.answer("Неизвестная Ошибка 😵")
        await state.clear()
        return
    await state.update_data(
        wish_text=wish.wish_text, wish_url=wish.wish_url, is_edit=True
    )
    await callback.message.edit_reply_markup()
    await callback.message.answer("Введите новый текст желания ✏️:")
    await state.set_state(WishStates.waiting_for_wish_text)


@main_menu_router.callback_query(F.data == "edit_wish_url_direct")
async def process_edit_wish_url_direct(
    callback: CallbackQuery, state: FSMContext, db: PostgresHandler
):
    """Обработка кнопки 'Изменить ссылку' - прямой переход к редактированию"""
    await callback.answer()
    data = await state.get_data()
    wish_id = data.get("wish_id")
    try:
        wish = await db.get_wish(wish_id)
    except Exception:
        logger.error(
            f"Ошибка получения: Wish с id {wish_id} для пользователя {callback.from_user.id}"
        )
        await callback.message.answer("Неизвестная Ошибка 😵")
        await state.clear()
        return
    await state.update_data(
        wish_text=wish.wish_text, wish_url=wish.wish_url, is_edit=True
    )
    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "Введите новую ссылку на подарок 🔗:", reply_markup=get_url_keyboard()
    )
    await state.set_state(WishStates.waiting_for_wish_url)


@main_menu_router.callback_query(F.data == "delete_wish")
async def process_delete_wish(
    callback: CallbackQuery, state: FSMContext, db: PostgresHandler
):
    """Обработка кнопки удаления wish"""
    data = await state.get_data()
    wish_id = data.get("wish_id")
    try:
        await db.delete_wish(wish_id, callback.from_user.id)
    except Exception:
        logger.error(
            f"Ошибка удаления: Wish с id {wish_id} для пользователя {callback.from_user.id}"
        )
        await callback.message.answer("Неизвестная Ошибка 😵")
        await state.clear()
        return
    await callback.message.edit_text("✅ Желание удалено")
    await state.clear()
