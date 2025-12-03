from typing import Callable, Dict, Any, Awaitable, Union
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from create_bot import pg_db

MSG_NO_SERVICE_USER = "❌ У вас нет прав сервисного пользователя"

class RequireServiceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[
            [Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]
        ],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        """Проверка наличия прав service_user

        Args:
            handler: Следующий обработчик в цепочке
            event: Входящее сообщение или callback
            data: Дополнительные данные события

        Returns:
            Any: Результат обработки события
        """
        try:
            service_user = await pg_db.get_service_user()
        except Exception as e:
            await event.answer("Ошибка получения сервисного пользователя 😵‍💫")
            return
        
        if service_user.user_id != event.from_user.id:
            await event.answer(MSG_NO_SERVICE_USER)
            return
        
        return await handler(event, data)