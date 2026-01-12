"""
Базовый репозиторий с общими методами.
"""

from typing import TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db_handler.models import Base
from exceptions import RecordNotFound

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Базовый репозиторий с CRUD операциями."""

    model: type[T]

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def _get_by_user_id(
        self,
        user_id: int,
        session: AsyncSession,
        load_user: bool = False,
    ) -> T:
        """
        Получить объект по user_id.
        
        Args:
            user_id: ID пользователя
            session: Активная сессия
            load_user: Загружать ли связанного пользователя
        
        Raises:
            RecordNotFound: Если объект не найден
        """
        query = select(self.model).where(self.model.user_id == user_id)

        if load_user and hasattr(self.model, "user"):
            query = query.options(selectinload(self.model.user))

        result = await session.execute(query)
        obj = result.scalar_one_or_none()

        if not obj:
            raise RecordNotFound(entity=self.model.__name__, entity_id=user_id)

        return obj

