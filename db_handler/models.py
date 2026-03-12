from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Text,
    ForeignKey,
    DateTime,
    BigInteger,
    Boolean,
    Numeric,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeMeta, relationship, Mapped
from typing import List, Optional

Base: DeclarativeMeta = declarative_base()


class User(Base):
    """Модель пользователя"""

    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(32), unique=True)
    first_name = Column(String(64))
    last_name = Column(String(64))
    patronymic = Column(String(64))
    birth_date = Column(Date)

    # Связи с другими таблицами
    wishes: Mapped[List["Wish"]] = relationship("Wish", back_populates="user")
    administrator: Mapped[Optional["Administrator"]] = relationship(
        "Administrator", back_populates="user", lazy="selectin"
    )
    collector: Mapped[Optional["Collector"]] = relationship(
        "Collector", back_populates="user", lazy="selectin"
    )
    service_user: Mapped[Optional["ServiceUser"]] = relationship(
        "ServiceUser", back_populates="user", lazy="selectin"
    )

    # Связь с переводами (отправленные)
    sent_transfers: Mapped[List["Transfer"]] = relationship(
        "Transfer",
        foreign_keys="Transfer.sender_id",
        back_populates="sender",
        lazy="selectin",
        cascade="all, delete",
    )

    # Связь с переводами (полученные для именинника)
    received_transfers: Mapped[List["Transfer"]] = relationship(
        "Transfer",
        foreign_keys="Transfer.birthday_user_id",
        back_populates="birthday_user",
        lazy="selectin",
        cascade="all, delete",
    )

    def __repr__(self):
        return f"User(id={self.user_id}, username={self.username})"

    def get_full_name(self):
        """Получить полное имя (метод для обратной совместимости)"""
        return f"{self.last_name} {self.first_name} {self.patronymic}"

    def get_initials_name(self):
        """Получить инициалы (метод для обратной совместимости)"""
        return f"{self.last_name} {self.first_name[0]}. {self.patronymic[0]}."

    @property
    def full_name(self) -> str:
        """Получить полное имя как свойство"""
        parts = [self.last_name or "", self.first_name or "", self.patronymic or ""]
        return " ".join(filter(None, parts)).strip() or f"Пользователь {self.user_id}"

    @property
    def initials(self) -> str:
        """Получить инициалы как свойство"""
        if not self.last_name or not self.first_name or not self.patronymic:
            return f"Пользователь {self.user_id}"
        return f"{self.last_name} {self.first_name[0]}. {self.patronymic[0]}."

    @property
    def is_admin(self) -> bool:
        """Проверка, является ли пользователь администратором"""
        return self.administrator is not None

    @property
    def is_collector(self) -> bool:
        """Проверка, является ли пользователь коллектором"""
        return self.collector is not None

    @property
    def is_service_user(self) -> bool:
        """Проверка, является ли пользователь сервисным пользователем"""
        return self.service_user is not None


class Wish(Base):
    """Модель желания"""

    __tablename__ = "wishes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    wish_text = Column(Text, nullable=False)
    wish_url = Column(Text, nullable=True)

    # Связь с пользователем
    user: Mapped["User"] = relationship("User", back_populates="wishes")

    def __repr__(self):
        return f"Wish(id={self.id}, user_id={self.user_id})"


class Administrator(Base):
    """Модель администратора системы"""

    __tablename__ = "administrators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Связь с пользователем
    user: Mapped["User"] = relationship("User", back_populates="administrator")

    def __repr__(self):
        return f"Administrator(id={self.id}, user_id={self.user_id})"


class Collector(Base):
    """Модель коллектора средств

    Важно: В системе может быть активен только один коллектор одновременно.
    Это обеспечивается логикой в db_class.py через методы _deactivate_all_collectors
    и validate_single_active_collector.
    """

    __tablename__ = "collectors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    phone_number = Column(String(20), nullable=False)
    bank_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)

    # Связь с пользователем
    user: Mapped["User"] = relationship("User", back_populates="collector")

    def __repr__(self):
        return (
            f"Collector(id={self.id}, user_id={self.user_id}, active={self.is_active})"
        )


class Transfer(Base):
    """Модель перевода"""

    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    birthday_user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    transfer_datetime = Column(DateTime, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)  # Сумма перевода (до 2 знаков после запятой)
    gift_text = Column(Text, nullable=True)  # Текст предложения подарка
    gift_url = Column(Text, nullable=True)  # Ссылка предложения подарка

    # Связи с пользователями
    sender: Mapped["User"] = relationship(
        "User", foreign_keys=[sender_id], back_populates="sent_transfers"
    )
    birthday_user: Mapped["User"] = relationship(
        "User", foreign_keys=[birthday_user_id], back_populates="received_transfers"
    )

    def __repr__(self):
        return f"Transfer(id={self.id}, sender={self.sender_id}, birthday_user={self.birthday_user_id}, amount={self.amount})"


class Greeting(Base):
    __tablename__ = "greetings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    birthday_user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    text = Column(Text, nullable=False)

    def __repr__(self):
        return f"Greeting(id={self.id}, sender={self.sender_id}, birthday_user={self.birthday_user_id})"


class ServiceUser(Base):
    """Модель сервисного пользователя
    
    В системе может быть только один сервисный пользователь.
    Это пользователь с максимальными правами для управления системой.
    """

    __tablename__ = "service_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Связь с пользователем
    user: Mapped["User"] = relationship("User", back_populates="service_user")

    def __repr__(self):
        return f"ServiceUser(id={self.id}, user_id={self.user_id})"
