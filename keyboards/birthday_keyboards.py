from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Константы для текстов кнопок
BUTTON_SUGGEST_GIFT = "🎁 Предложить вариант подарка"
BUTTON_WISHLISTS = "👥❤️ Вишлисты"

# callback для просмотра вишлистов из раздела дней рождений
BIRTHDAYS_WISHLISTS = "birthdays_wishlists"


def get_birthday_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с действиями для дня рождения.

    Содержит кнопки:
    - Предложить подарок
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BUTTON_SUGGEST_GIFT,
                    callback_data=f"suggest_gift:{user_id}",
                )
            ],
        ]
    )


def get_birthdays_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура под списком дней рождений.

    Содержит кнопку:
    - Вишлисты (просмотр вишлистов людей)
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BUTTON_WISHLISTS,
                    callback_data=BIRTHDAYS_WISHLISTS,
                )
            ]
        ]
    )
