from datetime import datetime, timedelta
from aiogram import Bot
import logging

from db_handler import PostgresHandler
from keyboards.birthday_keyboards import get_birthday_actions_keyboard

logger = logging.getLogger(__name__)

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


async def send_birthday_notifications(
    bot: Bot, days_before: int, db: PostgresHandler
) -> None:
    """Отправляет напоминания о предстоящих днях рождения за days_before дней."""
    today = datetime.now()
    target_date = today + timedelta(days=days_before)
    when_text = "Через неделю" if days_before == 7 else "Завтра"

    try:
        with_transfers = days_before == 1
        all_users = await db.get_all_users(with_transfers=with_transfers)
        if not all_users:
            logger.warning(LOG_NO_RECIPIENTS)
            return
    except Exception as e:
        logger.exception(f"Ошибка получения пользователей для напоминаний: {e}")
        return

    birthday_users = [
        user
        for user in all_users
        if user.birth_date
        and user.birth_date.month == target_date.month
        and user.birth_date.day == target_date.day
    ]

    if not birthday_users:
        logger.info(LOG_NO_BIRTHDAYS.format(when=when_text))
        return

    for birthday_user in birthday_users:
        # Безопасное формирование полного имени
        name_parts = [
            birthday_user.last_name or "",
            birthday_user.first_name or "",
            birthday_user.patronymic or "",
        ]
        full_name = " ".join(filter(None, name_parts)).strip()
        if not full_name:
            full_name = f"Пользователь {birthday_user.user_id}"

        for recipient in all_users:
            if recipient == birthday_user:
                continue

            show_keyboard = True
            gift_text = "Присоединяйтесь к подарку 🎁⬇️"

            if days_before == 1:
                has_transfer = any(
                    transfer.birthday_user_id == birthday_user.user_id
                    for transfer in recipient.sent_transfers
                )
                if has_transfer:
                    show_keyboard = False
                    gift_text = ""

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
                # Обработка различных типов ошибок
                error_msg = str(e).lower()
                if "blocked" in error_msg or "chat not found" in error_msg:
                    logger.warning(
                        f"Пользователь {recipient.user_id} заблокировал бота или чат не найден"
                    )
                elif "forbidden" in error_msg:
                    logger.warning(
                        f"Нет доступа к пользователю {recipient.user_id}"
                    )
                else:
                    logger.exception(
                        f"Ошибка отправки напоминания о ДР пользователю {recipient.user_id}: {e}"
                    )

    logger.info(LOG_REMINDERS_SENT.format(count=len(birthday_users), when=when_text))
