"""
Репозиторий для работы с переводами.
"""

import logging
from datetime import datetime

from sqlalchemy import select, delete, or_, and_, extract
from sqlalchemy.orm import selectinload

from db_handler.models import Transfer, User, Greeting
from exceptions import RecordNotFound
from .base import BaseRepository

logger = logging.getLogger(__name__)


class TransferRepository(BaseRepository[Transfer]):
    """Репозиторий для работы с переводами."""

    model = Transfer

    async def add(
        self,
        sender_id: int,
        birthday_user_id: int,
        transfer_datetime: datetime,
    ) -> bool:
        """
        Добавить запись о переводе.
        
        Returns:
            True если перевод добавлен, False если уже существует
        """
        sender_id = int(sender_id)
        birthday_user_id = int(birthday_user_id)

        async with self._session_factory() as session:
            # Проверяем существование пользователей
            sender = await session.get(User, sender_id)
            if not sender:
                raise RecordNotFound(entity=User.__name__, entity_id=sender_id)

            birthday_user = await session.get(User, birthday_user_id)
            if not birthday_user:
                raise RecordNotFound(entity=User.__name__, entity_id=birthday_user_id)

            # Проверяем, не было ли уже перевода
            existing = await session.execute(
                select(Transfer).where(
                    Transfer.sender_id == sender_id,
                    Transfer.birthday_user_id == birthday_user_id,
                )
            )

            if existing.scalar_one_or_none():
                logger.warning(
                    f"Перевод уже существует: {sender_id} -> {birthday_user_id}"
                )
                return False

            transfer = Transfer(
                sender_id=sender_id,
                birthday_user_id=birthday_user_id,
                transfer_datetime=transfer_datetime,
            )
            session.add(transfer)
            await session.commit()
            await session.refresh(transfer)

            logger.info(
                f"✅ Добавлен перевод: {sender_id} -> {birthday_user_id}, ID: {transfer.id}"
            )
            return True

    async def get_for_birthday_user(self, birthday_user_id: int) -> list[Transfer]:
        """Получить все переводы для именинника."""
        birthday_user_id = int(birthday_user_id)

        async with self._session_factory() as session:
            result = await session.execute(
                select(Transfer)
                .where(Transfer.birthday_user_id == birthday_user_id)
                .order_by(Transfer.transfer_datetime.desc())
            )
            return list(result.scalars().all())

    async def get_all(self) -> list[Transfer]:
        """Получить все переводы с данными отправителей и именинников."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Transfer)
                .options(
                    selectinload(Transfer.sender),
                    selectinload(Transfer.birthday_user),
                )
                .order_by(Transfer.birthday_user_id, Transfer.transfer_datetime.desc())
            )
            return list(result.scalars().all())

    async def clear_past_birthday_records(self) -> None:
        """Очистка записей переводов для пользователей с прошедшими ДР."""
        current = datetime.now()

        async with self._session_factory() as session:
            # Находим пользователей с прошедшими ДР
            result = await session.execute(
                select(User).where(
                    or_(
                        extract("month", User.birth_date) < current.month,
                        and_(
                            extract("month", User.birth_date) == current.month,
                            extract("day", User.birth_date) < current.day,
                        ),
                    )
                )
            )
            past_birthday_users = result.scalars().all()

            if past_birthday_users:
                user_ids = [user.user_id for user in past_birthday_users]

                # Удаляем переводы
                await session.execute(
                    delete(Transfer).where(Transfer.birthday_user_id.in_(user_ids))
                )

                # Удаляем поздравления
                await session.execute(
                    delete(Greeting).where(Greeting.birthday_user_id.in_(user_ids))
                )

                await session.commit()
                logger.info(f"✅ Cleared birthday records for {len(user_ids)} users")

