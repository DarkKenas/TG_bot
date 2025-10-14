import re
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states.user_states import CollectorStates
from keyboards.common_keyboards import get_confirmation_keyboard


def validate_phone(phone: str) -> bool:
    """Валидация российского номера телефона"""
    # Убираем все пробелы и символы кроме цифр и +
    phone_clean = re.sub(r"[^0-9+]", "", phone)

    # Проверяем российские форматы: +7XXXXXXXXXX или 8XXXXXXXXXX/7XXXXXXXXXX
    return bool(re.match(r"^(\+7[0-9]{10}|[78][0-9]{10})$", phone_clean))


async def handle_phone(message: Message, state: FSMContext) -> bool:
    """Обработка номера телефона"""
    phone = message.text.strip()

    if not validate_phone(phone):
        await message.answer(
            "❌ Неверный формат номера телефона.\n"
            "Используйте формат: +7XXXXXXXXXX или 8XXXXXXXXXX\n"
            "Попробуйте еще раз:"
        )
        return False

    await state.update_data(phone_number=phone)
    return True


async def handle_bank(message: Message, state: FSMContext) -> bool:
    """Обработка названия банка"""
    bank_name = message.text.strip()

    if len(bank_name) < 2:
        await message.answer(
            "❌ Название банка слишком короткое.\n" "Попробуйте еще раз:"
        )
        return False

    if len(bank_name) > 100:
        await message.answer(
            "❌ Название банка слишком длинное (максимум 100 символов)\n"
            "Попробуйте еще раз:"
        )
        return False

    await state.update_data(bank_name=bank_name)
    return True


async def handle_collector_confirmation(
    event: Message | CallbackQuery, state: FSMContext
):
    """Показать данные коллектора для подтверждения"""
    data = await state.get_data()

    confirmation_text = (
        f"📋 <b>Проверьте данные для переводов:</b>\n\n"
        f"📱 Номер телефона: <code>{data['phone_number']}</code>\n"
        f"🏦 Банк: {data.get('bank_name') or 'не указан'}"
    )

    if isinstance(event, Message):
        await event.answer(confirmation_text, reply_markup=get_confirmation_keyboard())
    else:
        await event.message.edit_text(
            confirmation_text, reply_markup=get_confirmation_keyboard()
        )
    await state.set_state(CollectorStates.confirmation)
