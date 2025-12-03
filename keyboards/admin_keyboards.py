from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

SET_ACTIVE_COLLECTOR = "admin_set_collector"
DELETE_USER = "admin_delete_user"


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура админ панели"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 Назначить ответственного за сбор",
                    callback_data=SET_ACTIVE_COLLECTOR,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить пользователя", callback_data=DELETE_USER
                ),
            ],
        ]
    )


def get_confirm_action_keyboard(
    action_type: str, target_id: int, role: str = ""
) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"{role}confirm_{action_type}:{target_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data="cancel"
                ),
            ]
        ]
    )
