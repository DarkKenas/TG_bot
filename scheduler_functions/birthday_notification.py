from datetime import datetime, timedelta
from aiogram import Bot
import logging

from db_handler import PostgresHandler
from keyboards.birthday_keyboards import get_birthday_actions_keyboard
from config import get_settings

logger = logging.getLogger(__name__)

# Шаблоны для разных случаев
BIRTHDAY_NOTIFICATION_TOMORROW = (
    "Доброе утро!\n\n"
    "📅 Напоминание: завтра <b>{date}</b> день рождения отмечает <b>{full_name}</b>\n\n"
    "{payment_block}"
)

BIRTHDAY_NOTIFICATION_WEEK = (
    "Доброе утро!\n\n"
    "📅 <b>{date}</b> день рождения отмечает <b>{full_name}</b>\n\n"
    "{payment_block}"
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

    # Получаем активного коллектора один раз для всех уведомлений
    active_collector = None
    try:
        active_collector = await db.get_active_collector()
    except Exception as e:
        logger.warning(f"Не удалось получить активного коллектора: {e}")

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

            # Если получатель - коллектор, добавляем информацию о возрасте
            age_info = ""
            if recipient.collector and birthday_user.birth_date:
                try:
                    birth_year = birthday_user.birth_date.year
                    age = target_date.year - birth_year
                    if age > 0:
                        if age % 10 == 0:
                            age_info = f"\n\n<b>🎊 Юбилей - {age} лет!</b>\n"
                        else:
                            age_info = f"\n\nИсполняется: <b>{age} лет</b>\n"
                except Exception as e:
                    logger.warning(
                        f"Ошибка вычисления возраста для {birthday_user.user_id}: {e}"
                    )

            # Блок реквизитов (для всех получателей)
            if active_collector:
                collector_user = active_collector.user
                payment_block = (
                    "Перевести деньги на подарок 🎁:\n"
                    f"Кому: {collector_user.initials}\n"
                    f"Куда: <b>{active_collector.bank_name or 'не указан банк'}</b>, "
                    f"{active_collector.phone_number}\n"
                )
            else:
                payment_block = (
                    "Перевести деньги на подарок 🎁:\n"
                    "Ответственный за сбор пока не назначен.\n"
                )

            # Выбираем шаблон в зависимости от days_before
            if days_before == 1:
                message = BIRTHDAY_NOTIFICATION_TOMORROW.format(
                    date=target_date.strftime("%d.%m"),
                    full_name=full_name,
                    payment_block=payment_block,
                )
            else:
                message = BIRTHDAY_NOTIFICATION_WEEK.format(
                    date=target_date.strftime("%d.%m"),
                    full_name=full_name,
                    payment_block=payment_block,
                )

            # Добавляем информацию о возрасте для коллекторов
            if age_info:
                message = message.rstrip() + age_info
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
                    logger.warning(f"Нет доступа к пользователю {recipient.user_id}")
                else:
                    logger.exception(
                        f"Ошибка отправки напоминания о ДР пользователю {recipient.user_id}: {e}"
                    )

    logger.info(LOG_REMINDERS_SENT.format(count=len(birthday_users), when=when_text))
