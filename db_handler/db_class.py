from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text, delete, or_, and_, extract, func
from sqlalchemy.orm import selectinload
from datetime import date, datetime
import logging
from typing import TypeVar, Type

from .models import (
    Base,
    User,
    Wish,
    Transfer,
    Greeting,
    Administrator,
    Collector,
    ServiceUser
)
from exceptions.my_exceptions import (
    UserIdExist,
    RecordNotFound,
    RecordExist,
    CollectorUniquenessError,
)

logger = logging.getLogger(__name__)

# TypeVar для типизации универсального метода
T = TypeVar("T")


class PostgresHandler:
    def __init__(self, db_url: str):
        # URL уже содержит +asyncpg (конвертация в config.py)
        self.db_url = db_url
        self.engine = None
        self.async_session = None

    async def create_pool(self):
        """Инициализация подключения к БД"""
        try:
            self.engine = create_async_engine(
                self.db_url,
                # Проверка подключения сессии (если нет, то подключается автоматом)
                pool_pre_ping=True,
            )

            self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)

            # Создаем таблицы
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Проверяем подключение
            await self._check_connection()
            logger.info("✅ Database connected successfully")

        except Exception as e:
            logger.exception(f"❌ Database connection failed: {e}")
            raise
        
    async def close_pool(self):
        """Закрытие подключения"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
            
    async def init_data(self, service_user_id: int) -> None:
        """Функция инициализации начальных данных в БД

        Args:
            service_user_id (int): id сервисного пользователя
        """
        async with self.async_session() as session:
            result = await session.execute(select(ServiceUser))
            existing = result.scalars().first()
            if not existing:
                session.add(ServiceUser(user_id=service_user_id))
                await session.commit()
        logger.info("✅ Date initialization was successful")

    # === СЕРВИСНЫЕ МЕТОДЫ ===

    async def _check_connection(self):
        """Проверка подключения к БД"""
        async with self.async_session() as session:
            result = await session.execute(text("SELECT 1"))
            if result.scalar() != 1:
                raise ConnectionError("Unexpected result")
            
    async def _get_obj_or_raise(
        self,
        user_id: int,
        session: AsyncSession,
        model_class: Type[T],
        connect_user: bool = False,
    ) -> T:
        """Универсальный метод получения объекта по user_id

        Args:
            user_id: ID пользователя
            session: Активная сессия БД
            model_class: Класс модели для поиска
            connect_user Загружать ли связанные данные пользователя

        Returns:
            Найденный объект

        Raises:
            RecordNotFound: Если объект не найден
        """
        if model_class == User:
            # Для User модели поиск по primary key
            obj = await session.get(model_class, user_id)
        else:
            # Для других моделей поиск по полю user_id
            query = select(model_class).where(model_class.user_id == user_id)

            # Загружаем связанные данные пользователя при необходимости
            if connect_user:
                query = query.options(selectinload(model_class.user))

            result = await session.execute(query)
            obj = result.scalar_one_or_none()

        if not obj:
            raise RecordNotFound(user_id, model_class.__tablename__)
        return obj

    # === МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ===

    async def add_user(
        self,
        user_id: int,
        username: str,
        last_name: str,
        first_name: str,
        patronymic: str,
        birth_date: date,
    ):
        """Добавление нового пользователя (базовая информация)

        Args:
            user_id (int): ID пользователя
            username (str): Логин пользователя
            last_name (str): Фамилия пользователя
            first_name (str): Имя пользователя
            patronymic (str): Отчество пользователя
            birth_date (date): Дата рождения пользователя
        """
        user_id = int(user_id)
        async with self.async_session() as session:
            # Проверяем, есть ли уже такой пользователь
            existing_user = await session.get(User, user_id)
            if existing_user:
                raise UserIdExist(user_id)

            new_user = User(
                user_id=user_id,
                username=username,
                last_name=last_name,
                first_name=first_name,
                patronymic=patronymic,
                birth_date=birth_date,
            )
            session.add(new_user)
            await session.commit()
            logger.info(f"✅ User {user_id} added to database")

    async def update_user(
        self,
        user_id: int,
        username: str,
        last_name: str | None = None,
        first_name: str | None = None,
        patronymic: str | None = None,
        birth_date: date | None = None,
    ) -> None:
        """Обновление информации о пользователе"""
        user_id = int(user_id)
        async with self.async_session() as session:
            user = await self._get_obj_or_raise(user_id, session, User)

            user.username = username
            if last_name:
                user.last_name = last_name
            if first_name:
                user.first_name = first_name
            if patronymic:
                user.patronymic = patronymic
            if birth_date:
                user.birth_date = birth_date

            await session.commit()
            logger.info(f"✅ User {user_id} updated in database")

    async def delete_user(self, user_id: int) -> None:
        """Удаление пользователя"""
        user_id = int(user_id)
        async with self.async_session() as session:
            user = await self._get_obj_or_raise(user_id, session, User)
            await session.delete(user)
            await session.commit()
            logger.info(f"✅ User {user_id} deleted from database")

    async def get_user(self, user_id: int) -> User:
        """Получение данных пользователя"""
        user_id = int(user_id)
        async with self.async_session() as session:
            return await self._get_obj_or_raise(user_id, session, User)

    async def get_all_users(self, with_transfers: bool = False) -> list[User]:
        """Получение всех пользователей

        Args:
            with_transfers: Загружать ли переводы пользователей

        Returns:
            list[User]: Список пользователей
        """
        async with self.async_session() as session:
            query = select(User)

            if with_transfers:
                query = query.options(selectinload(User.sent_transfers))

            result = await session.execute(query)
            return result.scalars().all()

    # === МЕТОДЫ ДЛЯ ЖЕЛАНИЙ ===

    async def add_wish(
        self, user_id: int, wish_text: str, wish_url: str | None = None
    ) -> None:
        """Добавление пожелания

        Args:
            user_id (int): ID пользователя
            wish_text (str): Текст пожелания
            wish_url (str, optional): Ссылка на товар. Defaults to None.
        """
        user_id = int(user_id)
        async with self.async_session() as session:
            # Проверяем, существует ли пользователь
            await self._get_obj_or_raise(user_id, session, User)

            wish = Wish(user_id=user_id, wish_text=wish_text, wish_url=wish_url)
            session.add(wish)
            await session.commit()

            # Получаем ID созданного желания
            await session.refresh(wish)
            logger.info(f"✅ Wish added for user {user_id}, wish_id: {wish.id}")

    async def get_wish(self, wish_id: int) -> Wish:
        """Получение желания по ID"""
        wish_id = int(wish_id)
        async with self.async_session() as session:
            wish = await session.get(Wish, wish_id)
            if not wish:
                raise RecordNotFound(wish_id, Wish.__tablename__)
            return wish

    async def get_wish_list(self, user_id: int) -> list[Wish]:
        """Получение всех желаний пользователя"""
        user_id = int(user_id)
        async with self.async_session() as session:
            wishes = await session.scalars(
                select(Wish).where(Wish.user_id == user_id).order_by(Wish.id)
            )
            return list(wishes)

    async def delete_wish(self, wish_id: int, user_id: int):
        """Удаление желания"""
        wish_id = int(wish_id)
        user_id = int(user_id)
        async with self.async_session() as session:
            wish = await session.get(Wish, wish_id)

            if wish and wish.user_id == user_id:
                await session.delete(wish)
                await session.commit()
                logger.info(f"✅ Wish {wish_id} deleted by user {user_id}")
            else:
                raise RecordNotFound(wish_id, Wish.__tablename__, user_id=user_id)

    async def update_wish(
        self,
        wish_id: int,
        user_id: int,
        wish_text: str | None = None,
        wish_url: str | None = None,
    ):
        """Обновление желания

        Args:
            wish_id (int): ID желания
            user_id (int): ID пользователя
            wish_text (str, optional): Текст желания. Defaults to None.
            wish_url (str, optional): Ссылка на товар. Defaults to None.
        """
        wish_id = int(wish_id)
        user_id = int(user_id)
        async with self.async_session() as session:
            wish = await session.get(Wish, wish_id)

            if wish and wish.user_id == user_id:
                if wish_text:
                    wish.wish_text = wish_text
                if wish_url is not None:
                    wish.wish_url = wish_url

                await session.commit()
                logger.info(f"✅ Wish {wish_id} updated by user {user_id}")
            else:
                raise RecordNotFound(wish_id, Wish.__tablename__, user_id=user_id)

    # === МЕТОДЫ ДЛЯ ПЕРЕВОДОВ ===

    async def add_transfer(
        self, sender_id: int, birthday_user_id: int, transfer_datetime: datetime
    ):
        """Добавление записи о переводе

        Args:
            sender_id (int): ID отправителя
            birthday_user_id (int): ID именинника
            transfer_datetime (datetime): Время перевода

        Returns:
            bool: True если перевод добавлен, False если уже существует
        """
        sender_id = int(sender_id)
        birthday_user_id = int(birthday_user_id)

        async with self.async_session() as session:
            # Проверяем существование пользователей
            await self._get_obj_or_raise(sender_id, session, User)
            await self._get_obj_or_raise(birthday_user_id, session, User)

            # Проверяем, не отправлял ли уже этот пользователь перевод для данного именинника
            existing_transfer = await session.execute(
                select(Transfer).where(
                    Transfer.sender_id == sender_id,
                    Transfer.birthday_user_id == birthday_user_id,
                )
            )

            if existing_transfer.scalar_one_or_none():
                logger.warning(
                    f"Перевод уже существует: отправитель {sender_id} -> именинник {birthday_user_id}"
                )
                return False  # Перевод уже был зарегистрирован

            transfer = Transfer(
                sender_id=sender_id,
                birthday_user_id=birthday_user_id,
                transfer_datetime=transfer_datetime,
            )
            session.add(transfer)
            await session.commit()

            # Получаем ID созданного перевода
            await session.refresh(transfer)
            logger.info(
                f"✅ Добавлен перевод: отправитель {sender_id} -> именинник {birthday_user_id}, ID перевода: {transfer.id}"
            )
            return True

    async def get_transfers_for_birthday_user(
        self, birthday_user_id: int
    ) -> list[Transfer]:
        """Получение всех переводов для конкретного именинника"""
        birthday_user_id = int(birthday_user_id)
        async with self.async_session() as session:
            transfers = await session.scalars(
                select(Transfer)
                .where(Transfer.birthday_user_id == birthday_user_id)
                .order_by(Transfer.transfer_datetime.desc())
            )
            return list(transfers)

    async def get_all_transfers(self) -> list[Transfer]:
        """Получение всех переводов, сгруппированных по имениннику и отсортированных по дате"""
        async with self.async_session() as session:
            transfers = await session.execute(
                select(Transfer)
                .options(
                    selectinload(Transfer.sender), selectinload(Transfer.birthday_user)
                )
                .order_by(Transfer.birthday_user_id, Transfer.transfer_datetime.desc())
            )
            return transfers.scalars().all()

    # === МЕТОДЫ ДЛЯ АДМИНИСТРАТОРА ===

    async def add_administrator(self, user_id: int):
        """Создание записи администратора"""
        user_id = int(user_id)
        async with self.async_session() as session:
            # Проверяем, не является ли уже админом
            existing_admin = await session.get(Administrator, user_id)
            
            if existing_admin:
                raise RecordExist(Administrator.__tablename__, user_id=user_id)

            administrator = Administrator(user_id=user_id)
            session.add(administrator)
            await session.commit()

            logger.info(f"✅ Создан администратор для пользователя {user_id}")

    async def get_administrator(self, user_id: int) -> Administrator:
        """Получение админа"""
        user_id = int(user_id)
        async with self.async_session() as session:
            return await self._get_obj_or_raise(user_id, session, Administrator)
    
    async def delete_administrator(self, user_id: int) -> Administrator:
        """Удаление администратора"""
        async with self.async_session() as session:
            admin = await self._get_obj_or_raise(user_id, session, Administrator)
            await session.delete(admin)
            await session.commit()
            logger.info(f"✅ Admin {user_id} deleted from database")
    
    async def get_all_administrators(self) -> list[Administrator]:
        """Получение всех админов

        Returns:
            list[Administrator]: Список админов
        """
        async with self.async_session() as session:
            result = await session.execute(select(Administrator))
            return result.scalars().all()
        
    # === МЕТОДЫ ДЛЯ СЕРВИС ЮЗЕРА ===
    async def set_service_user(self, user_id: int) -> ServiceUser:
        user_id = int(user_id)
        async with self.async_session() as session:
            result = await session.execute(select(ServiceUser))
            service_user = result.scalars().first()
            if service_user:
                service_user.user_id == user_id
            else:
                service_user = ServiceUser(user_id=user_id)
                session.add(service_user)
            await session.commit()
            logger.info(f"✅ Установлен сервисный пользователь с user_id: {user_id}")
    
    async def get_service_user(self) -> ServiceUser:
        async with self.async_session() as session:
            result = await session.execute(select(ServiceUser))
            return result.scalar_one()
            
    # === МЕТОДЫ ДЛЯ КОЛЛЕКТОРА ===

    async def create_collector(
        self,
        user_id: int,
        phone_number: str,
        bank_name: str | None = None,
    ) -> Collector:
        """Создание записи коллектора"""
        async with self.async_session() as session:
            # Проверяем, не является ли уже коллектором
            existing_collector = await session.execute(
                select(Collector).where(Collector.user_id == user_id)
            )
            if existing_collector.scalar_one_or_none():
                raise RecordExist("collectors", user_id=user_id)

            collector = Collector(
                user_id=user_id,
                phone_number=phone_number,
                bank_name=bank_name,
                is_active=False,
            )
            session.add(collector)
            await session.commit()
            await session.refresh(collector)

            logger.info(f"✅ Создан неактивный коллектор для пользователя {user_id}")
            return collector

    async def get_collector(self, user_id: int) -> Collector:
        """Получение записи коллектора"""
        user_id = int(user_id)
        async with self.async_session() as session:
            return await self._get_obj_or_raise(
                user_id, session, Collector, connect_user=True
            )

    async def get_all_collectors(self) -> list[Collector]:
        """Получение всех коллекторов с данными пользователей"""
        async with self.async_session() as session:
            collectors = await session.execute(
                select(Collector).options(selectinload(Collector.user))
            )
            return list(collectors.scalars())

    async def update_collector(
        self,
        user_id: int,
        phone_number: str | None = None,
        bank_name: str | None = None,
    ) -> Collector:
        """Обновление данных коллектора"""
        user_id = int(user_id)
        async with self.async_session() as session:
            collector = await self._get_obj_or_raise(user_id, session, Collector)

            if phone_number is not None:
                collector.phone_number = phone_number
            if bank_name is not None:
                collector.bank_name = bank_name

            await session.commit()
            await session.refresh(collector)

            logger.info(f"✅ Обновлен коллектор для пользователя {user_id}")
            return collector

    async def get_active_collector(self) -> Collector:
        """Получение активного коллектора"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Collector)
                .options(selectinload(Collector.user))
                .where(Collector.is_active == True)
            )
            collector = result.scalar_one_or_none()

            if not collector:
                raise RecordNotFound(
                    None, "collectors", details="Активный коллектор не найден"
                )

            return collector

    async def set_active_collector(self, user_id: int) -> Collector:
        """Назначение активного коллектора"""
        async with self.async_session() as session:
            # Проверяем, что коллектор существует
            collector = await session.execute(
                select(Collector).where(Collector.user_id == user_id)
            )
            collector = collector.scalar_one_or_none()

            if not collector:
                raise RecordNotFound(
                    user_id,
                    "collectors",
                    details=f"Коллектор с user_id {user_id} не найден",
                )

            # Деактивируем текущего активного коллектора
            await self._deactivate_current_collector(session)

            # Активируем нужного
            collector.is_active = True

            await session.commit()
            await session.refresh(collector)

            logger.info(f"✅ Коллектор {user_id} назначен активным")

            # Проверяем, что активен только один коллектор
            await self.validate_single_active_collector()

            return collector

    async def _deactivate_current_collector(self, session: AsyncSession) -> None:
        """Деактивация текущего активного коллектора (внутренний метод)"""
        # Ищем активного коллектора
        active_collector = await session.execute(
            select(Collector).where(Collector.is_active == True)
        )
        collector = active_collector.scalar_one_or_none()

        if collector:
            collector.is_active = False
            logger.info(f"Деактивирован коллектор {collector.user_id}")
        else:
            logger.debug("Активный коллектор не найден")

    async def validate_single_active_collector(self) -> None:
        """Проверка, что активен только один коллектор"""
        async with self.async_session() as session:
            result = await session.execute(
                select(func.count(Collector.id)).where(Collector.is_active == True)
            )
            count = result.scalar()

            if count > 1:
                logger.error(
                    f"⚠️ Найдено {count} активных коллекторов! Должен быть только один."
                )
                raise CollectorUniquenessError(count)

    async def clear_past_birthday_records(self) -> None:
        """Очистка записей переводов и поздравлений для пользователей,
        чьи дни рождения уже прошли"""
        current_date = datetime.now()

        async with self.async_session() as session:
            # Получаем всех пользователей с прошедшими днями рождения
            users = await session.execute(
                select(User).where(
                    or_(
                        extract("month", User.birth_date) < current_date.month,
                        and_(
                            extract("month", User.birth_date) == current_date.month,
                            extract("day", User.birth_date) < current_date.day,
                        ),
                    )
                )
            )
            past_birthday_users = users.scalars().all()

            if past_birthday_users:
                # Получаем ID пользователей с прошедшими днями рождения
                user_ids = [user.user_id for user in past_birthday_users]

                # Удаляем записи из таблицы Transfer
                await session.execute(
                    delete(Transfer).where(Transfer.birthday_user_id.in_(user_ids))
                )

                # Удаляем записи из таблицы Greeting
                await session.execute(
                    delete(Greeting).where(Greeting.birthday_user_id.in_(user_ids))
                )

                await session.commit()
                logger.info(f"✅ Cleared birthday records for {len(user_ids)} users")
