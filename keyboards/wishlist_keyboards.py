from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_url_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Нет URL 🔗", callback_data="url_no"),
            ]
        ]
    )


def get_edit_wishdata_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Текст", callback_data="edit_wish_text")],
            [InlineKeyboardButton(text="🔗 URL", callback_data="edit_wish_url")],
        ]
    )


def get_edit_wishlist_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать WishList", callback_data="edit_wishlist"
                )
            ]
        ]
    )


def get_edit_wish_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать Wish", callback_data="edit_wish"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Удалить Wish", callback_data="delete_wish"
                ),
            ],
        ]
    )


def get_num_wish_keyboards(wish_id_list: list[int]):
    """Кнопки для выбора номера желания"""
    inline_keyboard = []

    # Создаем кнопки по 3 в ряд
    row = []
    for i, wish_id in enumerate(wish_id_list, 1):
        row.append(
            InlineKeyboardButton(
                text=f"{i}",
                callback_data=f"select_wish:{wish_id}",
            )
        )

        # Каждые 3 кнопки - новый ряд
        if len(row) == 3:
            inline_keyboard.append(row)
            row = []

    # Добавляем оставшиеся кнопки
    if row:
        inline_keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
