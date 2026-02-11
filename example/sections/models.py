import random
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import factory
from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import expression

from brilliance_admin.translations import TranslateText as _
from example.database import async_sessionmaker_
from example.utils import SQLAlchemyFactoryBase


class ModelBase(DeclarativeBase):
    pass


class BaseIDModel(ModelBase):
    __abstract__ = True
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"),
        primary_key=True,
        autoincrement=True,
    )


class User(BaseIDModel):
    __tablename__ = "user"

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=True)

    is_staff: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=expression.true())

    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )  # pylint: disable=not-callable

    # group_associations = relationship("UserGroup", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class UserFactory(SQLAlchemyFactoryBase):
    class Meta:
        model = User
        sqlalchemy_session_factory = async_sessionmaker_
        sqlalchemy_session_persistence = "commit"

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Faker("email")


class DeviceType(Enum):
    DESKTOP = 'desktop'
    MOBILE = 'mobile'
    TABLET = 'tablet'

    @property
    def label(self):
        labels = {
            self.DESKTOP: _('device_type.desktop'),
            self.MOBILE: _('device_type.mobile'),
            self.TABLET: _('device_type.tablet'),
        }
        return labels[self]

    @property
    def tag_color(self):
        colors = {
            self.DESKTOP: 'blue-darken-1',
            self.MOBILE: 'green-darken-1',
            self.TABLET: 'orange-darken-1',
        }
        return colors[self]


class UserSession(BaseIDModel):
    __tablename__ = "user_session"

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    user: Mapped["User"] = relationship()

    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=True)

    device_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        info={"choices": DeviceType},
    )
    browser: Mapped[str] = mapped_column(String(50), nullable=True)
    os: Mapped[str] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=expression.true())

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, ip={self.ip_address})>"


class UserSessionFactory(SQLAlchemyFactoryBase):
    class Meta:
        model = UserSession
        sqlalchemy_session_factory = async_sessionmaker_
        sqlalchemy_session_persistence = "commit"

    user = factory.SubFactory(UserFactory)

    ip_address = factory.Faker("ipv4")
    country_code = factory.Faker("country_code")
    city = factory.Faker("city")

    device_type = factory.Faker("random_element", elements=["desktop", "mobile", "tablet"])
    browser = factory.Faker("random_element", elements=["Chrome", "Firefox", "Safari", "Edge", "Opera"])
    os = factory.Faker("random_element", elements=["Windows 11", "macOS", "Ubuntu", "iOS", "Android"])
    user_agent = factory.Faker("user_agent")

    is_active = factory.Faker("boolean", chance_of_getting_true=30)

    started_at = factory.Faker("date_time_between", start_date="-7d", end_date="now")
    ended_at = factory.LazyAttribute(
        lambda o: factory.Faker("date_time_between", start_date=o.started_at, end_date="now").evaluate(
            None, None, {"locale": None}
        ) if not o.is_active else None
    )


class Currency(BaseIDModel):
    __tablename__ = "currency"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    num_code: Mapped[int] = mapped_column(SmallInteger, unique=True, index=True, nullable=False)
    char_code: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)

    depth: Mapped[int] = mapped_column(SmallInteger, index=True, nullable=False, default=2)

    terminals: Mapped[list["Terminal"]] = relationship(back_populates="currency")  # noqa F821

    def __repr__(self):
        return f"<Currency(id={self.id}, num_code='{self.num_code}', char_code='{self.char_code}')>"

    def __str__(self):
        return self.title


class CurrencyFactory(SQLAlchemyFactoryBase):
    class Meta:
        model = Currency
        sqlalchemy_session_factory = async_sessionmaker_
        sqlalchemy_session_persistence = "commit"

    title = factory.Faker("currency_name")
    num_code = factory.Sequence(lambda n: 100 + n)
    char_code = factory.Sequence(lambda n: f"C{n:03d}")
    depth = factory.Faker("random_element", elements=[2, 3])


class Merchant(BaseIDModel):
    __tablename__ = "merchant"

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    provider_settings: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB().with_variant(JSON(), 'sqlite')),
        nullable=True,
    )

    tx_actions: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(ARRAY(String(50)).with_variant(JSON(), 'sqlite')),
        nullable=True,
    )

    description: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )  # pylint: disable=not-callable
    terminals: Mapped[list["Terminal"]] = relationship(back_populates="merchant")

    def __repr__(self):
        return f"<Merchant(id={self.id}, title='{self.title}')>"

    def __str__(self):
        return self.title


class MerchantFactory(SQLAlchemyFactoryBase):
    class Meta:
        model = Merchant
        sqlalchemy_session_factory = async_sessionmaker_
        sqlalchemy_session_persistence = "commit"

    user_id = factory.Faker("random_int", min=1, max=10_000)
    title = factory.Faker("word")
    description = factory.Faker("sentence", nb_words=6)
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))

    def __str__(self):
        return self.title


class Fee(BaseIDModel):
    __tablename__ = "fee"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    terminals: Mapped[list["Terminal"]] = relationship(back_populates="fee")

    def __repr__(self):
        return f"<Fee(id={self.id}, title='{self.title}')>"

    def __str__(self):
        return self.title


class FeeFactory(SQLAlchemyFactoryBase):
    class Meta:
        model = Fee
        sqlalchemy_session_factory = async_sessionmaker_
        sqlalchemy_session_persistence = "commit"

    title = factory.Faker("word")

    def __str__(self):
        return self.title


class TerminalStatuses(Enum):
    PROCESS = 'process'
    SUCCESS = 'success'
    ERROR = 'error'

    @property
    def label(self):
        labels = {
            self.PROCESS: _('statuses.process'),
            self.SUCCESS: _('statuses.success'),
            self.ERROR: _('statuses.error'),
        }
        return labels[self]

    @property
    def tag_color(self):
        colors = {
            self.PROCESS: 'grey-lighten-1',
            self.SUCCESS: 'green-darken-1',
            self.ERROR: 'red-lighten-2',
        }
        return colors[self]


class Terminal(BaseIDModel):
    __tablename__ = "terminal"

    manager_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        info={"label": _("description")},
    )
    secret_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )

    status: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        info={"choices": TerminalStatuses},
    )

    return_url: Mapped[str] = mapped_column(String(500), nullable=True)
    callback_url: Mapped[str] = mapped_column(String(500), nullable=True)

    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchant.id"), index=True)
    merchant: Mapped["Merchant"] = relationship(back_populates="terminals")

    currency_id: Mapped[int] = mapped_column(ForeignKey("currency.id"), index=True)
    currency: Mapped["Currency"] = relationship(back_populates="terminals")  # noqa F821

    fee_id: Mapped[int] = mapped_column(ForeignKey("fee.id"), nullable=True)
    fee: Mapped["Fee"] = relationship(back_populates="terminals")

    is_h2h: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=expression.true())
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=expression.true())

    public_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    imitation_api: Mapped[str] = mapped_column(String(50), nullable=True)
    test_mode: Mapped[bool] = mapped_column(nullable=False, default=False)

    registered_delay: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # errors: Mapped[dict[str, Any]] = mapped_column(JSONB().with_variant(JSON(), 'sqlite'), nullable=True)
    errors: Mapped[list[Any]] = mapped_column(
        MutableList.as_mutable(ARRAY(JSONB).with_variant(JSON(), 'sqlite')),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )  # DateTime used once

    # whitelist_ips: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    def __repr__(self):
        return f"<Terminal #{self.id} title={self.title}>"

    def __str__(self):
        return self.title


class TerminalFactory(SQLAlchemyFactoryBase):
    class Meta:
        model = Terminal
        sqlalchemy_session_factory = async_sessionmaker_
        sqlalchemy_session_persistence = "commit"

    manager_id = factory.Sequence(lambda n: n + 1)

    title = factory.Faker("company")
    description = factory.Faker("sentence", nb_words=6)

    status = factory.LazyFunction(lambda: random.choice(list(TerminalStatuses)).value)

    secret_key = factory.LazyFunction(lambda: str(uuid.uuid4()))
    public_id = factory.LazyFunction(lambda: str(uuid.uuid4()))

    merchant = factory.SubFactory(MerchantFactory)
    currency = factory.SubFactory(CurrencyFactory)

    is_h2h = factory.Faker("boolean")
    is_active = factory.Faker("boolean")

    imitation_api = factory.Faker("random_element", elements=[None, "sandbox", "mock"])
    test_mode = factory.Faker("boolean")

    errors = [{"code": "exception", "message": "Insufficient funds", "provider_code": "insufficient-funds"}]

    registered_delay = factory.Faker(
        "random_element",
        elements=[None, 5, 10, 30, 60],
    )
