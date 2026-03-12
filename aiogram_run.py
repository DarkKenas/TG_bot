import asyncio
import logging
from create_bot import bot, dp, scheduler, pg_db, default_service_user_id
from handlers.start import start_router
from handlers.register import register_router
from handlers.wish_handler import wishlist_router
from handlers.main_menu import main_menu_router
from handlers.birthday_handler import birthday_router
from handlers.admin_handler import admin_router
from handlers.collector_handler import collector_router
from handlers.service_user_handler import service_user_router
from handlers.set_role_handler import role_router
from middlewares import (
    DIMiddleware,
    RegistrationMiddleware,
    RequireAdmin,
    RequireServiceUser,
)
from scheduler_functions.birthday_notification import send_birthday_notifications
from scheduler_functions.assign_backup_collector import assign_backup_collector

logger = logging.getLogger(__name__)


async def shutdown():
    """Корректное завершение работы бота"""
    logger.info("Остановка бота...")

    # Останавливаем scheduler
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler остановлен")

    # Закрываем соединение с БД
    try:
        await pg_db.close_pool()
        logger.info("Соединение с БД закрыто")
    except Exception as e:
        logger.exception(f"Ошибка при закрытии БД: {e}")

    # Закрываем сессию бота
    try:
        await bot.session.close()
        logger.info("Сессия бота закрыта")
    except Exception as e:
        logger.exception(f"Ошибка при закрытии сессии бота: {e}")


async def main():
    try:
        await pg_db.create_pool()
        await pg_db.init_data(default_service_user_id)

        scheduler.add_job(
            send_birthday_notifications,
            "cron",
            hour=16,
            minute=23,
            args=(bot, 7, pg_db),
        )
        scheduler.add_job(
            send_birthday_notifications,
            "cron",
            hour=16,
            minute=23,
            args=(bot, 1, pg_db),
        )
        scheduler.add_job(pg_db.clear_past_birthday_records, "cron", hour=0, minute=0)

        # Автоматическое назначение запасного коллектора 24 февраля в 9:00
        scheduler.add_job(
            assign_backup_collector,
            "cron",
            month=2,
            day=24,
            hour=9,
            minute=0,
            args=(bot, pg_db),
        )

        scheduler.start()

        # Глобальные middleware (порядок важен: DI → Registration → Role)
        dp.message.middleware(DIMiddleware(pg_db))
        dp.callback_query.middleware(DIMiddleware(pg_db))
        dp.message.middleware(RegistrationMiddleware())
        dp.callback_query.middleware(RegistrationMiddleware())

        # Middleware для ролей (готовые экземпляры)
        admin_router.message.middleware(RequireAdmin)
        admin_router.callback_query.middleware(RequireAdmin)
        service_user_router.message.middleware(RequireServiceUser)
        service_user_router.callback_query.middleware(RequireServiceUser)

        dp.include_routers(start_router, main_menu_router)
        dp.include_routers(register_router, wishlist_router, birthday_router)
        dp.include_routers(
            admin_router, collector_router, service_user_router, role_router
        )
        await bot.delete_webhook(drop_pending_updates=True)

        logger.info("Бот запущен")
        await dp.start_polling(bot)

    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
    finally:
        await shutdown()


if __name__ == "__main__":
    asyncio.run(main())
