from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def get_userdata_edit_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Фамилию", callback_data="edit_last_name")],
            [InlineKeyboardButton(text="👤 Имя", callback_data="edit_first_name")],
            [InlineKeyboardButton(text="👤 Отчество", callback_data="edit_patronymic")],
            [
                InlineKeyboardButton(
                    text="📅 Дату рождения", callback_data="edit_birth_date"
                )
            ],
        ]
    )


def get_registration_keyboard():
    """Клавиатура для незарегистрированных пользователей"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Регистрация", callback_data="register")],
        ],
    )
