"""
Кастомные исключения приложения.

Иерархия:
- AppError (базовый класс)
  ├── RecordNotFound     — запись не найдена
  ├── RecordAlreadyExists — запись уже существует  
  ├── CollectorUniquenessError — нарушение единственности коллектора
  └── StateDataError     — ошибка данных в FSM state
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppError(Exception):
    """Базовое исключение приложения."""
    
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | {self.details}"
        return self.message


@dataclass
class RecordNotFound(AppError):
    """Запись не найдена в БД."""
    
    entity: str = ""          # "User", "Wish", "Collector" и т.д.
    entity_id: int | None = None
    
    def __post_init__(self):
        if not self.message:
            if self.entity_id is not None:
                self.message = f"{self.entity} с ID {self.entity_id} не найден"
            else:
                self.message = f"{self.entity} не найден"
        super().__post_init__()


@dataclass
class RecordAlreadyExists(AppError):
    """Запись уже существует в БД."""
    
    entity: str = ""
    entity_id: int | None = None
    
    def __post_init__(self):
        if not self.message:
            self.message = f"{self.entity} уже существует"
            if self.entity_id is not None:
                self.message += f" (ID: {self.entity_id})"
        super().__post_init__()


@dataclass
class CollectorUniquenessError(AppError):
    """Нарушение ограничения единственности активного коллектора."""
    
    active_count: int = 0
    
    def __post_init__(self):
        if not self.message:
            self.message = (
                f"Найдено {self.active_count} активных коллекторов, "
                "должен быть только один"
            )
        super().__post_init__()


@dataclass
class StateDataError(AppError):
    """Ошибка данных в FSM state."""
    
    key: str = ""
    
    def __post_init__(self):
        if not self.message:
            self.message = f"В StateData не найден ключ: {self.key}"
        super().__post_init__()
