"""
Репозиторий для работы с желаниями.
"""

import logging
from sqlalchemy import select

from db_handler.models import Wish, User
from exceptions import RecordNotFound
from .base import BaseRepository

logger = logging.getLogger(__name__)


class WishRepository(BaseRepository[Wish]):
    """Репозиторий для работы с желаниями."""

    model = Wish

    async def add(
        self,
        user_id: int,
        wish_text: str,
        wish_url: str | None = None,
    ) -> Wish:
        """Добавить желание."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            # Проверяем существование пользователя
            user = await session.get(User, user_id)
            if not user:
                raise RecordNotFound(entity=User.__name__, entity_id=user_id)

            wish = Wish(user_id=user_id, wish_text=wish_text, wish_url=wish_url)
            session.add(wish)
            await session.commit()
            await session.refresh(wish)

            logger.info(f"✅ Wish added for user {user_id}, wish_id: {wish.id}")
            return wish

    async def get(self, wish_id: int) -> Wish:
        """Получить желание по ID."""
        wish_id = int(wish_id)

        async with self._session_factory() as session:
            wish = await session.get(Wish, wish_id)
            if not wish:
                raise RecordNotFound(entity=Wish.__name__, entity_id=wish_id)
            return wish

    async def get_list(self, user_id: int) -> list[Wish]:
        """Получить все желания пользователя."""
        user_id = int(user_id)

        async with self._session_factory() as session:
            result = await session.execute(
                select(Wish).where(Wish.user_id == user_id).order_by(Wish.id)
            )
            return list(result.scalars().all())

    async def update(
        self,
        wish_id: int,
        user_id: int,
        wish_text: str | None = None,
        wish_url: str | None = None,
    ) -> Wish:
        """Обновить желание."""
        wish_id = int(wish_id)
        user_id = int(user_id)

        async with self._session_factory() as session:
            wish = await session.get(Wish, wish_id)

            if not wish or wish.user_id != user_id:
                raise RecordNotFound(
                    entity=Wish.__name__,
                    entity_id=wish_id,
                    details={"user_id": user_id},
                )

            if wish_text:
                wish.wish_text = wish_text
            if wish_url is not None:
                wish.wish_url = wish_url

            await session.commit()
            logger.info(f"✅ Wish {wish_id} updated by user {user_id}")
            return wish

    async def delete(self, wish_id: int, user_id: int) -> None:
        """Удалить желание."""
        wish_id = int(wish_id)
        user_id = int(user_id)

        async with self._session_factory() as session:
            wish = await session.get(Wish, wish_id)

            if not wish or wish.user_id != user_id:
                raise RecordNotFound(
                    entity=Wish.__name__,
                    entity_id=wish_id,
                    details={"user_id": user_id},
                )

            await session.delete(wish)
            await session.commit()
            logger.info(f"✅ Wish {wish_id} deleted by user {user_id}")

