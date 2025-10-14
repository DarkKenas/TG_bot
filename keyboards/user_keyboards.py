from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_edit_user_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать данные", callback_data="edit_user_data"
                )
            ]
        ]
    )
