"""
Репозиторий для работы с сервисным пользователем.
"""

import logging
from sqlalchemy import select

from db_handler.models import ServiceUser, User
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
        """
        Инициализировать сервисного пользователя (если не существует).
        
        Если пользователя с указанным user_id еще нет в таблице users,
        инициализация пропускается с предупреждением.
        """
        async with self._session_factory() as session:
            # Проверяем, существует ли service_user
            result = await session.execute(select(ServiceUser))
            existing = result.scalars().first()

            if existing:
                logger.info(f"ℹ️ Сервисный пользователь уже существует: {existing.user_id}")
                return

            # Проверяем, существует ли пользователь в таблице users
            user = await session.get(User, user_id)
            if not user:
                logger.warning(
                    f"⚠️ Пользователь {user_id} не найден в таблице users. "
                    f"Инициализация service_user пропущена. "
                    f"Пользователь может получить права service_user после регистрации через команду /get_service_user"
                )
                return

            # Создаем service_user только если пользователь существует
            session.add(ServiceUser(user_id=user_id))
            await session.commit()
            logger.info(f"✅ Инициализирован сервисный пользователь: {user_id}")

