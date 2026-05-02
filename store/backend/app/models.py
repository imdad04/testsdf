from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class OrderStatus(StrEnum):
    PENDING = "pending"        # created, awaiting payment
    PAID = "paid"              # payment received, queued for operator
    IN_PROGRESS = "in_progress"  # operator took it
    DELIVERED = "delivered"    # key delivered to client
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(StrEnum):
    PLATEGA = "platega"
    CRYPTOBOT = "cryptobot"
    BALANCE = "balance"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram id
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(64))
    language_code: Mapped[str | None] = mapped_column(String(8))
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    cashback: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    referrer_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    orders: Mapped[list["Order"]] = relationship(back_populates="user", foreign_keys="Order.user_id")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    icon: Mapped[str | None] = mapped_column(String(32))  # emoji or url
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String(128))
    subtitle: Mapped[str | None] = mapped_column(String(128))   # e.g. "1 month"
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    icon_url: Mapped[str | None] = mapped_column(String(512))
    # internal: where the operator buys this from. NEVER shown to client.
    source_url: Mapped[str | None] = mapped_column(String(512))
    source_note: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    category: Mapped[Category] = relationship()


class Promo(Base):
    __tablename__ = "promos"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    discount_pct: Mapped[int] = mapped_column(Integer, default=0)   # 0-100
    discount_fixed: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    promo_id: Mapped[int | None] = mapped_column(ForeignKey("promos.id"))
    status: Mapped[str] = mapped_column(String(16), default=OrderStatus.PENDING)
    payment_method: Mapped[str] = mapped_column(String(16))
    payment_id: Mapped[str | None] = mapped_column(String(128))   # provider tx id
    payment_url: Mapped[str | None] = mapped_column(String(512))
    operator_id: Mapped[int | None] = mapped_column(BigInteger)
    operator_msg_id: Mapped[int | None] = mapped_column(BigInteger)
    delivered_payload: Mapped[str | None] = mapped_column(Text)   # the key/code
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped[User] = relationship(back_populates="orders", foreign_keys=[user_id])
    product: Mapped[Product] = relationship()
    promo: Mapped[Promo | None] = relationship()


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram id
    name: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str | None] = mapped_column(String(128))
    payload: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
