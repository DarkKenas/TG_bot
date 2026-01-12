"""
Репозиторий для работы с сервисным пользователем.
"""

import logging
from sqlalchemy import select

from db_handler.models import ServiceUser
from .base import BaseRepository

logger = logging.getLogger(__name__)


class ServiceUserRepository(BaseRepository[ServiceUser]):
    """Репозиторий для работы с сервисным пользователем."""

    model = ServiceUser

    async def set(self, user_id: int) -> ServiceUser:
        """Установить сервисного пользователя."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            result = await session.execute(select(ServiceUser))
            service_user = result.scalars().first()

            if service_user:
                service_user.user_id = user_id
            else:
                service_user = ServiceUser(user_id=user_id)
                session.add(service_user)

            await session.commit()
            logger.info(f"✅ Установлен сервисный пользователь: {user_id}")
            return service_user

    async def get(self) -> ServiceUser:
        """Получить сервисного пользователя."""
        async with self._session_factory() as session:
            result = await session.execute(select(ServiceUser))
            return result.scalar_one()

    async def init(self, user_id: int) -> None:
        """Инициализировать сервисного пользователя (если не существует)."""
        async with self._session_factory() as session:
            result = await session.execute(select(ServiceUser))
            existing = result.scalars().first()

            if not existing:
                session.add(ServiceUser(user_id=user_id))
                await session.commit()
                logger.info(f"✅ Инициализирован сервисный пользователь: {user_id}")

