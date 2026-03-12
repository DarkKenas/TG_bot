"""
Скрипт для выполнения миграции БД: добавление полей gift_text и gift_url в таблицу transfers.
"""

import asyncio
import logging
from sqlalchemy import text
from config import get_settings
from db_handler.session import DatabaseSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_migration():
    """Выполнить миграцию: добавить поля gift_text и gift_url в таблицу transfers."""
    settings = get_settings()
    session = DatabaseSession(settings.pg_link)
    
    try:
        logger.info("🔧 Подключаюсь к БД...")
        await session.connect()
        
        async with session.get_session()() as db_session:
            # SQL команды для миграции
            # Добавляем поле gift_text
            try:
                await db_session.execute(
                    text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS gift_text TEXT")
                )
                logger.info("✅ Поле gift_text добавлено")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при добавлении gift_text (возможно, уже существует): {e}")
            
            # Добавляем поле gift_url
            try:
                await db_session.execute(
                    text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS gift_url TEXT")
                )
                logger.info("✅ Поле gift_url добавлено")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при добавлении gift_url (возможно, уже существует): {e}")
            
            await db_session.commit()
            
            logger.info("🎉 Миграция выполнена успешно!")
            logger.info("   Добавлены поля: gift_text, gift_url в таблицу transfers")
            
    except Exception as e:
        logger.exception(f"❌ Ошибка при выполнении миграции: {e}")
        raise
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(run_migration())
