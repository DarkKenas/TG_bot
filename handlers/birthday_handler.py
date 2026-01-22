from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime
import logging

from db_handler import PostgresHandler
from exceptions import RecordNotFound
from keyboards.birthday_keyboards import get_gift_collection_keyboard
from keyboards.main_menu_keyboards import get_main_menu_keyboard, BUTTON_BIRTHDAYS
from db_handler.models import User, Collector
from states.user_states import TransferStates

birthday_router = Router()
logger = logging.getLogger(__name__)

GIFT_COLLECTION_MESSAGE = (
    "💰 <b>Сбор средств на подарок</b>\n\n"
    "👤 Собирает: <b>{collector_name}</b>\n"
    "📱 Перевод по номеру телефона: <code>{phone}</code>\n"
    "🏦 Банк: <u>{bank_name}</u>\n\n"
    "📲 Переводите удобным для вас способом"
)

NO_ACTIVE_COLLECTOR_MESSAGE = (
    "⚠️ <b>Ответственный за сбор средств не назначен</b>\n"
    "🔧 Обратитесь к администратору или в техническую поддержку для решения этого вопроса."
)

TRANSFER_ALREADY_REGISTERED = (
    "Ваш перевод уже зарегистрирован\n\nСпасибо за участие! 🎁"
)

TRANSFER_SUCCESS_MESSAGE = (
    "😇 <b>Спасибо за участие!</b>\n" "✅ Ваш перевод зафиксирован"
)

NOTIFICATION_MESSAGE = (
    "💰 <b>Новый перевод на подарок!</b>\n\n"
    "👤 <b>От:</b> {sender_name}\n"
    "🎁 <b>Для:</b> {birthday_name}\n"
    "💵 <b>Сумма:</b> {amount} ₽\n"
    "⏰ <b>Время:</b> {datetime}"
)

ASK_AMOUNT_MESSAGE = (
    "💰 Введите сумму перевода в рублях:\n\n"
    "Например: 500 или 1000.50"
)

NOTIFICATION_SENT = "👌 Ответственный за сбор получил уведомление о вашем переводе"

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


@birthday_router.callback_query(F.data.startswith("birthday_gift:"))
async def handle_birthday_gift(
    callback: CallbackQuery, active_collector: Collector | None
) -> None:
    """Обработка кнопки 'Средства на подарок'."""
    if active_collector is None:
        await callback.message.edit_text(NO_ACTIVE_COLLECTOR_MESSAGE)
        return
    try:
        birthday_user_id = int(callback.data.split(":")[1])
        collector_user = active_collector.user

        message = GIFT_COLLECTION_MESSAGE.format(
            collector_name=collector_user.full_name,
            phone=active_collector.phone_number,
            bank_name=active_collector.bank_name or "не указан",
        )

        keyboard = get_gift_collection_keyboard(birthday_user_id)
        await callback.message.edit_text(message, reply_markup=keyboard)
    except Exception as e:
        logger.exception(f"Ошибка при обработке сбора средств: {e}")
        await callback.message.edit_text("❌ Произошла ошибка")


@birthday_router.callback_query(F.data.startswith("transferred:"))
async def handle_transferred(
    callback: CallbackQuery,
    user: User,
    state: FSMContext,
    db: PostgresHandler,
) -> None:
    """Обработка кнопки 'Перевел' - запрос суммы перевода."""
    try:
        birthday_user_id = int(callback.data.split(":")[1])
        birthday_user = await db.get_user(birthday_user_id)
        sender_id = callback.from_user.id

        # Проверяем, не был ли уже зарегистрирован перевод
        transfers = await db.transfers.get_for_birthday_user(birthday_user_id)
        existing_transfer = any(
            t.sender_id == sender_id for t in transfers
        )
        
        if existing_transfer:
            await callback.message.edit_text(TRANSFER_ALREADY_REGISTERED)
            return

        # Сохраняем данные в state и запрашиваем сумму
        await state.update_data(
            birthday_user_id=birthday_user_id,
            sender_id=sender_id,
        )
        await callback.message.edit_text(ASK_AMOUNT_MESSAGE)
        await state.set_state(TransferStates.waiting_for_transfer_amount)

    except RecordNotFound:
        await callback.message.edit_text("❌ Пользователь не найден")
    except Exception as e:
        logger.exception(f"Ошибка при обработке перевода: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при обработке перевода")


@birthday_router.message(TransferStates.waiting_for_transfer_amount)
async def process_transfer_amount(
    message: Message,
    user: User,
    state: FSMContext,
    active_collector: Collector | None,
    db: PostgresHandler,
) -> None:
    """Обработка введенной суммы перевода."""
    try:
        # Парсим сумму
        try:
            amount = float(message.text.replace(",", ".").strip())
            if amount <= 0:
                await message.answer("❌ Сумма должна быть больше нуля. Введите сумму еще раз:")
                return
        except ValueError:
            await message.answer("❌ Неверный формат суммы. Введите число, например: 500 или 1000.50")
            return

        data = await state.get_data()
        birthday_user_id = data.get("birthday_user_id")
        sender_id = data.get("sender_id", message.from_user.id)

        if not birthday_user_id:
            await message.answer("❌ Ошибка: данные сессии устарели. Начните заново.")
            await state.clear()
            return

        birthday_user = await db.get_user(birthday_user_id)

        # Создаем перевод
        transfer_added = await db.add_transfer(
            sender_id=sender_id,
            birthday_user_id=birthday_user_id,
            transfer_datetime=datetime.now(),
            amount=amount,
        )

        if not transfer_added:
            await message.answer(TRANSFER_ALREADY_REGISTERED)
            await state.clear()
            return

        sender_name = user.full_name
        birthday_name = birthday_user.full_name

        # Отправляем уведомление коллектору
        is_sent = await send_notification_to_collector(
            message.bot, sender_name, birthday_name, datetime.now(), amount, active_collector
        )

        if not is_sent:
            logger.warning(
                f"Не удалось отправить уведомление о переводе: {sender_id} -> {birthday_user_id}"
            )
            await message.answer(
                "❌ Ошибка при отправке уведомления ответственному за сбор"
            )
            await state.clear()
            return

        await message.answer(
            f"{TRANSFER_SUCCESS_MESSAGE}\n\n"
            f"💵 Сумма: <b>{amount:.2f} ₽</b>",
            reply_markup=await get_main_menu_keyboard(
                is_admin=user.is_admin,
                is_collector=user.is_collector,
            ),
        )
        logger.info(f"✅ Перевод зафиксирован: {sender_name} -> {birthday_name}, сумма: {amount} ₽")
        await state.clear()

    except RecordNotFound:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
    except Exception as e:
        logger.exception(f"Ошибка при обработке перевода: {e}")
        await message.answer("❌ Произошла ошибка при обработке перевода")
        await state.clear()


async def send_notification_to_collector(
    bot: Bot,
    sender_name: str,
    birthday_name: str,
    datetime_obj: datetime,
    amount: float,
    active_collector: Collector | None,
) -> bool:
    """Отправка уведомления коллектору о переводе."""
    try:
        if active_collector is None:
            logger.warning(
                f"Не найден активный коллектор при отправке уведомления о переводе от {sender_name}"
            )
            return False
        collector_user_id = active_collector.user_id

        notification_message = NOTIFICATION_MESSAGE.format(
            sender_name=sender_name,
            birthday_name=birthday_name,
            amount=f"{amount:.2f}",
            datetime=datetime_obj.strftime("%d.%m.%Y %H:%M:%S"),
        )

        await bot.send_message(collector_user_id, notification_message)

        logger.info(
            f"✅ Уведомление от {sender_name} отправлено коллектору "
            f"{active_collector.user.initials}, сумма: {amount} ₽"
        )
        return True
    except Exception as e:
        logger.exception(f"❌ Ошибка при отправке уведомления коллектору: {e}")
        return False


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

    response += "📅 <b>Предстоящие:</b>\n\n"
    if upcoming:
        for user in upcoming:
            if user.birth_date:
                date = f"{user.birth_date.day} {MONTH_NAMES[user.birth_date.month]}"
                response += f"{date} - {user.initials}\n"

    if past:
        response += "\n📆 <b>Прошедшие:</b>\n\n"
        for user in past:
            if user.birth_date:
                date = f"{user.birth_date.day} {MONTH_NAMES[user.birth_date.month]}"
                response += f"{date} - {user.initials}\n"

    await message.answer(response)
