"""
Репозиторий для работы с коллекторами (сборщиками средств).
"""

import logging
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from db_handler.models import Collector
from exceptions import RecordNotFound, RecordAlreadyExists, CollectorUniquenessError
from .base import BaseRepository

logger = logging.getLogger(__name__)


class CollectorRepository(BaseRepository[Collector]):
    """Репозиторий для работы с коллекторами."""

    model = Collector

    async def create(
        self,
        user_id: int,
        phone_number: str,
        bank_name: str | None = None,
    ) -> Collector:
        """Создать коллектора (неактивного)."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            existing = await session.execute(
                select(Collector).where(Collector.user_id == user_id)
            )
            if existing.scalar_one_or_none():
                raise RecordAlreadyExists(entity=Collector.__name__, entity_id=user_id)

            collector = Collector(
                user_id=user_id,
                phone_number=phone_number,
                bank_name=bank_name,
                is_active=False,
            )
            session.add(collector)
            await session.commit()
            await session.refresh(collector)

            logger.info(f"✅ Создан неактивный коллектор для пользователя {user_id}")
            return collector

    async def get(self, user_id: int) -> Collector:
        """Получить коллектора по user_id."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            return await self._get_by_user_id(user_id, session, load_user=True)

    async def get_all(self) -> list[Collector]:
        """Получить всех коллекторов с данными пользователей."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Collector).options(selectinload(Collector.user))
            )
            return list(result.scalars().all())

    async def update(
        self,
        user_id: int,
        phone_number: str | None = None,
        bank_name: str | None = None,
    ) -> Collector:
        """Обновить данные коллектора."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            collector = await self._get_by_user_id(user_id, session)

            if phone_number is not None:
                collector.phone_number = phone_number
            if bank_name is not None:
                collector.bank_name = bank_name

            await session.commit()
            await session.refresh(collector)

            logger.info(f"✅ Обновлен коллектор для пользователя {user_id}")
            return collector

    async def get_active(self) -> Collector:
        """Получить активного коллектора."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Collector)
                .options(selectinload(Collector.user))
                .where(Collector.is_active == True)
            )
            collector = result.scalar_one_or_none()

            if not collector:
                raise RecordNotFound(
                    message="Активный коллектор не найден",
                    entity=Collector.__name__,
                )

            return collector

    async def set_active(self, user_id: int) -> Collector:
        """Назначить активного коллектора."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            # Проверяем существование коллектора
            result = await session.execute(
                select(Collector).where(Collector.user_id == user_id)
            )
            collector = result.scalar_one_or_none()

            if not collector:
                raise RecordNotFound(entity=Collector.__name__, entity_id=user_id)

            # Деактивируем текущего
            await self._deactivate_current(session)

            # Активируем нового
            collector.is_active = True
            await session.commit()
            await session.refresh(collector)

            logger.info(f"✅ Коллектор {user_id} назначен активным")

            # Проверяем единственность
            await self._validate_single_active()

            return collector

    async def _deactivate_current(self, session) -> None:
        """Деактивировать текущего активного коллектора."""
        result = await session.execute(
            select(Collector).where(Collector.is_active == True)
        )
        collector = result.scalar_one_or_none()

        if collector:
            collector.is_active = False
            logger.info(f"Деактивирован коллектор {collector.user_id}")

    async def _validate_single_active(self) -> None:
        """Проверить, что активен только один коллектор."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(func.count(Collector.id)).where(Collector.is_active == True)
            )
            count = result.scalar()

            if count > 1:
                logger.error(f"⚠️ Найдено {count} активных коллекторов!")
                raise CollectorUniquenessError(count)

