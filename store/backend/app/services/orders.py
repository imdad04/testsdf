"""Order business logic shared between webhook handlers and bot callbacks."""

from datetime import datetime
from decimal import Decimal

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus, PaymentMethod, Product, Promo, User
from app.services.notifications import (
    notify_client_delivered,
    notify_client_processing,
    notify_client_refund,
    notify_operator,
)


async def get_or_create_user(session: AsyncSession, tg_user: dict) -> User:
    user = await session.get(User, tg_user["id"])
    if user is None:
        user = User(
            id=tg_user["id"],
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name"),
            language_code=tg_user.get("language_code"),
        )
        session.add(user)
        await session.flush()
    else:
        # keep profile fresh
        user.username = tg_user.get("username") or user.username
        user.first_name = tg_user.get("first_name") or user.first_name
    return user


class InvalidPromoError(Exception):
    """Raised when user-supplied promo code is invalid; surfaced to the client."""


async def apply_promo(session: AsyncSession, code: str, base_amount: Decimal) -> tuple[Decimal, Promo | None]:
    if not code:
        return base_amount, None
    # Promo codes are stored upper-case by the admin tools; normalize input.
    normalized = code.strip().upper()
    promo = (await session.execute(select(Promo).where(Promo.code == normalized))).scalar_one_or_none()
    if not promo:
        raise InvalidPromoError("промокод не найден")
    if not promo.is_active:
        raise InvalidPromoError("промокод отключён")
    if promo.max_uses and promo.used_count >= promo.max_uses:
        raise InvalidPromoError("количество активаций исчерпано")
    if promo.expires_at and promo.expires_at < datetime.utcnow():
        raise InvalidPromoError("срок действия истёк")
    amount = base_amount
    if promo.discount_pct:
        amount = amount * (Decimal(100) - Decimal(promo.discount_pct)) / Decimal(100)
    if promo.discount_fixed:
        amount = max(Decimal("0"), amount - promo.discount_fixed)
    return amount.quantize(Decimal("0.01")), promo


async def create_order(
    session: AsyncSession,
    user: User,
    product: Product,
    quantity: int,
    payment_method: PaymentMethod,
    promo_code: str | None = None,
) -> tuple[Order, Promo | None]:
    base = product.price * Decimal(quantity)
    amount, promo = await apply_promo(session, promo_code or "", base)
    order = Order(
        user_id=user.id,
        product_id=product.id,
        quantity=quantity,
        amount=amount,
        promo_id=promo.id if promo else None,
        payment_method=payment_method.value,
        status=OrderStatus.PENDING,
    )
    session.add(order)
    await session.flush()
    return order, promo


async def mark_paid(session: AsyncSession, bot: Bot, order_id: int, payment_id: str | None = None) -> bool:
    """Idempotent: marks order paid + notifies operator + reassures client."""
    order = await session.get(Order, order_id)
    if order is None or order.status != OrderStatus.PENDING:
        return False
    order.status = OrderStatus.PAID
    order.paid_at = datetime.utcnow()
    if payment_id:
        order.payment_id = payment_id

    product = await session.get(Product, order.product_id)
    user = await session.get(User, order.user_id)

    if order.promo_id:
        promo = await session.get(Promo, order.promo_id)
        if promo:
            promo.used_count += 1

    await session.flush()

    msg_id = await notify_operator(bot, order, product, user)
    order.operator_msg_id = msg_id

    await notify_client_processing(bot, user.id, order.id)
    await session.commit()
    return True


async def operator_take(session: AsyncSession, order_id: int, operator_id: int) -> Order | None:
    order = await session.get(Order, order_id)
    if not order or order.status != OrderStatus.PAID:
        return None
    order.status = OrderStatus.IN_PROGRESS
    order.operator_id = operator_id
    await session.commit()
    return order


async def operator_deliver(
    session: AsyncSession, bot: Bot, order_id: int, operator_id: int, payload: str
) -> Order | None:
    order = await session.get(Order, order_id)
    if not order or order.status not in (OrderStatus.PAID, OrderStatus.IN_PROGRESS):
        return None
    order.status = OrderStatus.DELIVERED
    order.operator_id = operator_id
    order.delivered_payload = payload
    order.delivered_at = datetime.utcnow()
    await session.commit()
    await notify_client_delivered(bot, order.user_id, order.id, payload)
    return order


async def operator_refund(session: AsyncSession, bot: Bot, order_id: int, operator_id: int) -> Order | None:
    order = await session.get(Order, order_id)
    if not order or order.status not in (OrderStatus.PAID, OrderStatus.IN_PROGRESS):
        return None
    order.status = OrderStatus.REFUNDED
    order.operator_id = operator_id
    await session.commit()
    await notify_client_refund(bot, order.user_id, order.id)
    return order
