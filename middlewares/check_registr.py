import logging
from collections.abc import Callable, Awaitable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from keyboards.register_keyboards import get_registration_keyboard
from keyboards.main_menu_keyboards import get_main_menu_keyboard
from exceptions import RecordNotFound

logger = logging.getLogger(__name__)


class RegistrationMiddleware(BaseMiddleware):
    """Middleware для проверки регистрации пользователя.

    Загружает пользователя из БД и добавляет в data.
    Если не зарегистрирован - предлагает зарегистрироваться.

    Пропускает без регистрации:
    - Команду /start
    - Callback 'register'
    - Все состояния, начинающиеся с 'UserDataStates:'
    
    Требует: DIMiddleware должен быть зарегистрирован раньше.
    """

    # Команды и callback-и, доступные без регистрации
    ALLOWED_COMMANDS: set[str] = {"/start"}
    REGISTER_CALLBACKS: set[str] = {"register"}
    USER_DATA_STATE_PREFIX: str = "UserDataStates:"

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        db = data["db"]  # Получаем db из DIMiddleware
        user_id = event.from_user.id

        # Загружаем пользователя (связи administrator, collector, service_user
        # загружаются автоматически благодаря lazy="joined")
        try:
            user = await db.get_user(user_id)
        except RecordNotFound:
            user = None
        except Exception as e:
            logger.exception(f"Ошибка при загрузке пользователя {user_id}: {e}")
            await event.answer("Ошибка сервера при проверке регистрации")
            return

        # Добавляем пользователя в data
        data["user"] = user

        # Если пользователь зарегистрирован
        if user:
            # Загружаем активного коллектора (нужен для отображения данных сбора)
            try:
                data["active_collector"] = await db.get_active_collector()
            except RecordNotFound:
                data["active_collector"] = None

            # Если пытается зарегистрироваться повторно
            if (
                isinstance(event, CallbackQuery)
                and event.data in self.REGISTER_CALLBACKS
            ):
                await event.bot.send_message(
                    event.from_user.id,
                    "Вы уже зарегистрированы 😊",
                    reply_markup=await get_main_menu_keyboard(
                        is_admin=user.is_admin,
                        is_collector=user.is_collector,
                    ),
                )
                return

            return await handler(event, data)

        # Пользователь не зарегистрирован
        data["active_collector"] = None

        # Проверяем состояние FSM (для процесса регистрации)
        current_state: str | None = data.get("raw_state")
        if current_state and current_state.startswith(self.USER_DATA_STATE_PREFIX):
            return await handler(event, data)

        # Пропускаем разрешённые команды и callback-и
        if isinstance(event, Message) and event.text in self.ALLOWED_COMMANDS:
            return await handler(event, data)

        if isinstance(event, CallbackQuery) and event.data in self.REGISTER_CALLBACKS:
            return await handler(event, data)

        # Предлагаем зарегистрироваться
        await event.answer(
            "Вы не зарегистрированы.\nДля регистрации нажмите на кнопку 📝:",
            reply_markup=get_registration_keyboard(),
        )
