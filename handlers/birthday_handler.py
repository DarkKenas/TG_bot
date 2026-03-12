from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime
import logging

from db_handler import PostgresHandler
from exceptions import RecordNotFound, StateDataError
from keyboards.birthday_keyboards import (
    get_birthdays_keyboard,
    BIRTHDAYS_WISHLISTS,
    get_birthday_actions_keyboard,
)
from keyboards.wishlist_keyboards import get_url_keyboard
from keyboards.main_menu_keyboards import BUTTON_BIRTHDAYS
from db_handler.models import User
from states.user_states import BirthdayStates, GiftSuggestionStates
from handlers.services.service_user_list import (
    get_user_dict_from_state,
    get_user_id_by_num,
)

birthday_router = Router()
logger = logging.getLogger(__name__)

MONTH_NAMES = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


@birthday_router.callback_query(F.data.startswith("suggest_gift:"))
async def start_suggest_gift(
    callback: CallbackQuery,
    state: FSMContext,
    db: PostgresHandler,
) -> None:
    """Старт предложения подарка: спрашиваем текст предложения."""
    try:
        birthday_user_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Некорректные данные", show_alert=True)
        return

    # Получаем информацию о пользователе, у которого ДР
    try:
        birthday_user = await db.get_user(birthday_user_id)
        if not birthday_user.birth_date:
            await callback.answer("У пользователя не указана дата рождения", show_alert=True)
            return
        
        # Формируем дату в формате DD.MM
        date_str = birthday_user.birth_date.strftime("%d.%m")
        # Получаем полное имя
        full_name = birthday_user.full_name
        
        # Формируем текст сообщения
        message_text = (
            f"📅 {date_str} день рождения отмечает {full_name}\n\n"
            "Опишите в одном собщении ваши предложения по подарку:"
        )
        
        await state.update_data(birthday_user_id=birthday_user_id)
        # Отправляем новое сообщение, не редактируя старое (кнопка остается)
        await callback.message.answer(message_text)
        await state.set_state(GiftSuggestionStates.waiting_for_gift_text)
        await callback.answer()
    except Exception as e:
        logger.exception(f"Ошибка при получении данных пользователя для предложения подарка: {e}")
        await callback.answer("Ошибка при загрузке данных", show_alert=True)


@birthday_router.message(GiftSuggestionStates.waiting_for_gift_text)
async def process_gift_text(message: Message, state: FSMContext):
    """Обработка текста предложения подарка."""
    text = message.text.strip()
    if len(text) < 3:
        await message.answer(
            "❌ Текст должен быть не короче 3 символов. Попробуйте ещё раз."
        )
        return

    await state.update_data(gift_text=text)
    await message.answer(
        "Теперь добавьте ссылку на этот подарок 🔗\n\n"
        "Если ссылки нет, нажмите «Нет ссылки 🔗».",
        reply_markup=get_url_keyboard(),
    )
    await state.set_state(GiftSuggestionStates.waiting_for_gift_url)


@birthday_router.callback_query(
    F.data == "url_no", GiftSuggestionStates.waiting_for_gift_url
)
async def process_gift_url_no(
    callback: CallbackQuery,
    state: FSMContext,
    db: PostgresHandler,
) -> None:
    """Обработка варианта без ссылки для предложения подарка."""
    data = await state.get_data()
    birthday_user_id = data.get("birthday_user_id")
    gift_text = data.get("gift_text")

    if not birthday_user_id or not gift_text:
        await callback.message.edit_text("❌ Данные сессии устарели. Начните заново.")
        await state.clear()
        await callback.answer()
        return

    try:
        await db.add_transfer(
            sender_id=callback.from_user.id,
            birthday_user_id=birthday_user_id,
            transfer_datetime=datetime.now(),
            amount=0,  # поле не используется, но оставлено в БД
            gift_text=gift_text,
            gift_url=None,
        )
        await callback.message.edit_text("✅ Ваше предложение подарка сохранено.")
        await state.clear()
    except Exception as e:
        logger.exception(f"Ошибка при сохранении предложения подарка: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при сохранении предложения."
        )
        await state.clear()
    finally:
        await callback.answer()


@birthday_router.message(GiftSuggestionStates.waiting_for_gift_url)
async def process_gift_url(
    message: Message,
    state: FSMContext,
    db: PostgresHandler,
) -> None:
    """Обработка ссылки для предложения подарка."""
    url = message.text.strip()

    data = await state.get_data()
    birthday_user_id = data.get("birthday_user_id")
    gift_text = data.get("gift_text")

    if not birthday_user_id or not gift_text:
        await message.answer("❌ Данные сессии устарели. Начните заново.")
        await state.clear()
        return

    # Валидацию ссылки делаем через already used фильтр/функцию, если нужно,
    # но чтобы не дублировать логику, можно использовать is_valid_url из filters.valid
    from filters.valid import is_valid_url

    is_valid, answer = is_valid_url(url)
    if not is_valid:
        await message.answer(answer)
        return

    try:
        await db.add_transfer(
            sender_id=message.from_user.id,
            birthday_user_id=birthday_user_id,
            transfer_datetime=datetime.now(),
            amount=0,
            gift_text=gift_text,
            gift_url=url,
        )
        await message.answer("✅ Ваше предложение подарка сохранено.")
        await state.clear()
    except Exception as e:
        logger.exception(f"Ошибка при сохранении предложения подарка: {e}")
        await message.answer("❌ Произошла ошибка при сохранении предложения.")
        await state.clear()


@birthday_router.message(F.text == BUTTON_BIRTHDAYS)
async def show_upcoming_birthdays(message: Message, db: PostgresHandler):
    """Показать предстоящие дни рождения."""
    current_date = datetime.now()
    current = (current_date.month, current_date.day)

    users = await db.get_all_users()

    if not users:
        await message.answer("Список дней рождений пуст.")
        return

    upcoming: list[User] = []
    past: list[User] = []

    for user in users:
        if not user.birth_date:
            continue  # Пропускаем пользователей без даты рождения
        if (user.birth_date.month, user.birth_date.day) >= current:
            upcoming.append(user)
        else:
            past.append(user)

    def sort_key(user: User) -> tuple[int, int]:
        if not user.birth_date:
            return (13, 32)  # Помещаем пользователей без даты в конец
        return (user.birth_date.month, user.birth_date.day)

    upcoming.sort(key=sort_key)
    past.sort(key=sort_key)

    response = "🎂 <b>Дни рождения</b>\n\n"

    response += "📅 <b>Предстоящие:</b>\n"
    if upcoming:
        last_month = None
        for user in upcoming:
            if not user.birth_date:
                continue
            month = user.birth_date.month
            # Пустая строка при смене месяца (кроме самого первого)
            if last_month is not None and month != last_month:
                response += "\n"
            last_month = month

            date = f"{user.birth_date.day} {MONTH_NAMES[month]}"
            response += f"{date} - {user.initials}\n"

    if past:
        response += "\n📆 <b>Прошедшие:</b>\n"
        for user in past:
            if not user.birth_date:
                continue
            month = user.birth_date.month
            date = f"{user.birth_date.day} {MONTH_NAMES[month]}"
            response += f"{date} - {user.initials}\n"

    await message.answer(response, reply_markup=get_birthdays_keyboard())


@birthday_router.callback_query(F.data == BIRTHDAYS_WISHLISTS)
async def show_users_list_for_wishlist_from_birthdays(
    callback: CallbackQuery,
    state: FSMContext,
    db: PostgresHandler,
):
    """Показать список пользователей для выбора вишлиста (через 'Дни рождения')."""
    try:
        users = await db.get_all_users()
        if not users:
            await callback.message.edit_text("📋 <b>Список пользователей пуст</b>")
            await callback.answer()
            return

        users.sort(key=lambda user: user.last_name or "")
        users_text = "👥❤️ <b>Список пользователей:</b>\n\n"

        user_dict: dict[int, int] = {}
        for num, user_item in enumerate(users, 1):
            users_text += f"  {num}. {user_item.full_name}\n"
            user_dict[num] = user_item.user_id

        await state.update_data(user_dict=user_dict)

        await callback.message.edit_text(
            users_text
            + "\nВведите номер пользователя, вишлист которого хотите посмотреть:"
        )
        await state.set_state(BirthdayStates.waiting_for_wishlist_user_num)
        await callback.answer()

    except Exception as e:
        logger.exception(f"Ошибка при создании списка пользователей: {e}")
        await callback.message.edit_text("❌ Ошибка при загрузке списка пользователей")
        await state.clear()


@birthday_router.message(BirthdayStates.waiting_for_wishlist_user_num)
async def show_user_wishlist_from_birthdays(
    message: Message,
    state: FSMContext,
    db: PostgresHandler,
):
    """Показать вишлист выбранного пользователя (через 'Дни рождения')."""
    try:
        user_dict = await get_user_dict_from_state(state)
    except StateDataError as e:
        logger.exception(e)
        await message.answer("❌ Сессия устарела. Начните заново.")
        await state.clear()
        return

    try:
        user_id = get_user_id_by_num(user_dict, message.text.strip())
        wish_list = await db.get_wish_list(user_id)
        user = await db.get_user(user_id)

        if not wish_list:
            await message.answer(
                f"❤️ Вишлист пользователя <b>{user.full_name}</b> пуст.\n\n"
                "Введите другой номер или нажмите кнопку «⭕ Остановить ввод»."
            )
            return

        wishlist_text = f"❤️ <b>Вишлист {user.full_name}:</b>\n\n"

        for i, wish in enumerate(wish_list, 1):
            if wish.wish_url:
                wishlist_text += (
                    f"{i}. <a href='{wish.wish_url}'>{wish.wish_text}</a>\n"
                )
            else:
                wishlist_text += f"{i}. {wish.wish_text}\n"

        await message.answer(
            wishlist_text
            + "\nВведите другой номер или нажмите кнопку «⭕ Остановить ввод».",
            disable_web_page_preview=True,
        )

    except ValueError:
        await message.answer(
            "❌ Неверный номер. Введите номер пользователя из списка "
            "или нажмите кнопку «⭕ Остановить ввод»."
        )
        return
    except Exception as e:
        logger.exception(f"Ошибка при получении вишлиста: {e}")
        await message.answer("❌ Произошла ошибка при загрузке вишлиста")
        await state.clear()
