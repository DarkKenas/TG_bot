from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Константы для кнопок панели коллектора
UPDATE_COLLECTOR_DATA = "update_collector_data"
CREATE_COLLECTOR_DATA = "create_collector_data"
VIEW_ALL_TRANSFERS = "view_all_transfers"

# Константы для редактирования данных коллектора
EDIT_COLLECTOR_PHONE = "edit_collector_phone"
EDIT_COLLECTOR_BANK = "edit_collector_bank"
SKIP_COLLECTOR_BANK = "skip_collector_bank"


def get_collector_menu_keyboard(is_active: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура панели коллектора

    Args:
        is_active: True если коллектор активный (может видеть все переводы)
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="✏️ Редактировать данные", callback_data=UPDATE_COLLECTOR_DATA
            )
        ]
    ]

    # Кнопка просмотра переводов доступна только активному коллектору
    if is_active:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="📋 Посмотреть все переводы", callback_data=VIEW_ALL_TRANSFERS
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_collector_create_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для создания нового коллектора"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Указать реквизиты", callback_data=CREATE_COLLECTOR_DATA
                )
            ]
        ]
    )


def get_collector_edit_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для редактирования данных коллектора"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Номер телефона", callback_data=EDIT_COLLECTOR_PHONE
                )
            ],
            [InlineKeyboardButton(text="🏦 Банк", callback_data=EDIT_COLLECTOR_BANK)],
        ]
    )


def get_bank_edit_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для редактирования банка с опцией не указывать"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏦 Не указывать банк", callback_data=SKIP_COLLECTOR_BANK
                )
            ]
        ]
    )
