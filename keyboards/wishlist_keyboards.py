from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_url_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Нет ссылки 🔗", callback_data="url_no"),
            ]
        ]
    )


def get_my_wishlist_keyboard(has_wishes: bool) -> InlineKeyboardMarkup:
    """Клавиатура под сообщением 'Мой вишлист'.

    - Всегда: добавить желание
    - Если есть желания: редактировать вишлист (выбор номера -> действия)
    """
    keyboard_buttons: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="➕ Добавить желание", callback_data="add_wish_from_list"
            )
        ]
    ]

    if has_wishes:
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать вишлист", callback_data="edit_wishlist"
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_edit_wishdata_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Текст", callback_data="edit_wish_text")],
            [InlineKeyboardButton(text="🔗 Ссылка", callback_data="edit_wish_url")],
        ]
    )


def get_edit_wish_keyboard():
    """Клавиатура с выбором действия для редактирования wish"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Изменить текст", callback_data="edit_wish_text_direct"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔗 Изменить ссылку", callback_data="edit_wish_url_direct"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Удалить желание", callback_data="delete_wish"
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
