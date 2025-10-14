from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states.user_states import WishStates
from filters.valid import is_valid_url
from keyboards.common_keyboards import get_confirmation_keyboard

# Константы для валидации
MIN_WISH_LENGTH = 3
MAX_WISH_LENGTH = 500
MAX_URL_LENGTH = 2000


async def handle_wish_text(message: Message, state: FSMContext) -> bool:
    """Универсальная обработка текста желания.
    
    Args:
        message: Сообщение от пользователя с текстом желания
        state: Состояние FSM для сохранения данных
        
    Returns:
        bool: True если текст валидный и сохранен, False если есть ошибки
    """
    wish_text = message.text.strip()
    if len(wish_text) < MIN_WISH_LENGTH:
        await message.answer(
            f"❌ Текст желания должен содержать минимум {MIN_WISH_LENGTH} символа. Попробуйте еще раз:"
        )
        return False
    if len(wish_text) > MAX_WISH_LENGTH:
        await message.answer(
            f"❌ Текст желания слишком длинный (максимум {MAX_WISH_LENGTH} символов). Попробуйте еще раз:"
        )
        return False
    await state.update_data(wish_text=wish_text)
    return True


async def handle_wish_url(message: Message, state: FSMContext) -> bool:
    """Универсальная обработка URL желания.
    
    Args:
        message: Сообщение от пользователя с URL
        state: Состояние FSM для сохранения данных
        
    Returns:
        bool: True если URL валидный и сохранен, False если есть ошибки
    """
    url = message.text.strip()

    is_valid, answer = is_valid_url(url)

    # Проверяем, что это валидный URL
    if not is_valid:
        await message.answer(answer)
        return False

    # Проверяем длину URL
    if len(url) > MAX_URL_LENGTH:
        await message.answer(
            f"❌ URL слишком длинный (максимум {MAX_URL_LENGTH} символов). Попробуйте еще раз:"
        )
        return False

    await state.update_data(wish_url=url)
    return True


async def handle_wish_confirmation(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Показать данные желания для подтверждения.
    
    Args:
        event: Сообщение или колбэк от пользователя
        state: Состояние FSM для получения данных
    """
    data = await state.get_data()
    confirmation_text = f"🎯 <b>Проверьте ваше желание:</b>\n\n"
    if data.get("wish_url"):
        confirmation_text += f"<a href='{data['wish_url']}'>{data['wish_text']}</a>"
    else:
        confirmation_text += f"{data['wish_text']}"
    
    if isinstance(event, Message):
        await event.answer(
            confirmation_text,
            reply_markup=get_confirmation_keyboard(),
            disable_web_page_preview=True,
        )
    else:
        await event.message.edit_text(
            confirmation_text,
            reply_markup=get_confirmation_keyboard(),
            disable_web_page_preview=True,
        )
    await state.set_state(WishStates.confirmation)
