import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import get_settings
from db_handler import PostgresHandler

# Загружаем настройки (валидация происходит здесь!)
settings = get_settings()

# Используем настройки
default_service_user_id = settings.default_service_user_id
pg_db = PostgresHandler(settings.pg_link)  # URL уже с +asyncpg
scheduler = AsyncIOScheduler(timezone=settings.timezone)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=MemoryStorage())
