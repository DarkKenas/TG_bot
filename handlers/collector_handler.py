from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging
import asyncio

from db_handler import PostgresHandler
from keyboards.main_menu_keyboards import BUTTON_COLLECTOR_PANEL, get_main_menu_keyboard
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
    """Просмотр предложений подарков (только для активного коллектора)."""
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

        # Оставляем только записи с предложениями подарков
        transfers = [t for t in transfers if t.gift_text or t.gift_url]

        if not transfers:
            await callback.message.edit_text("📋 <b>Предложений подарков пока нет</b>")
            return

        # Группируем предложения по именинникам
        grouped_transfers: dict[int, list[Transfer]] = {}
        for transfer in transfers:
            birthday_user_id = transfer.birthday_user_id
            if birthday_user_id not in grouped_transfers:
                grouped_transfers[birthday_user_id] = []
            grouped_transfers[birthday_user_id].append(transfer)

        # Формируем текст отчета
        report_lines = ["📋 <b>Предложения подарков:</b>\n"]

        for birthday_user_id, user_transfers in grouped_transfers.items():
            birthday_user = user_transfers[0].birthday_user
            report_lines.append(f"\n🎂 <b>{birthday_user.full_name}</b>:\n")

            for transfer in user_transfers:
                sender = transfer.sender
                text = transfer.gift_text or "Без описания"
                if transfer.gift_url:
                    report_lines.append(
                        f"  🎁 {sender.initials}: <a href='{transfer.gift_url}'>{text}</a>\n"
                    )
                else:
                    report_lines.append(f"  🎁 {sender.initials}: {text}\n")

        report_text = "".join(report_lines)
        await callback.message.edit_text(report_text, disable_web_page_preview=True)

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
            active_collector = await db.set_active_collector(user_id)

            # Отправляем уведомление всем админам о новом активном коллекторе
            try:
                admins = await db.get_all_administrators()
                collector_user = await db.get_user(user_id)
                notification_text = (
                    "🔔 <b>Новый активный коллектор назначен!</b>\n\n"
                    f"👤 <b>Коллектор:</b> {collector_user.full_name}\n"
                    f"📱 <b>Телефон:</b> <code>{active_collector.phone_number}</code>\n"
                    f"🏦 <b>Банк:</b> {active_collector.bank_name or 'не указан'}"
                )

                for admin in admins:
                    try:
                        await callback.bot.send_message(
                            admin.user_id,
                            notification_text,
                        )
                        logger.info(
                            f"✅ Уведомление о новом коллекторе отправлено админу {admin.user_id}"
                        )
                    except Exception as e:
                        error_msg = str(e).lower()
                        if "blocked" in error_msg or "chat not found" in error_msg:
                            logger.warning(
                                f"Админ {admin.user_id} заблокировал бота или чат не найден"
                            )
                        else:
                            logger.exception(
                                f"Ошибка отправки уведомления админу {admin.user_id}: {e}"
                            )
            except Exception as e:
                logger.exception(f"Ошибка при отправке уведомлений админам: {e}")

        await callback.message.edit_text(
            "✅ <b>Данные успешно сохранены!</b>\n\n"
            f"📱 Телефон: <code>{data['phone_number']}</code>\n"
            f"🏦 Банк: {data.get('bank_name') or 'не указан'}"
        )

        # Обновляем меню пользователя, чтобы появилась кнопка панели коллектора
        try:
            # Небольшая задержка, чтобы БД успела обновиться
            await asyncio.sleep(0.1)

            updated_user = await db.get_user(user_id)
            is_collector = updated_user.is_collector
            logger.info(
                f"Обновление меню для пользователя {user_id} после создания коллектора: "
                f"is_admin={updated_user.is_admin}, is_collector={is_collector}, "
                f"collector exists={updated_user.collector is not None}"
            )

            if not is_collector:
                logger.warning(
                    f"⚠️ Пользователь {user_id} не определяется как коллектор после создания! "
                    f"collector={updated_user.collector}"
                )

            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text="🔔 Ваше меню обновлено! Теперь доступна 💰Сбор панель",
                reply_markup=await get_main_menu_keyboard(
                    is_admin=updated_user.is_admin,
                    is_collector=is_collector,
                ),
            )
        except Exception as e:
            logger.exception(f"Не удалось обновить меню пользователя {user_id}: {e}")

    except Exception as e:
        logger.exception(f"Ошибка при сохранении данных коллектора {user_id}: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при сохранении данных")

    await state.clear()


@collector_router.callback_query(F.data == "confirm_no", CollectorStates.confirmation)
async def show_collector_edit_menu(callback: CallbackQuery):
    """Показать меню редактирования данных коллектора"""
    await callback.message.edit_reply_markup(reply_markup=get_collector_edit_keyboard())
    await callback.answer("Выберите что изменить")
