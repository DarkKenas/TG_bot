"""
Управление подключением к БД и сессиями.
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy import text

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseSession:
    """Класс для управления подключением к БД."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker | None = None

    async def connect(self) -> None:
        """Инициализация подключения к БД."""
        try:
            self.engine = create_async_engine(
                self.db_url,
                pool_pre_ping=True,
            )

            self.session_factory = async_sessionmaker(
                self.engine,
                expire_on_commit=False,
            )

            # Создаём таблицы
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Проверяем подключение
            await self._check_connection()
            logger.info("✅ Database connected successfully")

        except Exception as e:
            logger.exception(f"❌ Database connection failed: {e}")
            raise

    async def disconnect(self) -> None:
        """Закрытие подключения."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")

    async def _check_connection(self) -> None:
        """Проверка подключения к БД."""
        async with self.session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            if result.scalar() != 1:
                raise ConnectionError("Unexpected result from database")

    def get_session(self):
        """Получить фабрику сессий для использования в репозиториях."""
        if not self.session_factory:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.session_factory

