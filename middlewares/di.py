"""
Middleware для Dependency Injection.

Добавляет зависимости в data, чтобы handlers могли получать их как параметры.
"""

from collections.abc import Callable, Awaitable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from db_handler import PostgresHandler


class DIMiddleware(BaseMiddleware):
    """
    Middleware для инъекции зависимостей.
    
    Использование в handler:
        async def my_handler(message: Message, db: PostgresHandler):
            user = await db.get_user(message.from_user.id)
    """

    def __init__(self, db: PostgresHandler) -> None:
        self.db = db

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        # Инжектим зависимости в data
        data["db"] = self.db
        
        return await handler(event, data)

