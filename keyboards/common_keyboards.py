from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_confirmation_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data="confirm_yes"
                ),
                InlineKeyboardButton(
                    text="✏️ Редактировать", callback_data="confirm_no"
                ),
            ]
        ]
    )
