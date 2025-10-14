from typing import Any


class UserIdExist(Exception):
    """Исключение для случая, когда пользователь с таким ID уже существует.

    Attributes:
        user_id: ID пользователя, который уже существует
        message: Сообщение об ошибке

    Example:
        >>> raise UserIdExist(123456789)
        UserIdExist: Пользователь с ID 123456789 уже существует в базе данных
    """

    def __init__(self, user_id: int) -> None:
        self.user_id: int = user_id
        self.message: str = f"Пользователь с ID {user_id} уже существует в базе данных"
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class RecordExist(Exception):
    """Исключение для случая, когда запись уже существует в базе данных.

    Attributes:
        table_name: Название таблицы, в которой найден дубликат
        details: Дополнительная информация об ошибке
        message: Сообщение об ошибке

    Example:
        >>> raise RecordExist("administrators", user_id=123456789)
        RecordExist: Запись уже существует в таблице administrators.
        Дополнительная информация: {'user_id': 123456789}
    """

    def __init__(self, table_name: str, **details: Any) -> None:
        self.table_name: str = table_name
        self.details: dict[str, Any] = details

        self.message: str = f"Запись уже существует в таблице {table_name}"

        if details:
            self.message += f"\nДополнительная информация: {details}"

        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class RecordNotFound(Exception):
    """Исключение для случая, когда запись не найдена в базе данных.

    Attributes:
        record_id: ID записи, которая не найдена
        table_name: Название таблицы, в которой искали запись
        details: Дополнительная информация об ошибке
        message: Сообщение об ошибке

    Example:
        >>> raise RecordNotFound(1, "users", user_name="John")
        RecordNotFound: Запись с ID 1 не найдена в таблице users.
        Дополнительная информация: {'user_name': 'John'}

        >>> raise RecordNotFound(None, "collectors", is_active=True)
        RecordNotFound: Запись не найдена в таблице collectors.
        Дополнительная информация: {'is_active': True}
    """

    def __init__(self, record_id: int | None, table_name: str, **details: Any) -> None:
        self.record_id: int | None = record_id
        self.table_name: str = table_name
        self.details: dict[str, Any] = details

        if record_id is not None:
            self.message: str = (
                f"Запись с ID {record_id} не найдена в таблице {table_name}"
            )
        else:
            self.message: str = f"Запись не найдена в таблице {table_name}"

        if details:
            self.message += f"\nДополнительная информация: {details}"

        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class CollectorUniquenessError(Exception):
    """Исключение для нарушения ограничения единственности активного коллектора.

    Attributes:
        active_count: Количество найденных активных коллекторов
        message: Сообщение об ошибке

    Example:
        >>> raise CollectorUniquenessError(3)
        CollectorUniquenessError: Нарушение единственности коллектора: найдено 3 активных коллекторов, должен быть только один
    """

    def __init__(self, active_count: int) -> None:
        self.active_count: int = active_count
        self.message: str = (
            f"Нарушение единственности коллектора: найдено {active_count} активных коллекторов, должен быть только один"
        )
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class StateDataError(Exception):
    def __init__(self, key: str):
        self.message = f"Ошибка: В StateData не найден ключ: {key}"
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message
