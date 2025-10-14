import asyncio
from create_bot import bot, dp, scheduler, pg_db
from handlers.start import start_router
from handlers.register import register_router
from handlers.wish_handler import wishlist_router
from handlers.main_menu import main_menu_router
from handlers.birthday_handler import birthday_router
from handlers.admin_handler import admin_router
from handlers.collector_handler import collector_router
from middlewares.check_registr import RegistrationMiddleware
from scheduler_functions.birthday_notification import send_birthday_notifications


async def main():
    await pg_db.create_pool()

    scheduler.add_job(
        send_birthday_notifications, "cron", hour=11, minute=7, args=(bot, 7)
    )
    scheduler.add_job(
        send_birthday_notifications, "cron", hour=11, minute=7, args=(bot, 1)
    )
    scheduler.add_job(pg_db.clear_past_birthday_records, "cron", hour=0, minute=0)
    scheduler.start()

    dp.message.middleware(RegistrationMiddleware())
    dp.callback_query.middleware(RegistrationMiddleware())

    dp.include_routers(start_router, main_menu_router)
    dp.include_routers(register_router, wishlist_router, birthday_router, admin_router, collector_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
