from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states.user_states import WishStates
from create_bot import pg_db
from exceptions.my_exceptions import RecordNotFound
from keyboards.wishlist_keyboards import (
    get_url_keyboard,
    get_edit_wishdata_keyboard,
)
from handlers.services.service_wish import (
    handle_wish_text,
    handle_wish_url,
    handle_wish_confirmation,
)
import logging

wishlist_router = Router()
logger = logging.getLogger(__name__)


# ============ Добавление желания ============
async def start_add_wish(message: Message, state: FSMContext):
    """Начало добавления желания"""
    await message.answer("🎯 Добавляем новый подарок для вас.\n\nОпишите ваше желание:")
    await state.update_data(is_add_wish=True)
    await state.set_state(WishStates.waiting_for_wish_text)


# Обработка текста желания
@wishlist_router.message(WishStates.waiting_for_wish_text)
async def process_wish_text(message: Message, state: FSMContext):
    """Обработка текста желания"""
    if not await handle_wish_text(message, state):
        return

    data = await state.get_data()
    if data.get("is_edit"):
        await handle_wish_confirmation(message, state)
    else:
        await message.answer(
            "Введите ссылку на подарок ✏️:\n\n"
            "P.s. Если таковой нет, то нажмите 'Нет URL 🔗'",
            reply_markup=get_url_keyboard(),
        )
        await state.set_state(WishStates.waiting_for_wish_url)


# Обработка кнопки 'Нет URL 🔗'
@wishlist_router.callback_query(F.data == "url_no", WishStates.waiting_for_wish_url)
async def process_url_no(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Нет URL 🔗'"""
    await state.update_data(wish_url=None)
    await handle_wish_confirmation(callback, state)


# Обработка URL
@wishlist_router.message(WishStates.waiting_for_wish_url)
async def process_url(message: Message, state: FSMContext):
    """Обработка URL"""
    if not await handle_wish_url(message, state):
        return

    await handle_wish_confirmation(message, state)


# ============ Подтверждение желания ============
@wishlist_router.callback_query(F.data == "confirm_yes", WishStates.confirmation)
async def confirm_wish(callback: CallbackQuery, state: FSMContext):
    """Подтверждение желания"""
    data = await state.get_data()
    wish_dict = {
        "user_id": callback.from_user.id,
        "wish_text": data["wish_text"],
        "wish_url": data.get("wish_url"),
    }

    try:
        if data.get("is_add_wish"):
            await pg_db.add_wish(**wish_dict)
        else:
            wish_dict["wish_id"] = data["wish_id"]
            await pg_db.update_wish(**wish_dict)
    except RecordNotFound as e:
        logger.error(e)
        await callback.message.edit_text("<b>Запись не найдена в базе данных 😥</b>")
        await state.clear()
        return
    except Exception as e:
        logger.error(
            f"Неожиданная ошибка при обработке желания пользователя {callback.from_user.id}: {e}"
        )
        await callback.message.edit_text(
            "<b>Произошла неожиданная ошибка сервера 😵</b>"
        )
        await state.clear()
        return

    success_text = f"✅ <b>Желание сохранено!</b>\n\n"
    if data.get("wish_url"):
        success_text += f"<a href='{data['wish_url']}'>{data['wish_text']}</a>"
    else:
        success_text += f"{data['wish_text']}"

    await callback.message.edit_text(success_text, disable_web_page_preview=True)
    await state.clear()


# ============ Редактирование желания ============
@wishlist_router.callback_query(F.data == "confirm_no", WishStates.confirmation)
async def show_wish_edit_menu(callback: CallbackQuery, state: FSMContext):
    """Показать меню редактирования желания"""
    await callback.message.edit_reply_markup(reply_markup=get_edit_wishdata_keyboard())
    await callback.answer("Выберите что исправить:")
    await state.update_data(is_edit=True)


# Редактирование текста желания
@wishlist_router.callback_query(F.data == "edit_wish_text", WishStates.confirmation)
async def edit_wish_text(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await callback.message.answer("Введите новый текст желания ✏️:")
    await callback.answer()
    await state.set_state(WishStates.waiting_for_wish_text)


# Редактирование URL желания
@wishlist_router.callback_query(F.data == "edit_wish_url", WishStates.confirmation)
async def edit_wish_url(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "Введите новый URL подарка 🔗:", reply_markup=get_url_keyboard()
    )
    await state.set_state(WishStates.waiting_for_wish_url)
