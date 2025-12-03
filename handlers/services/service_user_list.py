from aiogram.fsm.context import FSMContext
from exceptions.my_exceptions import StateDataError

# --- Утилита для получения user_dict из state ---
async def get_user_dict_from_state(state: FSMContext) -> dict:
    data = await state.get_data()
    user_dict = data.get("user_dict")
    if not user_dict:
        raise StateDataError("user_dict")
    return user_dict


# --- Утилита для получения user_id по номеру ---
def get_user_id_by_num(user_dict: dict, num_str: str) -> int:
    try:
        user_num = int(num_str)
        user_id = user_dict.get(user_num)
        if not user_id:
            raise ValueError
        return user_id
    except Exception:
        raise ValueError