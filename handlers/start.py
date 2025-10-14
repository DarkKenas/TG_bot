from keyboards.register_keyboards import get_registration_keyboard
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram import Router

start_router = Router()


@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Добро пожаловать!\n\n Для начала выполните регистрацию:",
        reply_markup=get_registration_keyboard(),
    )
