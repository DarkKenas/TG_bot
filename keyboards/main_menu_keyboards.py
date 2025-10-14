from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from create_bot import default_service_user_id

BUTTON_MY_WISHES = "🎯 Мой WishList"
BUTTON_ADD_WISH = "➕ Добавить желание"
BUTTON_MY_DATA = "👤 Мои данные"
BUTTON_BIRTHDAYS = "📆 Дни Рождения"
BUTTON_SERVICE_CHAT = "⚙️ Чат поддержки"
BUTTON_CANCEL = "⭕ Остановить ввод"
BUTTON_ADMIN_PANEL = "🔐 Админ панель"
BUTTON_COLLECTOR_PANEL = "💰 Сбор панель"


async def get_main_menu_keyboard(
    is_admin: bool = False, is_collector: bool = False
) -> ReplyKeyboardMarkup:
    """Главное меню с кнопками под полем ввода"""
    keyboard = [
        [
            KeyboardButton(text=BUTTON_MY_WISHES),
            KeyboardButton(text=BUTTON_ADD_WISH),
        ],
        [
            KeyboardButton(text=BUTTON_MY_DATA),
            KeyboardButton(text=BUTTON_BIRTHDAYS),
        ],
        [
            KeyboardButton(text=BUTTON_SERVICE_CHAT),
            KeyboardButton(text=BUTTON_CANCEL),
        ],
    ]

    # Добавляем кнопку админ-панели для админов
    if is_admin is not None:
        keyboard.append([KeyboardButton(text=BUTTON_ADMIN_PANEL)])

    # Добавляем кнопку панели коллектора для коллекторов
    if is_collector is not None:
        keyboard.append([KeyboardButton(text=BUTTON_COLLECTOR_PANEL)])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
        input_field_placeholder="Выберите действие...",
    )


async def get_service_chat_keyboard():
    """Кнопка для связи с поддержкой"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Написать",
                    url=f"https://web.telegram.org/a/#{default_service_user_id}",
                )
            ]
        ]
    )
