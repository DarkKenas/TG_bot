"""
Репозиторий для работы с пользователями.
"""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db_handler.models import User
from exceptions import RecordNotFound, RecordAlreadyExists
from .base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """Репозиторий для работы с пользователями."""

    model = User

    async def add(
        self,
        user_id: int,
        username: str,
        last_name: str,
        first_name: str,
        patronymic: str,
        birth_date: date,
    ) -> User:
        """Добавить нового пользователя."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            existing = await session.get(User, user_id)
            if existing:
                raise RecordAlreadyExists(entity=User.__name__, entity_id=user_id)

            user = User(
                user_id=user_id,
                username=username,
                last_name=last_name,
                first_name=first_name,
                patronymic=patronymic,
                birth_date=birth_date,
            )
            session.add(user)
            await session.commit()
            logger.info(f"✅ User {user_id} added to database")
            return user

    async def update(
        self,
        user_id: int,
        username: str,
        last_name: str | None = None,
        first_name: str | None = None,
        patronymic: str | None = None,
        birth_date: date | None = None,
    ) -> User:
        """Обновить данные пользователя."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                raise RecordNotFound(entity=User.__name__, entity_id=user_id)

            user.username = username
            if last_name:
                user.last_name = last_name
            if first_name:
                user.first_name = first_name
            if patronymic:
                user.patronymic = patronymic
            if birth_date:
                user.birth_date = birth_date

            await session.commit()
            logger.info(f"✅ User {user_id} updated in database")
            return user

    async def delete(self, user_id: int) -> None:
        """Удалить пользователя."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                raise RecordNotFound(entity=User.__name__, entity_id=user_id)

            await session.delete(user)
            await session.commit()
            logger.info(f"✅ User {user_id} deleted from database")

    async def get(self, user_id: int) -> User:
        """Получить пользователя по ID."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            user = await session.get(User, user_id)
            if not user:
                raise RecordNotFound(entity=User.__name__, entity_id=user_id)
            return user

    async def get_all(self, with_transfers: bool = False) -> list[User]:
        """
        Получить всех пользователей.
        
        Args:
            with_transfers: Загружать ли переводы пользователей
        """
        async with self._session_factory() as session:
            query = select(User)

            if with_transfers:
                query = query.options(selectinload(User.sent_transfers))

            result = await session.execute(query)
            return list(result.scalars().all())

