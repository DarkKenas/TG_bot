"""
Универсальный middleware для проверки ролей.
"""

from collections.abc import Callable, Awaitable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery


class RoleMiddleware(BaseMiddleware):
    """
    Middleware для проверки роли пользователя.
    
    Использование:
        admin_router.message.middleware(RequireAdmin)
        service_router.message.middleware(RequireServiceUser)
    """

    ROLE_ERRORS = {
        "admin": "❌ У вас нет прав администратора",
        "service_user": "❌ У вас нет прав сервисного пользователя",
        "collector": "❌ У вас нет прав коллектора",
    }

    def __init__(self, required_role: str) -> None:
        """
        Args:
            required_role: Требуемая роль ("admin", "service_user", "collector")
        """
        self.required_role = required_role

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("user")

        # Проверяем роль
        has_role = False
        if user:
            if self.required_role == "admin":
                has_role = user.is_admin
            elif self.required_role == "service_user":
                has_role = user.is_service_user
            elif self.required_role == "collector":
                has_role = user.is_collector

        if not has_role:
            error_msg = self.ROLE_ERRORS.get(
                self.required_role,
                "❌ Недостаточно прав"
            )
            await self._send_error(event, error_msg)
            return

        return await handler(event, data)

    @staticmethod
    async def _send_error(event: Message | CallbackQuery, message: str) -> None:
        """Отправить сообщение об ошибке."""
        if isinstance(event, Message):
            await event.answer(message)
        else:
            await event.answer(message, show_alert=True)


# Готовые экземпляры для удобства импорта
RequireAdmin = RoleMiddleware("admin")
RequireServiceUser = RoleMiddleware("service_user")
RequireCollector = RoleMiddleware("collector")
