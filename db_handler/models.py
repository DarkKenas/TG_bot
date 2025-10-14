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
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeMeta, relationship, Mapped
from typing import List

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
    administrator: Mapped["Administrator"] = relationship(
        "Administrator", back_populates="user"
    )
    collector: Mapped["Collector"] = relationship("Collector", back_populates="user")

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
        return f"{self.last_name} {self.first_name} {self.patronymic}"

    def get_initials_name(self):
        return f"{self.last_name} {self.first_name[0]}. {self.patronymic[0]}."


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

    # Связи с пользователями
    sender: Mapped["User"] = relationship(
        "User", foreign_keys=[sender_id], back_populates="sent_transfers"
    )
    birthday_user: Mapped["User"] = relationship(
        "User", foreign_keys=[birthday_user_id], back_populates="received_transfers"
    )

    def __repr__(self):
        return f"Transfer(id={self.id}, sender={self.sender_id}, birthday_user={self.birthday_user_id})"


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
