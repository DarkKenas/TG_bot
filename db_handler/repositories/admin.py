"""
Репозиторий для работы с администраторами.
"""

import logging
from sqlalchemy import select

from db_handler.models import Administrator
from exceptions import RecordNotFound, RecordAlreadyExists
from .base import BaseRepository

logger = logging.getLogger(__name__)


class AdminRepository(BaseRepository[Administrator]):
    """Репозиторий для работы с администраторами."""

    model = Administrator

    async def add(self, user_id: int) -> Administrator:
        """Создать администратора."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            existing = await session.get(Administrator, user_id)
            if existing:
                raise RecordAlreadyExists(entity=Administrator.__name__, entity_id=user_id)

            admin = Administrator(user_id=user_id)
            session.add(admin)
            await session.commit()

            logger.info(f"✅ Создан администратор для пользователя {user_id}")
            return admin

    async def get(self, user_id: int) -> Administrator:
        """Получить администратора по user_id."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            return await self._get_by_user_id(user_id, session)

    async def delete(self, user_id: int) -> None:
        """Удалить администратора."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            admin = await self._get_by_user_id(user_id, session)
            await session.delete(admin)
            await session.commit()
            logger.info(f"✅ Admin {user_id} deleted from database")

    async def get_all(self) -> list[Administrator]:
        """Получить всех администраторов."""
        async with self._session_factory() as session:
            result = await session.execute(select(Administrator))
            return list(result.scalars().all())

