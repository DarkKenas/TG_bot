"""
Скрипт для ручной инициализации базы данных.
Создает все таблицы и инициализирует начальные данные.
"""

import asyncio
import logging
from config import get_settings
from db_handler import PostgresHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def init_database():
    """Инициализация базы данных."""
    settings = get_settings()
    db = PostgresHandler(settings.pg_link)
    
    try:
        logger.info("🔧 Начинаю инициализацию БД...")
        
        # Создаем подключение и таблицы
        await db.create_pool()
        logger.info("✅ Таблицы созданы успешно")
        
        # Инициализируем начальные данные
        await db.init_data(settings.default_service_user_id)
        logger.info("✅ Начальные данные инициализированы")
        
        logger.info("🎉 Инициализация завершена успешно!")
        
    except Exception as e:
        logger.exception(f"❌ Ошибка при инициализации: {e}")
        raise
    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(init_database())
