from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging

from db_handler import PostgresHandler
from keyboards.main_menu_keyboards import BUTTON_COLLECTOR_PANEL
from keyboards.collector_keyboards import (
    get_collector_menu_keyboard,
    get_collector_edit_keyboard,
    get_bank_edit_keyboard,
    UPDATE_COLLECTOR_DATA,
    CREATE_COLLECTOR_DATA,
    VIEW_ALL_TRANSFERS,
    EDIT_COLLECTOR_PHONE,
    EDIT_COLLECTOR_BANK,
    SKIP_COLLECTOR_BANK,
)
from db_handler.models import Transfer, User
from states.user_states import CollectorStates
from handlers.services.service_collector import (
    handle_phone,
    handle_bank,
    handle_collector_confirmation,
)

collector_router = Router()
logger = logging.getLogger(__name__)


@collector_router.message(F.text == BUTTON_COLLECTOR_PANEL)
async def show_collector_panel(message: Message, user: User):
    """Показ панели коллектора"""
    collector = user.collector
    if not collector:
        await message.answer("❌ У вас нет доступа к сбор панели")
        return

    try:
        status = "🟢 Активный" if collector.is_active else "🔴 Неактивный"

        await message.answer(
            f"💰 <b>Сбор панель</b>\n\n"
            f"<b>Данные для переводов:</b>\n"
            f"📱 <b>Номер телефона:</b> <code>{collector.phone_number}</code>\n"
            f"🏦 <b>Банк:</b> {collector.bank_name or 'не указан'}\n\n"
            f"📊 <b>Статус:</b> {status}\n\n"
            "Выберите действие:",
            reply_markup=get_collector_menu_keyboard(is_active=collector.is_active),
        )

    except Exception as e:
        logger.exception(
            f"Ошибка при отображении панели коллектора для {message.from_user.id}: {e}"
        )
        await message.answer("❌ Произошла ошибка при загрузке панели")


@collector_router.callback_query(F.data == UPDATE_COLLECTOR_DATA)
async def update_collector_data(callback: CallbackQuery, user: User, state: FSMContext):
    """Показать меню обновления данных коллектора"""
    collector = user.collector
    if not collector:
        await callback.answer("❌ У вас нет доступа к этой функции", show_alert=True)
        return

    await state.update_data(
        phone_number=collector.phone_number, bank_name=collector.bank_name, is_edit=True
    )
    await callback.message.edit_reply_markup(reply_markup=get_collector_edit_keyboard())
    await callback.answer("Выберите что изменить")


@collector_router.callback_query(F.data == CREATE_COLLECTOR_DATA)
async def create_collector_data(callback: CallbackQuery, state: FSMContext):
    """Показать меню обновления данных коллектора"""
    await edit_collector_phone(callback, state)


@collector_router.callback_query(F.data == VIEW_ALL_TRANSFERS)
async def view_all_transfers(callback: CallbackQuery, user: User, db: PostgresHandler):
    """Просмотр всех переводов (только для активного коллектора)"""
    collector = user.collector
    if not collector:
        await callback.answer("❌ У вас нет доступа к этой функции", show_alert=True)
        return

    if not collector.is_active:
        await callback.answer(
            "❌ Доступно только при активном статусе", show_alert=True
        )
        return

    try:
        transfers = await db.get_all_transfers()

        if not transfers:
            await callback.message.edit_text("📋 <b>Список переводов пуст</b>")
            return

        # Группируем переводы по именинникам
        grouped_transfers: dict[int, list[Transfer]] = {}
        for transfer in transfers:
            birthday_user_id = transfer.birthday_user_id
            if birthday_user_id not in grouped_transfers:
                grouped_transfers[birthday_user_id] = []
            grouped_transfers[birthday_user_id].append(transfer)

        # Формируем текст отчета
        report_lines = ["📋 <b>Отчет по переводам:</b>\n"]

        for birthday_user_id, user_transfers in grouped_transfers.items():
            birthday_user = user_transfers[0].birthday_user

            report_lines.append(f"\n🎂 <b>{birthday_user.full_name}</b>:\n")

            for transfer in user_transfers:
                transfer_date = transfer.transfer_datetime.strftime("%d.%m.%Y %H:%M")
                report_lines.append(
                    f"\n  💰 {transfer.sender.initials} - {transfer_date}"
                )

        report_text = "".join(report_lines)
        await callback.message.edit_text(report_text)

    except Exception as e:
        logger.exception(
            f"Ошибка при получении переводов для коллектора {callback.from_user.id}: {e}"
        )
        await callback.message.edit_text(
            "❌ Произошла ошибка при загрузке переводов",
        )


# =============== Обработчики редактирования данных коллектора ===============

@collector_router.callback_query(F.data == EDIT_COLLECTOR_PHONE)
async def edit_collector_phone(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование номера телефона"""
    phone_text = (
        "📱 Введите номер телефона в формате:\n" "• +7XXXXXXXXXX\n" "• 8XXXXXXXXXX\n"
    )
    await callback.message.edit_text(phone_text)
    await state.set_state(CollectorStates.waiting_for_phone)


@collector_router.callback_query(F.data == EDIT_COLLECTOR_BANK)
async def edit_collector_bank(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование банка"""
    await callback.message.edit_text(
        "🏦 Введите название банка:", reply_markup=get_bank_edit_keyboard()
    )
    await state.set_state(CollectorStates.waiting_for_bank)


@collector_router.callback_query(F.data == SKIP_COLLECTOR_BANK)
async def skip_collector_bank(callback: CallbackQuery, state: FSMContext):
    """Не указывать банк (установить в None)"""
    await state.update_data(bank_name=None)
    await handle_collector_confirmation(callback, state)


# =============== Обработчики состояний FSM ===============

@collector_router.message(CollectorStates.waiting_for_phone)
async def process_collector_phone(message: Message, state: FSMContext):
    """Обработка номера телефона коллектора"""
    if not await handle_phone(message, state):
        return

    data = await state.get_data()
    if data.get("is_edit"):
        await handle_collector_confirmation(message, state)
    else:
        await message.answer("🏦 Теперь введите название банка:")
        await state.set_state(CollectorStates.waiting_for_bank)


@collector_router.message(CollectorStates.waiting_for_bank)
async def process_collector_bank(message: Message, state: FSMContext):
    """Обработка банка коллектора"""
    if not await handle_bank(message, state):
        return

    await handle_collector_confirmation(message, state)


@collector_router.callback_query(F.data == "confirm_yes", CollectorStates.confirmation)
async def confirm_collector_data(
    callback: CallbackQuery,
    state: FSMContext,
    db: PostgresHandler,
):
    """Подтверждение данных коллектора - создание или обновление."""
    data = await state.get_data()
    user_id = callback.from_user.id
    is_edit = data.get("is_edit", False)

    try:
        if is_edit:
            await db.update_collector(
                user_id=user_id,
                phone_number=data.get("phone_number"),
                bank_name=data.get("bank_name"),
            )
        else:
            await db.create_collector(
                user_id=user_id,
                phone_number=data.get("phone_number"),
                bank_name=data.get("bank_name"),
            )
            await db.set_active_collector(user_id)

        await callback.message.edit_text(
            "✅ <b>Данные успешно сохранены!</b>\n\n"
            f"📱 Телефон: <code>{data['phone_number']}</code>\n"
            f"🏦 Банк: {data.get('bank_name') or 'не указан'}"
        )

    except Exception as e:
        logger.exception(f"Ошибка при сохранении данных коллектора {user_id}: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при сохранении данных")

    await state.clear()


@collector_router.callback_query(F.data == "confirm_no", CollectorStates.confirmation)
async def show_collector_edit_menu(callback: CallbackQuery):
    """Показать меню редактирования данных коллектора"""
    await callback.message.edit_reply_markup(reply_markup=get_collector_edit_keyboard())
    await callback.answer("Выберите что изменить")
