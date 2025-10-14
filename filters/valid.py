import re
from datetime import datetime as dt
from urllib.parse import urlparse

# Константы для валидации имени
NAME_PATTERN = r"^[А-Яа-яЁёA-Za-z]{2,50}$"
MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 50

# Константы для сообщений об ошибках URL
ERROR_NO_PROTOCOL = "❌ URL должен содержать http:// или https://. Попробуйте еще раз:"
ERROR_INVALID_URL = "❌ Неверный URL. Попробуйте еще раз:"


def validate_name(name: str) -> bool:
    """Проверка валидности имени.

    Проверяет, что имя:
    - Содержит только буквы русского и английского алфавита
    - Длина от 2 до 50 символов

    Args:
        name: Строка для проверки

    Returns:
        bool: True если имя валидное, False если нет
    """
    return bool(re.match(NAME_PATTERN, name))


def is_valid_url(url: str) -> tuple[bool, str]:
    """Проверка валидности URL.

    Проверяет, что URL:
    - Начинается с http:// или https://
    - Имеет валидную схему и домен
    - Домен содержит точку

    Args:
        url: Строка для проверки

    Returns:
        tuple[bool, str]: Кортеж (флаг валидности, сообщение об ошибке).
        Если URL валиден, возвращает (True, "").
    """
    try:
        # URL должен содержать протокол
        if not url.startswith(("http://", "https://")):
            return False, ERROR_NO_PROTOCOL

        result = urlparse(url)

        # Проверяем наличие схемы и домена
        if not all([result.scheme, result.netloc]):
            raise ValueError("Missing scheme or netloc")

        # Дополнительная проверка домена (содержит точку)
        if "." not in result.netloc:
            raise ValueError("Invalid domain")

        return True, ""
    except Exception:
        return False, ERROR_INVALID_URL
