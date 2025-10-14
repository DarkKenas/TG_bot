from create_bot import pg_db
from datetime import datetime, timedelta
from aiogram import Bot
from keyboards.birthday_keyboards import get_birthday_actions_keyboard
import logging

logger = logging.getLogger(__name__)

# Шаблон сообщения
BIRTHDAY_NOTIFICATION = (
    "🌟 Доброе утро!\n\n"
    "{when}: <b>{date}</b> 📅\n"
    "День Рождения! 🎉\n"
    "Именинник: <b>{full_name}</b>\n\n"
    "{gift_text}"
)

LOG_NO_BIRTHDAYS = "Нет дней рождения {when}"
LOG_REMINDERS_SENT = "Отправлены напоминания о {count} днях рождения ({when})"
LOG_NO_RECIPIENTS = "Нет получателей для отправки сообщений"


async def send_birthday_notifications(bot: Bot, days_before: int) -> None:
    """Отправляет напоминания о предстоящих днях рождения за days_before дней."""
    today = datetime.now()
    target_date = today + timedelta(days=days_before)
    when_text = "Через неделю" if days_before == 7 else "Завтра"

    try:
        # Для уведомления "Завтра" загружаем пользователей вместе с переводами
        with_transfers = days_before == 1
        all_users = await pg_db.get_all_users(with_transfers=with_transfers)
        if not all_users:
            logger.warning(LOG_NO_RECIPIENTS)
            return
    except Exception as e:
        logger.exception(f"Ошибка получения пользователей для напоминаний: {e}")
        return

    birthday_users = [
        user
        for user in all_users
        if user.birth_date.month == target_date.month
        and user.birth_date.day == target_date.day
    ]

    if not birthday_users:
        logger.info(LOG_NO_BIRTHDAYS.format(when=when_text))
        return

    for birthday_user in birthday_users:
        full_name = " ".join(
            [
                birthday_user.last_name,
                birthday_user.first_name,
                birthday_user.patronymic,
            ]
        )

        for recipient in all_users:
            if recipient == birthday_user:
                continue

            # Определяем, показывать ли клавиатуру и текст о подарке
            show_keyboard = True
            gift_text = "Присоединяйтесь к подарку 🎁⬇️"

            # Для уведомления "Завтра" проверяем наличие перевода
            if days_before == 1:
                # Проверяем, есть ли перевод от получателя к имениннику
                has_transfer = any(
                    transfer.birthday_user_id == birthday_user.user_id
                    for transfer in recipient.sent_transfers
                )
                if has_transfer:
                    show_keyboard = False
                    gift_text = ""

            # Формируем сообщение
            message = BIRTHDAY_NOTIFICATION.format(
                when=when_text,
                date=target_date.strftime("%d.%m"),
                full_name=full_name,
                gift_text=gift_text,
            )
            keyboard = (
                get_birthday_actions_keyboard(birthday_user.user_id)
                if show_keyboard
                else None
            )

            try:
                await bot.send_message(
                    recipient.user_id, message, reply_markup=keyboard
                )
            except Exception as e:
                logger.exception(
                    f"Ошибка отправки напоминания о ДР пользователю {recipient.user_id}: {e}"
                )

    logger.info(LOG_REMINDERS_SENT.format(count=len(birthday_users), when=when_text))
