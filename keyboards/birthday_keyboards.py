from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Константы для текстов кнопок
BUTTON_SEND_MONEY = "💰 Скинуться на подарок"
BUTTON_TRANSFERRED = "✅ Перевел"


def get_birthday_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с действиями для дня рождения.
    
    Содержит кнопки:
    - Скинуться на подарок
    
    Args:
        user_id: ID пользователя-именинника
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками действий
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BUTTON_SEND_MONEY,
                    callback_data=f"birthday_gift:{user_id}",
                )
            ],
        ]
    )


def get_gift_collection_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для сбора средств на подарок.
    
    Содержит кнопки:
    - Подтверждение перевода
    
    Args:
        user_id: ID пользователя-именинника
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для сбора средств
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BUTTON_TRANSFERRED,
                    callback_data=f"transferred:{user_id}"
                )
            ],
        ]
    )


