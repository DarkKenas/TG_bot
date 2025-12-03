from typing import Callable, Dict, Any, Awaitable, Union
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from create_bot import pg_db
from keyboards.register_keyboards import get_registration_keyboard
from keyboards.main_menu_keyboards import get_main_menu_keyboard
import logging
from exceptions import RecordNotFound

logger = logging.getLogger(__name__)


class RegistrationMiddleware(BaseMiddleware):
    """Middleware для проверки регистрации пользователя.

    Проверяет, зарегистрирован ли пользователь в системе.
    Если нет - предлагает зарегистрироваться.

    Пропускает без регистрации:
    - Команду /start
    - Callback 'register'
    - Все состояния, начинающиеся с 'UserDataStates:'
    """

    def __init__(self) -> None:
        """Инициализация middleware.

        Устанавливает списки разрешенных команд и callback-ов,
        которые доступны без регистрации.
        """
        # Команды и callback-и, доступные без регистрации
        self._allowed_commands: set[str] = {"/start"}
        self._register_callbacks: set[str] = {"register"}
        # Префикс состояний регистрации
        self._user_data_state_prefix: str = "UserDataStates:"

    async def __call__(
        self,
        handler: Callable[
            [Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]
        ],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        """Обработка события.

        Args:
            handler: Следующий обработчик в цепочке
            event: Входящее сообщение или callback
            data: Дополнительные данные события

        Returns:
            Any: Результат обработки события

        Note:
            Если пользователь не зарегистрирован, отправляет сообщение
            с предложением зарегистрироваться и клавиатурой регистрации.
        """
        user_id = event.from_user.id

        # Проверяем регистрацию пользователя в БД
        try:
            user = await pg_db.get_user(user_id)
        except RecordNotFound:
            user = None
        except Exception as e:
            logger.exception(
                f"Ошибка при проверке регистрации пользователя {user_id}: {e}"
            )
            await event.answer("Ошибка сервера при проверке регистрации")
            return

        # Добавляем информацию о пользователе в data
        data["user"] = user

        # Если пользователь зарегистрирован
        if user:
            # Получаем объекты admin и collector
            try:
                admin = await pg_db.get_administrator(user_id)
            except RecordNotFound:
                admin = None

            try:
                active_collector = await pg_db.get_active_collector()
                collector = await pg_db.get_collector(user_id)
            except RecordNotFound:
                active_collector = None
                collector = None

            data["admin"] = admin
            data["active_collector"] = active_collector
            data["collector"] = collector

            # Если это callback регистрации - сообщаем что уже зарегистрирован
            if (
                isinstance(event, CallbackQuery)
                and event.data in self._register_callbacks
            ):
                await event.bot.send_message(
                    event.from_user.id,
                    "Вы уже зарегистрированы 😊",
                    reply_markup = await get_main_menu_keyboard(
                        is_admin = True if admin else False,
                        is_collector = True if collector else False,
                    ),
                )
                return
            # Иначе пропускаем запрос дальше
            return await handler(event, data)

        data["admin"] = None
        data["collector"] = None

        # Получаем текущее состояние FSM напрямую из data
        current_state: str | None = data.get("raw_state")

        # Пропускаем все состояния регистрации
        if current_state and current_state.startswith(self._user_data_state_prefix):
            return await handler(event, data)

        # Пропускаем разрешенные команды и callback-и регистрации
        if (isinstance(event, Message) and event.text in self._allowed_commands) or (
            isinstance(event, CallbackQuery) and event.data in self._register_callbacks
        ):
            return await handler(event, data)

        # Если ничего не подошло - предлагаем зарегистрироваться
        await event.answer(
            "Вы не зарегистрированы.\n" "Для регистрации нажмите на кнопку 📝:",
            reply_markup=get_registration_keyboard(),
        )
