"""
Автоматическое назначение запасного коллектора 24 февраля.
"""

import logging
from aiogram import Bot
from db_handler import PostgresHandler
from config import get_settings
from exceptions import RecordNotFound

logger = logging.getLogger(__name__)


async def assign_backup_collector(bot: Bot, db: PostgresHandler) -> None:
    """
    Автоматически назначает запасного коллектора 24 февраля.
    
    Если назначение не удалось, отправляет предупреждение всем админам.
    """
    settings = get_settings()
    backup_user_id = settings.backup_collector_user_id

    if not backup_user_id:
        logger.warning("BACKUP_COLLECTOR_USER_ID не задан в .env")
        await notify_admins_no_backup_config(bot, db)
        return

    try:
        # Пытаемся назначить запасного коллектора активным
        await db.set_active_collector(backup_user_id)
        logger.info(f"✅ 24 февраля автоматически назначен запасной коллектор {backup_user_id}")
    except RecordNotFound:
        error_msg = f"Пользователь с ID {backup_user_id} не найден или не является коллектором"
        logger.error(f"❌ {error_msg}")
        await notify_admins_error(bot, db, error_msg)
    except Exception as e:
        error_msg = f"Ошибка при назначении запасного коллектора: {e}"
        logger.exception(f"❌ {error_msg}")
        await notify_admins_error(bot, db, error_msg)


async def notify_admins_no_backup_config(bot: Bot, db: PostgresHandler) -> None:
    """Уведомить админов, что не задан BACKUP_COLLECTOR_USER_ID."""
    try:
        admins = await db.get_all_administrators()
        if not admins:
            logger.warning("Нет администраторов для отправки уведомления")
            return

        message = (
            "⚠️ <b>Предупреждение</b>\n\n"
            "Не удалось автоматически назначить запасного коллектора 24 февраля:\n"
            "не задан BACKUP_COLLECTOR_USER_ID в файле .env"
        )

        for admin in admins:
            try:
                await bot.send_message(admin.user_id, message)
                logger.info(f"✅ Уведомление отправлено админу {admin.user_id}")
            except Exception as e:
                error_msg = str(e).lower()
                if "blocked" in error_msg or "chat not found" in error_msg:
                    logger.warning(f"Админ {admin.user_id} заблокировал бота")
                else:
                    logger.exception(f"Ошибка отправки уведомления админу {admin.user_id}: {e}")
    except Exception as e:
        logger.exception(f"Ошибка при отправке уведомлений админам: {e}")


async def notify_admins_error(bot: Bot, db: PostgresHandler, error_details: str) -> None:
    """Уведомить админов об ошибке назначения запасного коллектора."""
    try:
        admins = await db.get_all_administrators()
        if not admins:
            logger.warning("Нет администраторов для отправки уведомления")
            return

        message = (
            "⚠️ <b>Предупреждение</b>\n\n"
            "Не удалось автоматически назначить запасного коллектора 24 февраля.\n\n"
            f"<b>Причина:</b> {error_details}"
        )

        for admin in admins:
            try:
                await bot.send_message(admin.user_id, message)
                logger.info(f"✅ Уведомление об ошибке отправлено админу {admin.user_id}")
            except Exception as e:
                error_msg = str(e).lower()
                if "blocked" in error_msg or "chat not found" in error_msg:
                    logger.warning(f"Админ {admin.user_id} заблокировал бота")
                else:
                    logger.exception(f"Ошибка отправки уведомления админу {admin.user_id}: {e}")
    except Exception as e:
        logger.exception(f"Ошибка при отправке уведомлений админам: {e}")
