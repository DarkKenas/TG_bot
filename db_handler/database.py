"""
Главный класс для работы с базой данных.

Объединяет все репозитории и управление сессиями.
"""

import logging

from .session import DatabaseSession
from .repositories import (
    UserRepository,
    WishRepository,
    TransferRepository,
    AdminRepository,
    CollectorRepository,
    ServiceUserRepository,
)

logger = logging.getLogger(__name__)


class PostgresHandler:
    """
    Главный класс для работы с БД.
    
    Предоставляет доступ к репозиториям:
        db.users.get(user_id)
        db.wishes.add(...)
        db.collectors.set_active(...)
    """

    def __init__(self, db_url: str):
        self._session = DatabaseSession(db_url)

        # Репозитории инициализируются после подключения
        self.users: UserRepository | None = None
        self.wishes: WishRepository | None = None
        self.transfers: TransferRepository | None = None
        self.admins: AdminRepository | None = None
        self.collectors: CollectorRepository | None = None
        self.service_users: ServiceUserRepository | None = None

    async def create_pool(self) -> None:
        """Инициализация подключения и репозиториев."""
        await self._session.connect()

        # Создаём репозитории с фабрикой сессий
        session_factory = self._session.get_session()
        
        self.users = UserRepository(session_factory)
        self.wishes = WishRepository(session_factory)
        self.transfers = TransferRepository(session_factory)
        self.admins = AdminRepository(session_factory)
        self.collectors = CollectorRepository(session_factory)
        self.service_users = ServiceUserRepository(session_factory)

        logger.info("✅ All repositories initialized")

    async def close_pool(self) -> None:
        """Закрытие подключения."""
        await self._session.disconnect()

    async def init_data(self, service_user_id: int) -> None:
        """Инициализация начальных данных."""
        await self.service_users.init(service_user_id)
        logger.info("✅ Data initialization successful")

    # === Методы-алиасы для обратной совместимости ===
    # (можно будет удалить после полного перехода на репозитории)

    async def get_user(self, user_id: int):
        return await self.users.get(user_id)

    async def add_user(self, **kwargs):
        return await self.users.add(**kwargs)

    async def update_user(self, **kwargs):
        return await self.users.update(**kwargs)

    async def delete_user(self, user_id: int):
        return await self.users.delete(user_id)

    async def get_all_users(self, with_transfers: bool = False):
        return await self.users.get_all(with_transfers=with_transfers)

    async def get_wish(self, wish_id: int):
        return await self.wishes.get(wish_id)

    async def add_wish(self, **kwargs):
        return await self.wishes.add(**kwargs)

    async def update_wish(self, **kwargs):
        return await self.wishes.update(**kwargs)

    async def delete_wish(self, wish_id: int, user_id: int):
        return await self.wishes.delete(wish_id, user_id)

    async def get_wish_list(self, user_id: int):
        return await self.wishes.get_list(user_id)

    async def add_transfer(self, **kwargs):
        return await self.transfers.add(**kwargs)

    async def get_all_transfers(self):
        return await self.transfers.get_all()

    async def clear_past_birthday_records(self):
        return await self.transfers.clear_past_birthday_records()

    async def add_administrator(self, user_id: int):
        return await self.admins.add(user_id)

    async def get_administrator(self, user_id: int):
        return await self.admins.get(user_id)

    async def delete_administrator(self, user_id: int):
        return await self.admins.delete(user_id)

    async def get_all_administrators(self):
        return await self.admins.get_all()

    async def create_collector(self, **kwargs):
        return await self.collectors.create(**kwargs)

    async def get_collector(self, user_id: int):
        return await self.collectors.get(user_id)

    async def update_collector(self, **kwargs):
        return await self.collectors.update(**kwargs)

    async def get_active_collector(self):
        return await self.collectors.get_active()

    async def set_active_collector(self, user_id: int):
        return await self.collectors.set_active(user_id)

    async def set_service_user(self, user_id: int):
        return await self.service_users.set(user_id)

    async def get_service_user(self):
        return await self.service_users.get()

