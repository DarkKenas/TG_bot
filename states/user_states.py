from aiogram.fsm.state import State, StatesGroup


class UserDataStates(StatesGroup):
    waiting_for_last_name = State()
    waiting_for_first_name = State()
    waiting_for_patronymic = State()
    waiting_for_birth_date = State()
    confirmation = State()


class WishStates(StatesGroup):
    waiting_for_wish_text = State()
    waiting_for_wish_url = State()
    confirmation = State()


class CollectorStates(StatesGroup):
    """Состояния для регистрации/обновления коллектора"""

    waiting_for_phone = State()
    waiting_for_bank = State()
    confirmation = State()


class AdminStates(StatesGroup):
    """Состояния для админ-панели"""

    waiting_for_delete_user_num = State()
    waiting_for_collector_user_num = State()

class RoleStates(StatesGroup):
    """Состояния назначения ролей"""
    
    waiting_for_admin_phrase = State()
    waiting_for_service_phrase = State()

class ServiceStates(StatesGroup):
    """Состояния для сервис пользователя"""
    
    waiting_for_delete_admin_num = State()