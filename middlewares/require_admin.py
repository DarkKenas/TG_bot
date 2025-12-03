from typing import Callable, Dict, Any, Awaitable, Union
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

MSG_NO_ADMIN = "❌ У вас нет прав администратора"

class RequireAdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[
            [Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]
        ],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        """Проверка наличия прав администратора

        Args:
            handler: Следующий обработчик в цепочке
            event: Входящее сообщение или callback
            data: Дополнительные данные события

        Returns:
            Any: Результат обработки события
        """
        admin = data.get("admin")
        if not admin:
            if hasattr(event, "answer"):
                await event.answer(MSG_NO_ADMIN)
            elif hasattr(event, "message"):
                await event.message.answer(MSG_NO_ADMIN)
            return
        return await handler(event, data)