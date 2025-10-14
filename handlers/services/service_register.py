from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.user_states import UserDataStates
from filters.valid import validate_name
from keyboards.common_keyboards import get_confirmation_keyboard
from datetime import datetime as dt


# Универсальные функции для обработки данных
async def handle_last_name(message: Message, state: FSMContext) -> bool:
    """Универсальная обработка фамилии"""
    if not validate_name(message.text):
        await message.answer(
            "❌ Фамилия должна содержать только буквы. Попробуйте еще раз:"
        )
        return False
    await state.update_data(last_name=message.text.title())
    return True


async def handle_first_name(message: Message, state: FSMContext) -> bool:
    """Универсальная обработка имени"""
    if not validate_name(message.text):
        await message.answer(
            "❌ Имя должно содержать только буквы. Попробуйте еще раз:"
        )
        return False
    await state.update_data(first_name=message.text.title())
    return True


async def handle_patronymic(message: Message, state: FSMContext) -> bool:
    """Универсальная обработка отчества"""
    if not validate_name(message.text):
        await message.answer(
            "❌ Отчество должно содержать только буквы. Попробуйте еще раз:"
        )
        return False
    await state.update_data(patronymic=message.text.title())
    return True


async def handle_birth_date(message: Message, state: FSMContext) -> bool:
    """Универсальная обработка даты рождения"""
    try:
        birth_date = dt.strptime(message.text, "%d.%m.%Y")
        await state.update_data(birth_date=birth_date)
        return True
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты. Попробуйте еще раз в формате ДД.ММ.ГГГГ:"
        )
        return False


async def handle_confirmation(message: Message, state: FSMContext):
    """Показать данные для подтверждения"""
    data = await state.get_data()
    confirmation_text = (
        f"📋 <b>Проверьте ваши данные:</b>\n\n"
        f"👤 Фамилия: {data['last_name']}\n"
        f"👤 Имя: {data['first_name']}\n"
        f"👤 Отчество: {data['patronymic']}\n"
        f"📅 Дата рождения: {data['birth_date'].strftime('%d.%m.%Y')}"
    )
    await message.answer(confirmation_text, reply_markup=get_confirmation_keyboard())
    await state.set_state(UserDataStates.confirmation)
