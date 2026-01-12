# 📚 Полный и дотошный гайд по Pydantic

## Содержание

1. [Что такое Pydantic](#что-такое-pydantic)
2. [Установка](#установка)
3. [Как это работает под капотом](#как-это-работает-под-капотом)
4. [Основы: BaseModel](#основы-basemodel)
5. [Типы данных и валидация](#типы-данных-и-валидация)
6. [Field - настройка полей](#field---настройка-полей)
7. [Валидаторы](#валидаторы)
8. [Модели и наследование](#модели-и-наследование)
9. [Конфигурация моделей](#конфигурация-моделей)
10. [Сериализация и десериализация](#сериализация-и-десериализация)
11. [Работа с JSON](#работа-с-json)
12. [Generics и TypeVar](#generics-и-typevar)
13. [Computed fields](#computed-fields)
14. [Настройки приложения (Settings)](#настройки-приложения-settings)
15. [Практические примеры](#практические-примеры)
16. [Частые ошибки и их решения](#частые-ошибки-и-их-решения)

---

## Что такое Pydantic

**Pydantic** — это библиотека для валидации данных и управления настройками с использованием аннотаций типов Python. 

### Ключевые особенности:
- ✅ **Валидация данных** — автоматическая проверка типов и значений
- ✅ **Сериализация** — конвертация в dict/JSON и обратно
- ✅ **Автодополнение в IDE** — благодаря типам
- ✅ **Высокая производительность** — ядро написано на Rust (pydantic-core)
- ✅ **Интеграция** — FastAPI, SQLAlchemy, Django и другие

### Pydantic v1 vs v2

```python
# Pydantic v1 (устаревшее)
from pydantic import validator

# Pydantic v2 (актуальное)
from pydantic import field_validator
```

> ⚠️ Этот гайд написан для **Pydantic v2** (версия 2.0+)

---

## Установка

```bash
# Базовая установка
pip install pydantic

# С поддержкой email валидации
pip install pydantic[email]

# Для работы с настройками из .env файлов
pip install pydantic-settings

# Проверка версии
python -c "import pydantic; print(pydantic.__version__)"
```

---

## Как это работает под капотом

### Архитектура Pydantic v2

```
┌─────────────────────────────────────────────────────┐
│                   Ваш Python код                     │
│              (class User(BaseModel): ...)           │
├─────────────────────────────────────────────────────┤
│                   Pydantic Python                    │
│          (декораторы, валидаторы, Field)            │
├─────────────────────────────────────────────────────┤
│                   pydantic-core                      │
│         (Rust библиотека для валидации)             │
└─────────────────────────────────────────────────────┘
```

### Этапы создания модели

1. **Метакласс ModelMetaclass** перехватывает создание класса
2. **Анализ аннотаций** — собираются все поля с типами
3. **Создание JSON Schema** — генерируется схема валидации
4. **Компиляция валидатора** — pydantic-core компилирует быстрый валидатор

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

# При создании класса автоматически:
# 1. Создаётся __pydantic_fields__ — информация о полях
# 2. Создаётся __pydantic_validator__ — скомпилированный валидатор
# 3. Создаётся model_fields — словарь с FieldInfo
# 4. Генерируется JSON schema
```

### Что происходит при создании экземпляра

```python
user = User(name="Alex", age=25)

# Последовательность:
# 1. __init__ получает аргументы
# 2. Вызывается __pydantic_validator__.validate_python(data)
# 3. Каждое поле проходит через цепочку валидаторов
# 4. Данные преобразуются к нужным типам
# 5. Вызываются кастомные валидаторы (если есть)
# 6. Результат сохраняется в __pydantic_fields_set__
```

### Внутренние атрибуты модели

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int = 0

user = User(name="Alex")

# Какие поля были явно переданы при создании
print(user.model_fields_set)  # {'name'}

# Информация о всех полях модели
print(User.model_fields)
# {
#   'name': FieldInfo(annotation=str, required=True),
#   'age': FieldInfo(annotation=int, required=False, default=0)
# }

# JSON Schema модели
print(User.model_json_schema())
# {
#   'properties': {
#     'name': {'title': 'Name', 'type': 'string'},
#     'age': {'default': 0, 'title': 'Age', 'type': 'integer'}
#   },
#   'required': ['name'],
#   'title': 'User',
#   'type': 'object'
# }
```

---

## Основы: BaseModel

### Создание простой модели

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool = True  # значение по умолчанию

# Создание экземпляра
user = User(id=1, name="Alex", email="alex@example.com")

print(user.id)        # 1
print(user.name)      # Alex
print(user.is_active) # True (по умолчанию)
```

### Автоматическое приведение типов

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    balance: float

# Pydantic автоматически конвертирует типы
user = User(id="123", name=456, balance="99.99")

print(user.id)      # 123 (int, был str)
print(user.name)    # "456" (str, был int)
print(user.balance) # 99.99 (float, был str)
print(type(user.id))  # <class 'int'>
```

### Обязательные и опциональные поля

```python
from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    # Обязательное поле
    name: str
    
    # Опциональное с default=None
    email: Optional[str] = None
    
    # Альтернативный синтаксис (Python 3.10+)
    phone: str | None = None
    
    # Опциональное с другим default
    role: str = "user"

# Можно создать только с обязательными полями
user = User(name="Alex")
print(user.email)  # None
print(user.role)   # "user"
```

### Вложенные модели

```python
from pydantic import BaseModel
from typing import List, Optional

class Address(BaseModel):
    city: str
    street: str
    house: int

class Company(BaseModel):
    name: str
    address: Address

class User(BaseModel):
    name: str
    company: Optional[Company] = None
    addresses: List[Address] = []

# Создание с вложенными данными
user = User(
    name="Alex",
    company={
        "name": "Tech Corp",
        "address": {
            "city": "Moscow",
            "street": "Lenina",
            "house": 1
        }
    },
    addresses=[
        {"city": "SPb", "street": "Nevsky", "house": 10}
    ]
)

print(user.company.name)  # Tech Corp
print(user.company.address.city)  # Moscow
print(type(user.company))  # <class 'Company'>
```

---

## Типы данных и валидация

### Стандартные типы Python

```python
from pydantic import BaseModel
from typing import List, Dict, Set, Tuple, Optional, Union, Any
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from uuid import UUID
from pathlib import Path
from enum import Enum

class DataTypes(BaseModel):
    # Базовые типы
    string: str
    integer: int
    floating: float
    boolean: bool
    
    # Коллекции
    items: List[int]
    mapping: Dict[str, int]
    unique: Set[str]
    fixed: Tuple[int, str, float]
    
    # Даты и время
    created_at: datetime
    birth_date: date
    wake_time: time
    duration: timedelta
    
    # Другие типы
    price: Decimal
    uuid: UUID
    file_path: Path
    
    # Специальные
    anything: Any
    optional_int: Optional[int] = None
    int_or_str: Union[int, str]

# Пример использования
data = DataTypes(
    string="hello",
    integer=42,
    floating=3.14,
    boolean=True,
    items=[1, 2, 3],
    mapping={"a": 1, "b": 2},
    unique={"x", "y"},
    fixed=(1, "two", 3.0),
    created_at="2024-01-15T10:30:00",  # Автопарсинг из строки!
    birth_date="1990-05-20",
    wake_time="07:30:00",
    duration="PT1H30M",  # ISO 8601 duration
    price="99.99",
    uuid="550e8400-e29b-41d4-a716-446655440000",
    file_path="/home/user/file.txt",
    anything={"любые": "данные"},
    int_or_str="hello"
)
```

### Специальные типы Pydantic

```python
from pydantic import (
    BaseModel,
    EmailStr,
    HttpUrl,
    AnyUrl,
    SecretStr,
    FilePath,
    DirectoryPath,
    PositiveInt,
    NegativeInt,
    NonNegativeInt,
    NonPositiveInt,
    PositiveFloat,
    StrictInt,
    StrictStr,
    StrictBool,
    conint,
    confloat,
    constr,
    conlist,
)

class ConstrainedTypes(BaseModel):
    # Email (требует pip install pydantic[email])
    email: EmailStr
    
    # URL
    website: HttpUrl
    any_url: AnyUrl
    
    # Секретные данные (не показываются в repr)
    password: SecretStr
    
    # Числа с ограничениями
    positive: PositiveInt      # > 0
    negative: NegativeInt      # < 0
    non_negative: NonNegativeInt  # >= 0
    
    # Строгие типы (без приведения)
    strict_int: StrictInt      # только int, не "123"
    strict_str: StrictStr      # только str, не 123
    strict_bool: StrictBool    # только bool, не 0/1

# Пример
data = ConstrainedTypes(
    email="test@example.com",
    website="https://example.com",
    any_url="ftp://files.example.com",
    password="secret123",
    positive=5,
    negative=-3,
    non_negative=0,
    strict_int=42,
    strict_str="hello",
    strict_bool=True
)

# SecretStr скрывает значение
print(data.password)  # **********
print(data.password.get_secret_value())  # secret123
```

### Constrained Types (ограниченные типы)

```python
from pydantic import BaseModel, conint, confloat, constr, conlist, conset
from typing import Annotated

class ConstrainedModel(BaseModel):
    # Целое число с ограничениями
    age: conint(ge=0, le=150)  # 0 <= age <= 150
    
    # Float с ограничениями
    rating: confloat(ge=0.0, le=5.0, multiple_of=0.5)
    
    # Строка с ограничениями
    username: constr(min_length=3, max_length=20, pattern=r'^[a-z]+$')
    
    # Список с ограничениями
    tags: conlist(str, min_length=1, max_length=5)
    
    # Множество с ограничениями
    categories: conset(str, min_length=1)

# Параметры conint/confloat:
# - gt: greater than (>)
# - ge: greater or equal (>=)
# - lt: less than (<)
# - le: less or equal (<=)
# - multiple_of: должно делиться на
# - strict: строгая типизация

# Параметры constr:
# - min_length: минимальная длина
# - max_length: максимальная длина
# - pattern: регулярное выражение
# - strip_whitespace: удалить пробелы
# - to_lower: привести к нижнему регистру
# - to_upper: привести к верхнему регистру
```

### Annotated синтаксис (рекомендуемый)

```python
from pydantic import BaseModel, Field
from typing import Annotated

class User(BaseModel):
    # Современный способ с Annotated
    age: Annotated[int, Field(ge=0, le=150, description="Возраст пользователя")]
    name: Annotated[str, Field(min_length=2, max_length=50)]
    
    # Эквивалентно старому способу:
    # age: int = Field(ge=0, le=150, description="Возраст пользователя")
```

### Enum типы

```python
from pydantic import BaseModel
from enum import Enum, IntEnum

class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"

class Priority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

class Task(BaseModel):
    title: str
    status: Status
    priority: Priority

task = Task(
    title="Fix bug",
    status="active",  # Можно передать строку
    priority=2        # Можно передать число
)

print(task.status)         # Status.ACTIVE
print(task.status.value)   # active
print(task.priority)       # Priority.MEDIUM
print(task.priority.value) # 2
```

### Literal типы

```python
from pydantic import BaseModel
from typing import Literal

class Config(BaseModel):
    mode: Literal["development", "production", "testing"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    
config = Config(mode="production", log_level="INFO")

# Ошибка: mode должен быть одним из трёх значений
# Config(mode="staging", log_level="INFO")  # ValidationError
```

---

## Field - настройка полей

### Основные параметры Field

```python
from pydantic import BaseModel, Field
from typing import Optional

class Product(BaseModel):
    # default - значение по умолчанию
    name: str = Field(default="Unknown")
    
    # default_factory - функция для создания default
    tags: list = Field(default_factory=list)
    
    # alias - альтернативное имя для входных данных
    product_id: int = Field(alias="id")
    
    # title и description - для документации
    price: float = Field(
        title="Product Price",
        description="The price of the product in USD"
    )
    
    # примеры для документации
    sku: str = Field(examples=["SKU-001", "SKU-002"])
    
    # deprecated - пометить как устаревшее
    old_code: Optional[str] = Field(default=None, deprecated=True)

# Использование alias
product = Product(id=1, price=99.99, sku="SKU-001")
print(product.product_id)  # 1 (не id!)
```

### Валидация через Field

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    # Числовые ограничения
    age: int = Field(ge=0, le=150)           # 0 <= age <= 150
    score: float = Field(gt=0, lt=100)       # 0 < score < 100
    
    # Строковые ограничения
    username: str = Field(min_length=3, max_length=20)
    email: str = Field(pattern=r'^[\w.-]+@[\w.-]+\.\w+$')
    
    # Список ограничений
    roles: list = Field(min_length=1, max_length=5)
    
    # Множественность
    quantity: int = Field(multiple_of=5)  # должно делиться на 5
    
    # Строгий режим (без приведения типов)
    strict_age: int = Field(strict=True)

# Все параметры Field:
# - default: значение по умолчанию
# - default_factory: фабрика для default
# - alias: альтернативное имя
# - alias_priority: приоритет alias
# - validation_alias: alias только для валидации
# - serialization_alias: alias только для сериализации
# - title: заголовок для JSON Schema
# - description: описание для JSON Schema
# - examples: примеры значений
# - exclude: исключить из сериализации
# - deprecated: пометить как deprecated
# - json_schema_extra: дополнительные данные для JSON Schema
# - frozen: сделать поле неизменяемым
# - validate_default: валидировать значение по умолчанию
# - repr: включать в __repr__
# - init: включать в __init__
# - init_var: переменная только для инициализации
# - kw_only: только keyword аргумент
# - pattern: регулярное выражение (для str)
# - strict: строгий режим
# - gt, ge, lt, le: числовые ограничения
# - multiple_of: делимость
# - min_length, max_length: ограничения длины
```

### Alias и его варианты

```python
from pydantic import BaseModel, Field, ConfigDict

class User(BaseModel):
    # alias - используется и для входа, и для выхода
    user_id: int = Field(alias="id")
    
    # validation_alias - только для входных данных
    user_name: str = Field(validation_alias="userName")
    
    # serialization_alias - только для выходных данных
    user_email: str = Field(serialization_alias="email")

# Входные данные с alias
user = User(id=1, userName="Alex", user_email="alex@test.com")

print(user.user_id)     # 1
print(user.user_name)   # Alex
print(user.user_email)  # alex@test.com

# При сериализации
print(user.model_dump())
# {'user_id': 1, 'user_name': 'Alex', 'user_email': 'alex@test.com'}

print(user.model_dump(by_alias=True))
# {'id': 1, 'user_name': 'Alex', 'email': 'alex@test.com'}


# AliasPath и AliasChoices для сложных случаев
from pydantic import AliasPath, AliasChoices

class ComplexModel(BaseModel):
    # Извлечение из вложенной структуры
    name: str = Field(validation_alias=AliasPath("user", "profile", "name"))
    
    # Несколько возможных названий
    email: str = Field(validation_alias=AliasChoices("email", "e-mail", "mail"))

# Работает с вложенными данными
data = {"user": {"profile": {"name": "Alex"}}, "e-mail": "alex@test.com"}
model = ComplexModel(**data)
```

---

## Валидаторы

### field_validator - валидация отдельных полей

```python
from pydantic import BaseModel, field_validator, ValidationError

class User(BaseModel):
    name: str
    age: int
    email: str
    
    # Валидатор для одного поля
    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip().title()
    
    # Валидатор для нескольких полей
    @field_validator('name', 'email')
    @classmethod
    def no_spaces(cls, v: str) -> str:
        if ' ' in v and '@' not in v:  # пробелы в email допустимы
            raise ValueError('No spaces allowed')
        return v
    
    # Валидатор с доступом к info
    @field_validator('age')
    @classmethod
    def check_age(cls, v: int, info) -> int:
        # info.field_name - имя поля
        # info.data - уже провалидированные поля
        if v < 0:
            raise ValueError(f'{info.field_name} must be non-negative')
        return v

# Режимы валидатора
class Product(BaseModel):
    price: float
    
    # mode='before' - до приведения типов
    @field_validator('price', mode='before')
    @classmethod
    def convert_price(cls, v):
        if isinstance(v, str):
            v = v.replace(',', '.').replace('$', '')
        return float(v)
    
    # mode='after' - после приведения типов (по умолчанию)
    @field_validator('price', mode='after')
    @classmethod
    def round_price(cls, v: float) -> float:
        return round(v, 2)
    
    # mode='wrap' - полный контроль
    @field_validator('price', mode='wrap')
    @classmethod
    def wrap_price(cls, v, handler):
        # handler - функция для продолжения валидации
        try:
            return handler(v)
        except Exception:
            return 0.0

# Пример использования
product = Product(price="$19,99")
print(product.price)  # 19.99
```

### model_validator - валидация всей модели

```python
from pydantic import BaseModel, model_validator, ValidationError

class Order(BaseModel):
    items: list[str]
    total: float
    discount: float = 0
    
    # mode='before' - до создания модели
    @model_validator(mode='before')
    @classmethod
    def check_data(cls, data: dict) -> dict:
        # data - сырой словарь входных данных
        if isinstance(data, dict):
            if 'items' not in data:
                data['items'] = []
        return data
    
    # mode='after' - после создания модели
    @model_validator(mode='after')
    def check_total(self) -> 'Order':
        # self - уже созданный экземпляр модели
        if self.discount > self.total:
            raise ValueError('Discount cannot exceed total')
        return self


class DateRange(BaseModel):
    start_date: str
    end_date: str
    
    @model_validator(mode='after')
    def check_dates(self) -> 'DateRange':
        if self.start_date > self.end_date:
            raise ValueError('start_date must be before end_date')
        return self


# mode='wrap' - полный контроль
class FlexibleModel(BaseModel):
    value: int
    
    @model_validator(mode='wrap')
    @classmethod
    def wrap_model(cls, values, handler):
        # Можно модифицировать входные данные
        # или обработать ошибки
        try:
            return handler(values)
        except ValidationError:
            # Вернуть модель со значением по умолчанию
            return cls(value=0)
```

### Порядок выполнения валидаторов

```python
from pydantic import BaseModel, field_validator, model_validator

class Example(BaseModel):
    a: int
    b: int
    c: int
    
    @field_validator('a', mode='before')
    @classmethod
    def val_a_before(cls, v):
        print(f"1. field_validator 'a' mode='before': {v}")
        return v
    
    @field_validator('a', mode='after')
    @classmethod
    def val_a_after(cls, v):
        print(f"2. field_validator 'a' mode='after': {v}")
        return v
    
    @model_validator(mode='before')
    @classmethod
    def model_before(cls, data):
        print(f"0. model_validator mode='before': {data}")
        return data
    
    @model_validator(mode='after')
    def model_after(self):
        print(f"3. model_validator mode='after': {self}")
        return self

# Порядок:
# 0. model_validator mode='before'
# 1. field_validator mode='before' (для каждого поля)
# 2. field_validator mode='after' (для каждого поля)
# 3. model_validator mode='after'

ex = Example(a=1, b=2, c=3)
```

### Повторное использование валидаторов

```python
from pydantic import BaseModel, field_validator
from typing import Annotated

# Способ 1: Через функцию
def validate_positive(v: int) -> int:
    if v <= 0:
        raise ValueError('Must be positive')
    return v

class Product(BaseModel):
    price: int
    quantity: int
    
    validate_price = field_validator('price')(validate_positive)
    validate_quantity = field_validator('quantity')(validate_positive)


# Способ 2: Через Annotated
from pydantic import AfterValidator

PositiveInt = Annotated[int, AfterValidator(validate_positive)]

class Product2(BaseModel):
    price: PositiveInt
    quantity: PositiveInt


# Способ 3: BeforeValidator, AfterValidator, WrapValidator
from pydantic import BeforeValidator, AfterValidator, WrapValidator

def strip_string(v):
    if isinstance(v, str):
        return v.strip()
    return v

def uppercase(v: str) -> str:
    return v.upper()

CleanString = Annotated[
    str,
    BeforeValidator(strip_string),
    AfterValidator(uppercase)
]

class Message(BaseModel):
    text: CleanString

msg = Message(text="  hello world  ")
print(msg.text)  # "HELLO WORLD"
```

---

## Модели и наследование

### Простое наследование

```python
from pydantic import BaseModel
from datetime import datetime

class BaseEntity(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime | None = None

class User(BaseEntity):
    name: str
    email: str

class Product(BaseEntity):
    title: str
    price: float

# User имеет поля: id, created_at, updated_at, name, email
user = User(
    id=1,
    created_at="2024-01-01T00:00:00",
    name="Alex",
    email="alex@test.com"
)
```

### Переопределение полей

```python
from pydantic import BaseModel, Field

class BaseUser(BaseModel):
    name: str = Field(max_length=100)
    age: int = Field(ge=0)

class StrictUser(BaseUser):
    # Переопределяем с более строгими ограничениями
    name: str = Field(max_length=50, min_length=2)
    age: int = Field(ge=18, le=100)

# StrictUser использует новые ограничения
```

### Множественное наследование (Mixins)

```python
from pydantic import BaseModel
from datetime import datetime

class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime | None = None

class SoftDeleteMixin(BaseModel):
    deleted_at: datetime | None = None
    is_deleted: bool = False

class User(TimestampMixin, SoftDeleteMixin, BaseModel):
    name: str
    email: str

# User имеет все поля из всех mixins
```

### Generic модели

```python
from pydantic import BaseModel
from typing import TypeVar, Generic, List

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    per_page: int
    
    @property
    def pages(self) -> int:
        return (self.total + self.per_page - 1) // self.per_page

class User(BaseModel):
    id: int
    name: str

class Product(BaseModel):
    id: int
    title: str

# Использование
users_response = PaginatedResponse[User](
    items=[User(id=1, name="Alex"), User(id=2, name="Bob")],
    total=100,
    page=1,
    per_page=10
)

products_response = PaginatedResponse[Product](
    items=[Product(id=1, title="Phone")],
    total=50,
    page=1,
    per_page=10
)
```

---

## Конфигурация моделей

### ConfigDict - настройка поведения модели

```python
from pydantic import BaseModel, ConfigDict

class User(BaseModel):
    model_config = ConfigDict(
        # Строгий режим - без приведения типов
        strict=False,
        
        # Запрет дополнительных полей
        extra='forbid',  # 'allow', 'ignore', 'forbid'
        
        # Заморозка модели (immutable)
        frozen=False,
        
        # Разрешить произвольные типы
        arbitrary_types_allowed=False,
        
        # Валидировать значения по умолчанию
        validate_default=False,
        
        # Использовать enum значения вместо объектов
        use_enum_values=False,
        
        # Заполнять по alias при инициализации
        populate_by_name=True,  # позволяет использовать и alias, и имя поля
        
        # Убрать пробелы в строках
        str_strip_whitespace=False,
        
        # Минимальная длина строк
        str_min_length=0,
        
        # Максимальная длина строк
        str_max_length=None,
        
        # Валидация при присваивании
        validate_assignment=False,
        
        # Revalidate при изменениях
        revalidate_instances='never',  # 'always', 'never', 'subclass-instances'
        
        # JSON Schema
        json_schema_extra={'example': {'id': 1, 'name': 'Alex'}},
    )
    
    id: int
    name: str
```

### Подробнее о важных настройках

```python
from pydantic import BaseModel, ConfigDict, Field

# extra='forbid' - запретить лишние поля
class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str

# Ошибка: extra fields not permitted
# StrictModel(name="Alex", age=25)


# frozen=True - неизменяемая модель
class ImmutableModel(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
## Computed fields
user = ImmutableModel(name="Alex")
# user.name = "Bob"  # Ошибка: Instance is frozen


# validate_assignment=True - валидация при присваивании
class ValidatedModel(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    age: int = Field(ge=0)

user = ValidatedModel(age=25)
# user.age = -5  # Ошибка: age must be >= 0


# populate_by_name=True - разрешить использовать оба имени
class AliasModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user_id: int = Field(alias="id")

# Оба варианта работают:
m1 = AliasModel(id=1)
m2 = AliasModel(user_id=1)
```

### Наследование конфигурации

```python
from pydantic import BaseModel, ConfigDict

class BaseConfig(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        str_strip_whitespace=True
    )

class User(BaseConfig):
    # Конфигурация наследуется
    # Можно расширить:
    model_config = ConfigDict(
        **BaseConfig.model_config,
        validate_assignment=True
    )
    
    name: str
    age: int
```

---

## Сериализация и десериализация

### model_dump() - конвертация в словарь

```python
from pydantic import BaseModel, Field
from datetime import datetime

class User(BaseModel):
    id: int
    name: str
    email: str
    password: str = Field(exclude=True)  # исключить из dump
    created_at: datetime

user = User(
    id=1,
    name="Alex",
    email="alex@test.com",
    password="secret",
    created_at="2024-01-15T10:00:00"
)

# Базовая конвертация
print(user.model_dump())
# {'id': 1, 'name': 'Alex', 'email': 'alex@test.com', 'created_at': datetime(...)}
# password исключён из-за exclude=True

# С параметрами
print(user.model_dump(
    # Включить только указанные поля
    include={'id', 'name'},
    
    # Исключить поля
    # exclude={'password'},
    
    # Исключить поля со значением None
    exclude_none=True,
    
    # Исключить поля с default значениями
    exclude_defaults=False,
    
    # Исключить поля, которые не были явно установлены
    exclude_unset=False,
    
    # Использовать alias
    by_alias=False,
    
    # Округлить float до N знаков
    # round_trip=True,
))

# Вложенные include/exclude
class Address(BaseModel):
    city: str
    street: str
    zip: str

class Company(BaseModel):
    name: str
    address: Address

company = Company(
    name="Tech Corp",
    address=Address(city="Moscow", street="Main", zip="123456")
)

# Исключить вложенное поле
print(company.model_dump(exclude={'address': {'zip'}}))
# {'name': 'Tech Corp', 'address': {'city': 'Moscow', 'street': 'Main'}}

# Включить только определённые вложенные поля
print(company.model_dump(include={'address': {'city'}}))
# {'address': {'city': 'Moscow'}}
```

### model_dump_json() - конвертация в JSON

```python
from pydantic import BaseModel
from datetime import datetime

class Event(BaseModel):
    name: str
    date: datetime
    data: dict

event = Event(
    name="Meeting",
    date="2024-01-15T10:00:00",
    data={"room": "A1"}
)

# JSON строка
json_str = event.model_dump_json()
print(json_str)
# '{"name":"Meeting","date":"2024-01-15T10:00:00","data":{"room":"A1"}}'

# С форматированием
json_pretty = event.model_dump_json(indent=2)
print(json_pretty)
# {
#   "name": "Meeting",
#   "date": "2024-01-15T10:00:00",
#   "data": {
#     "room": "A1"
#   }
# }

# Все параметры от model_dump тоже работают
json_str = event.model_dump_json(
    exclude={'data'},
    by_alias=True
)
```

### model_validate() - создание из словаря

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str

# Из словаря
data = {'id': 1, 'name': 'Alex'}
user = User.model_validate(data)

# Эквивалентно
user = User(**data)

# С дополнительными параметрами
user = User.model_validate(
    data,
    strict=True,  # строгий режим
    context={'request_id': '123'}  # контекст для валидаторов
)
```

### model_validate_json() - создание из JSON

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str

json_str = '{"id": 1, "name": "Alex"}'
user = User.model_validate_json(json_str)

# С параметрами
user = User.model_validate_json(
    json_str,
    strict=True
)
```

### Кастомная сериализация

```python
from pydantic import BaseModel, field_serializer, model_serializer
from datetime import datetime

class Event(BaseModel):
    name: str
    date: datetime
    
    # Кастомная сериализация для поля
    @field_serializer('date')
    def serialize_date(self, value: datetime) -> str:
        return value.strftime('%d.%m.%Y %H:%M')

event = Event(name="Meeting", date="2024-01-15T10:30:00")
print(event.model_dump())
# {'name': 'Meeting', 'date': '15.01.2024 10:30'}


# model_serializer - для всей модели
class CustomModel(BaseModel):
    x: int
    y: int
    
    @model_serializer
    def serialize_model(self) -> dict:
        return {'sum': self.x + self.y, 'original': {'x': self.x, 'y': self.y}}

m = CustomModel(x=1, y=2)
print(m.model_dump())
# {'sum': 3, 'original': {'x': 1, 'y': 2}}


# Разные режимы сериализации
class FlexibleModel(BaseModel):
    value: int
    
    @field_serializer('value', when_used='json')
    def serialize_for_json(self, value: int) -> str:
        return f"value_{value}"
    
    @field_serializer('value', when_used='unless-none')
    def serialize_always(self, value: int) -> int:
        return value * 10

# when_used варианты:
# 'always' - всегда
# 'unless-none' - если не None
# 'json' - только для JSON
# 'json-unless-none' - для JSON если не None
```

### PlainSerializer и WrapSerializer

```python
from pydantic import BaseModel
from pydantic.functional_serializers import PlainSerializer, WrapSerializer
from typing import Annotated
from datetime import datetime

# PlainSerializer - полная замена сериализации
DateString = Annotated[
    datetime,
    PlainSerializer(lambda x: x.strftime('%Y-%m-%d'), return_type=str)
]

class Event(BaseModel):
    date: DateString

event = Event(date="2024-01-15T10:00:00")
print(event.model_dump())  # {'date': '2024-01-15'}


# WrapSerializer - обёртка над стандартной сериализацией
def wrap_date(value: datetime, handler) -> str:
    # handler - стандартный сериализатор
    standard = handler(value)
    return f"DATE: {standard}"

WrappedDate = Annotated[datetime, WrapSerializer(wrap_date)]

class Event2(BaseModel):
    date: WrappedDate

event2 = Event2(date="2024-01-15T10:00:00")
print(event2.model_dump())  # {'date': 'DATE: 2024-01-15T10:00:00'}
```

---

## Работа с JSON

### JSON Schema

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class Address(BaseModel):
    """Адрес пользователя"""
    city: str = Field(description="Город")
    street: str = Field(description="Улица")

class User(BaseModel):
    """Модель пользователя"""
    id: int = Field(description="Уникальный идентификатор")
    name: str = Field(min_length=1, max_length=100, description="Имя пользователя")
    email: Optional[str] = Field(default=None, description="Email")
    addresses: List[Address] = Field(default_factory=list, description="Адреса")

# Получить JSON Schema
schema = User.model_json_schema()
print(schema)
# {
#     'description': 'Модель пользователя',
#     'properties': {
#         'id': {
#             'description': 'Уникальный идентификатор',
#             'title': 'Id',
#             'type': 'integer'
#         },
#         'name': {
#             'description': 'Имя пользователя',
#             'maxLength': 100,
#             'minLength': 1,
#             'title': 'Name',
#             'type': 'string'
#         },
#         'email': {
#             'anyOf': [{'type': 'string'}, {'type': 'null'}],
#             'default': None,
#             'description': 'Email',
#             'title': 'Email'
#         },
#         'addresses': {
#             '$ref': '#/$defs/Address',
#             ...
#         }
#     },
#     'required': ['id', 'name'],
#     'title': 'User',
#     'type': 'object',
#     '$defs': {
#         'Address': {...}
#     }
# }

# Красивый вывод
import json
print(json.dumps(schema, indent=2, ensure_ascii=False))
```

### Кастомизация JSON Schema

```python
from pydantic import BaseModel, Field, ConfigDict

class Product(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {'id': 1, 'name': 'Phone', 'price': 999.99}
            ]
        }
    )
    
    id: int
    name: str = Field(
        json_schema_extra={'examples': ['Phone', 'Laptop']}
    )
    price: float


# Динамическая модификация схемы
class DynamicSchema(BaseModel):
    value: int
    
    @classmethod
    def model_json_schema(cls, **kwargs):
        schema = super().model_json_schema(**kwargs)
        schema['x-custom-field'] = 'custom value'
        return schema
```

---

## Generics и TypeVar

### Базовое использование Generic

```python
from pydantic import BaseModel
from typing import TypeVar, Generic, List, Optional

T = TypeVar('T')

# Generic Response
class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None

class User(BaseModel):
    id: int
    name: str

class Product(BaseModel):
    id: int
    title: str
    price: float

# Использование с конкретными типами
user_response = ApiResponse[User](
    success=True,
    data=User(id=1, name="Alex")
)

product_response = ApiResponse[Product](
    success=True,
    data=Product(id=1, title="Phone", price=999)
)

# Тип data корректно определяется
print(user_response.data.name)  # Alex
print(product_response.data.price)  # 999
```

### Несколько TypeVar

```python
from pydantic import BaseModel
from typing import TypeVar, Generic, Dict

K = TypeVar('K')
V = TypeVar('V')

class KeyValueStore(BaseModel, Generic[K, V]):
    items: Dict[K, V]
    default_value: V

# Использование
store = KeyValueStore[str, int](
    items={"a": 1, "b": 2},
    default_value=0
)
```

### Generic с ограничениями

```python
from pydantic import BaseModel
from typing import TypeVar, Generic, List

# TypeVar с ограничением на базовый класс
class BaseEntity(BaseModel):
    id: int

T = TypeVar('T', bound=BaseEntity)

class Repository(BaseModel, Generic[T]):
    items: List[T]
    
    def find_by_id(self, id: int) -> T | None:
        return next((item for item in self.items if item.id == id), None)

class User(BaseEntity):
    name: str

class Product(BaseEntity):
    title: str

user_repo = Repository[User](items=[
    User(id=1, name="Alex"),
    User(id=2, name="Bob")
])

found = user_repo.find_by_id(1)
print(found.name if found else "Not found")  # Alex
```

---

## Computed fields

### computed_field - вычисляемые поля

```python
from pydantic import BaseModel, computed_field

class Rectangle(BaseModel):
    width: float
    height: float
    
    @computed_field
    @property
    def area(self) -> float:
        return self.width * self.height
    
    @computed_field
    @property
    def perimeter(self) -> float:
        return 2 * (self.width + self.height)

rect = Rectangle(width=10, height=5)

print(rect.area)       # 50.0
print(rect.perimeter)  # 30.0

# Включается в model_dump()
print(rect.model_dump())
# {'width': 10.0, 'height': 5.0, 'area': 50.0, 'perimeter': 30.0}

# Включается в JSON Schema
print(rect.model_json_schema())
```

### Кэширование computed_field

```python
from pydantic import BaseModel, computed_field
from functools import cached_property

class ExpensiveComputation(BaseModel):
    model_config = {'frozen': True}  # требуется для cached_property
    
    data: list[int]
    
    @computed_field
    @cached_property
    def processed(self) -> int:
        print("Computing...")  # выводится только один раз
        return sum(x ** 2 for x in self.data)

model = ExpensiveComputation(data=[1, 2, 3, 4, 5])
print(model.processed)  # Computing... 55
print(model.processed)  # 55 (без "Computing...")
```

### computed_field с repr и alias

```python
from pydantic import BaseModel, computed_field, Field

class User(BaseModel):
    first_name: str
    last_name: str
    
    @computed_field(repr=False)  # не включать в __repr__
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @computed_field(alias="displayName")  # alias для сериализации
    @property
    def display_name(self) -> str:
        return self.full_name.upper()

user = User(first_name="Alex", last_name="Smith")
print(user)  # first_name='Alex' last_name='Smith' display_name='ALEX SMITH'
print(user.model_dump(by_alias=True))
# {'first_name': 'Alex', 'last_name': 'Smith', 'full_name': 'Alex Smith', 'displayName': 'ALEX SMITH'}
```

---

## Настройки приложения (Settings)

### Установка pydantic-settings

```bash
pip install pydantic-settings
```

### Базовое использование

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',           # файл с переменными
        env_file_encoding='utf-8',
        env_prefix='APP_',         # префикс переменных окружения
        case_sensitive=False,      # регистронезависимые имена
        extra='ignore',            # игнорировать лишние переменные
    )
    
    # Эти поля будут загружены из:
    # 1. Переменных окружения (приоритет)
    # 2. .env файла
    # 3. Значений по умолчанию
    
    debug: bool = False
    database_url: str
    secret_key: str = Field(min_length=32)
    api_timeout: int = 30

# .env файл:
# APP_DEBUG=true
# APP_DATABASE_URL=postgresql://user:pass@localhost/db
# APP_SECRET_KEY=super_secret_key_with_32_characters!!

settings = Settings()
print(settings.debug)  # True
print(settings.database_url)  # postgresql://user:pass@localhost/db
```

### Вложенные настройки

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel

class DatabaseSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    name: str = "app"
    user: str = "postgres"
    password: str = ""
    
    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

class RedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_nested_delimiter='__',  # разделитель для вложенных настроек
    )
    
    debug: bool = False
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()

# .env файл:
# DEBUG=true
# DATABASE__HOST=db.example.com
# DATABASE__PORT=5432
# DATABASE__PASSWORD=secret
# REDIS__HOST=redis.example.com

settings = Settings()
print(settings.database.host)  # db.example.com
print(settings.database.url)   # postgresql://postgres:secret@db.example.com:5432/app
```

### Источники настроек

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Несколько .env файлов (порядок важен)
        env_file=('.env', '.env.local', '.env.production'),
        
        # Секреты Docker
        secrets_dir='/run/secrets',
    )
    
    # Из файла секретов: /run/secrets/database_password
    database_password: str = Field(validation_alias='database_password')
    
    api_key: str

# Приоритет источников (от высшего к низшему):
# 1. Аргументы инициализации Settings(api_key="...")
# 2. Переменные окружения
# 3. .env файлы (в порядке указания)
# 4. Секреты из secrets_dir
# 5. Значения по умолчанию
```

### Валидация настроек

```python
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
import os

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    debug: bool = False
    
    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith(('postgresql://', 'mysql://', 'sqlite://')):
            raise ValueError('Invalid database URL scheme')
        return v
    
    @model_validator(mode='after')
    def validate_production(self) -> 'Settings':
        if not self.debug and 'localhost' in self.database_url:
            raise ValueError('Cannot use localhost database in production')
        return self
```

### Singleton паттерн для настроек

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    debug: bool = False
    database_url: str = "sqlite:///./app.db"

@lru_cache()
def get_settings() -> Settings:
    """Кэшированные настройки (singleton)"""
    return Settings()

# Использование
settings = get_settings()
print(settings.debug)

# В FastAPI
from fastapi import Depends

def get_db(settings: Settings = Depends(get_settings)):
    ...
```

---

## Практические примеры

### Пример 1: API модели для FastAPI

```python
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

# Базовая модель
class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    role: UserRole = UserRole.USER

# Модель для создания (без id)
class UserCreate(UserBase):
    password: str = Field(min_length=8)
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v

# Модель для обновления (все поля опциональны)
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    role: Optional[UserRole] = None

# Модель для ответа (без пароля, с id и датами)
class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {'from_attributes': True}  # для работы с ORM

# Использование в FastAPI
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate):
    # user уже провалидирован Pydantic
    ...
    
@app.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user: UserUpdate):
    # Получаем только переданные поля
    update_data = user.model_dump(exclude_unset=True)
    ...
```

### Пример 2: Сложная валидация форм

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import date

class RegistrationForm(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: str
    password: str = Field(min_length=8)
    password_confirm: str
    birth_date: date
    terms_accepted: bool
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v.lower()
    
    @field_validator('email')
    @classmethod
    def email_valid(cls, v: str) -> str:
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError('Invalid email format')
        return v.lower()
    
    @field_validator('birth_date')
    @classmethod
    def check_age(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError('Must be at least 18 years old')
        return v
    
    @field_validator('terms_accepted')
    @classmethod
    def must_accept_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError('You must accept the terms')
        return v
    
    @model_validator(mode='after')
    def passwords_match(self) -> 'RegistrationForm':
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self

# Обработка ошибок валидации
from pydantic import ValidationError

try:
    form = RegistrationForm(
        username="alex123",
        email="alex@example.com",
        password="SecurePass1",
        password_confirm="SecurePass2",  # не совпадает!
        birth_date="2010-01-01",  # слишком молодой!
        terms_accepted=False  # не принял!
    )
except ValidationError as e:
    print(e.errors())
    # [
    #   {'type': 'value_error', 'loc': ('birth_date',), 'msg': 'Must be at least 18...'},
    #   {'type': 'value_error', 'loc': ('terms_accepted',), 'msg': 'You must accept...'},
    #   {'type': 'value_error', 'loc': (), 'msg': 'Passwords do not match'}
    # ]
    
    # Красивый вывод ошибок
    for error in e.errors():
        field = '.'.join(str(x) for x in error['loc']) or 'form'
        print(f"{field}: {error['msg']}")
```

### Пример 3: Работа с внешними API

```python
from pydantic import BaseModel, Field, field_validator, AliasPath
from typing import List, Optional
from datetime import datetime

# Модель для парсинга ответа внешнего API
class GitHubUser(BaseModel):
    id: int
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: str = Field(validation_alias='avatar_url')
    followers: int = 0
    following: int = 0
    created_at: datetime
    
    # API возвращает html_url, но мы хотим назвать его profile_url
    profile_url: str = Field(validation_alias='html_url')

class GitHubRepo(BaseModel):
    id: int
    name: str
    full_name: str
    description: Optional[str] = None
    private: bool = False
    stars: int = Field(validation_alias='stargazers_count')
    forks: int = Field(validation_alias='forks_count')
    language: Optional[str] = None
    
    # Вложенный путь
    owner_login: str = Field(validation_alias=AliasPath('owner', 'login'))

# Использование с requests
import httpx

async def get_github_user(username: str) -> GitHubUser:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.github.com/users/{username}")
        response.raise_for_status()
        return GitHubUser.model_validate(response.json())

async def get_user_repos(username: str) -> List[GitHubRepo]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.github.com/users/{username}/repos")
        response.raise_for_status()
        return [GitHubRepo.model_validate(repo) for repo in response.json()]
```

### Пример 4: Конфигурация с валидацией

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, SecretStr
from typing import List
import re

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_prefix='APP_',
    )
    
    # Основные настройки
    name: str = "MyApp"
    version: str = "1.0.0"
    debug: bool = False
    
    # Безопасность
    secret_key: SecretStr = Field(min_length=32)
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    cors_origins: List[str] = []
    
    # База данных
    database_url: str
    database_pool_size: int = Field(default=5, ge=1, le=20)
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Email
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    
    @field_validator('database_url')
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        valid_prefixes = ('postgresql://', 'mysql://', 'sqlite:///')
        if not v.startswith(valid_prefixes):
            raise ValueError(f'database_url must start with one of: {valid_prefixes}')
        return v
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    @field_validator('allowed_hosts', mode='before')
    @classmethod
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(',') if host.strip()]
        return v

# Использование
settings = AppSettings()

# Доступ к секретам
print(settings.secret_key.get_secret_value())
```

### Пример 5: Data Transfer Objects (DTO)

```python
from pydantic import BaseModel, Field, computed_field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

# Entity из базы данных (SQLAlchemy model)
class OrderEntity:
    def __init__(self):
        self.id = 1
        self.user_id = 42
        self.status = "completed"
        self.created_at = datetime.now()
        self.items = []  # List[OrderItemEntity]
        self.total_amount = Decimal("199.99")

# DTO для передачи между слоями
class OrderItemDTO(BaseModel):
    model_config = {'from_attributes': True}
    
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    
    @computed_field
    @property
    def total_price(self) -> Decimal:
        return self.quantity * self.unit_price

class OrderDTO(BaseModel):
    model_config = {'from_attributes': True}
    
    id: int
    user_id: int
    status: str
    created_at: datetime
    items: List[OrderItemDTO] = []
    total_amount: Decimal
    
    @computed_field
    @property
    def items_count(self) -> int:
        return sum(item.quantity for item in self.items)

# Конвертация из Entity в DTO
def entity_to_dto(entity: OrderEntity) -> OrderDTO:
    return OrderDTO.model_validate(entity)

# Response модель для API (без лишних полей)
class OrderResponse(BaseModel):
    id: int
    status: str
    items_count: int
    total_amount: str  # строка для JSON
    created_at: str
    
    @classmethod
    def from_dto(cls, dto: OrderDTO) -> 'OrderResponse':
        return cls(
            id=dto.id,
            status=dto.status,
            items_count=dto.items_count,
            total_amount=f"${dto.total_amount:.2f}",
            created_at=dto.created_at.strftime("%Y-%m-%d %H:%M")
        )
```

---

## Частые ошибки и их решения

### Ошибка 1: Mutable default values

```python
# ❌ НЕПРАВИЛЬНО - изменяемое значение по умолчанию
class User(BaseModel):
    tags: list = []  # Все экземпляры будут делить один список!
    
# ✅ ПРАВИЛЬНО - используем default_factory
from pydantic import Field

class User(BaseModel):
    tags: list = Field(default_factory=list)
```

### Ошибка 2: Циклические импорты с forward references

```python
# ❌ Проблема: циклический импорт
# file: user.py
from .order import Order
class User(BaseModel):
    orders: List[Order]

# file: order.py
from .user import User  # Циклический импорт!
class Order(BaseModel):
    user: User

# ✅ Решение: forward references
from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .order import Order

class User(BaseModel):
    orders: List['Order'] = []  # Строка вместо класса
    
    model_config = {'defer_build': True}

# После определения всех моделей:
User.model_rebuild()
```

### Ошибка 3: Валидатор не вызывается

```python
# ❌ Забыли @classmethod
class User(BaseModel):
    name: str
    
    @field_validator('name')
    def validate_name(cls, v):  # Без @classmethod!
        return v.strip()

# ✅ ПРАВИЛЬНО
class User(BaseModel):
    name: str
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()
```

### Ошибка 4: Optional vs Union[..., None]

```python
from typing import Optional, Union

# Эти записи эквивалентны:
class User(BaseModel):
    email: Optional[str] = None
    email: Union[str, None] = None
    email: str | None = None  # Python 3.10+

# ❌ НЕПРАВИЛЬНО - Optional без default
class User(BaseModel):
    email: Optional[str]  # Всё ещё обязательное поле!

# ✅ ПРАВИЛЬНО
class User(BaseModel):
    email: Optional[str] = None  # Опциональное с default
```

### Ошибка 5: Изменение экземпляра без валидации

```python
from pydantic import BaseModel, Field, ConfigDict

class User(BaseModel):
    age: int = Field(ge=0)

user = User(age=25)

# ❌ Изменение без валидации (по умолчанию)
user.age = -5  # Присвоится без ошибки!

# ✅ Включить валидацию при присваивании
class User(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    age: int = Field(ge=0)

user = User(age=25)
user.age = -5  # ValidationError!
```

### Ошибка 6: Неправильный порядок валидаторов

```python
from pydantic import BaseModel, field_validator

class User(BaseModel):
    name: str
    email: str
    
    # ❌ Валидатор для 'email' пытается использовать 'name',
    # но порядок валидации не гарантирован
    @field_validator('email')
    @classmethod
    def check_email(cls, v, info):
        name = info.data.get('name')  # Может быть None!
        ...

# ✅ Используем model_validator для зависимых полей
class User(BaseModel):
    name: str
    email: str
    
    @model_validator(mode='after')
    def check_email_matches_name(self) -> 'User':
        # Здесь все поля уже провалидированы
        if self.name.lower() not in self.email.lower():
            raise ValueError('Email should contain name')
        return self
```

### Ошибка 7: Большие числа и точность

```python
from pydantic import BaseModel
from decimal import Decimal

# ❌ Float теряет точность
class Payment(BaseModel):
    amount: float

p = Payment(amount="0.1")
print(p.amount + p.amount + p.amount)  # 0.30000000000000004

# ✅ Используем Decimal для денег
class Payment(BaseModel):
    amount: Decimal

p = Payment(amount="0.1")
print(p.amount + p.amount + p.amount)  # 0.3
```

### Ошибка 8: Неэффективная сериализация

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    password: str

# ❌ Пароль попадает в JSON!
print(user.model_dump_json())

# ✅ Исключаем чувствительные поля
print(user.model_dump_json(exclude={'password'}))

# ✅ Или помечаем поле как exclude
from pydantic import Field

class User(BaseModel):
    id: int
    name: str
    password: str = Field(exclude=True)
```

---

## Полезные ссылки

- 📖 [Официальная документация Pydantic](https://docs.pydantic.dev/)
- 📖 [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- 📖 [Migration Guide v1 → v2](https://docs.pydantic.dev/latest/migration/)
- 📖 [FastAPI + Pydantic](https://fastapi.tiangolo.com/tutorial/body/)
- 🔧 [pydantic-extra-types](https://github.com/pydantic/pydantic-extra-types) - дополнительные типы

---

## Шпаргалка

```python
# Импорты
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    computed_field,
    ConfigDict,
    ValidationError,
    EmailStr,
    SecretStr,
    HttpUrl,
    PositiveInt,
    conint, constr, conlist,
    AliasPath, AliasChoices,
    BeforeValidator, AfterValidator,
)
from pydantic_settings import BaseSettings
from typing import Optional, List, Dict, Annotated

# Основы
class Model(BaseModel):
    field: str                          # обязательное
    optional: str | None = None         # опциональное
    with_default: str = "default"       # со значением
    constrained: int = Field(ge=0)      # с ограничениями

# Валидаторы
@field_validator('field')
@classmethod
def validate(cls, v): return v

@model_validator(mode='after')
def validate_model(self): return self

# Методы
model.model_dump()                # → dict
model.model_dump_json()           # → str (JSON)
Model.model_validate(dict)        # dict → Model
Model.model_validate_json(str)    # JSON str → Model
Model.model_json_schema()         # → JSON Schema
```

---

**Удачи с Pydantic! 🚀**


