"""REST API consumed by the React WebApp."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import Category, Order, OrderStatus, PaymentMethod, Product
from app.schemas import (
    CatalogOut,
    CategoryOut,
    MeOut,
    OrderCreateIn,
    OrderListOut,
    OrderOut,
    ProductOut,
)
from app.security import AuthError, is_admin, parse_init_data
from app.services.cryptobot import CryptoBotClient
from app.services.orders import InvalidPromoError, create_order, get_or_create_user
from app.services.platega import PlategaClient

router = APIRouter(prefix="/api", tags=["webapp"])


async def _auth(init_data: str | None) -> dict:
    if not init_data:
        raise HTTPException(401, "missing initData")
    try:
        return parse_init_data(init_data)
    except AuthError as e:
        raise HTTPException(401, f"auth failed: {e}")


@router.get("/catalog", response_model=CatalogOut)
async def catalog(session: AsyncSession = Depends(get_session)):
    cats = (
        await session.execute(
            select(Category).where(Category.is_active == True).order_by(Category.sort_order)
        )
    ).scalars().all()
    prods = (
        await session.execute(
            select(Product).where(Product.is_active == True).order_by(Product.sort_order, Product.id)
        )
    ).scalars().all()
    return CatalogOut(
        categories=[CategoryOut.model_validate(c, from_attributes=True) for c in cats],
        products=[ProductOut.model_validate(p, from_attributes=True) for p in prods],
    )


@router.get("/me", response_model=MeOut)
async def me(
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    auth = await _auth(x_init_data)
    user = await get_or_create_user(session, auth["user"])
    await session.commit()
    return MeOut(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        balance=user.balance,
        cashback=user.cashback,
        is_admin=is_admin(user.id),
    )


@router.post("/orders", response_model=OrderOut)
async def create_order_endpoint(
    body: OrderCreateIn,
    session: AsyncSession = Depends(get_session),
):
    auth = await _auth(body.init_data)
    s = get_settings()

    user = await get_or_create_user(session, auth["user"])
    if user.is_banned:
        raise HTTPException(403, "user banned")

    product = await session.get(Product, body.product_id)
    if not product or not product.is_active or not product.in_stock:
        raise HTTPException(404, "product unavailable")

    try:
        method = PaymentMethod(body.payment_method)
    except ValueError:
        raise HTTPException(400, "bad payment_method")

    try:
        order, _ = await create_order(session, user, product, body.quantity, method, body.promo_code)
    except InvalidPromoError as e:
        raise HTTPException(400, f"Промокод: {e}")
    await session.flush()

    return_url = f"{s.webapp_url}/orders/{order.id}"
    desc = f"BUTA STORE: {product.name} x{body.quantity}"

    if method == PaymentMethod.PLATEGA:
        try:
            inv = await PlategaClient().create_invoice(
                order_id=order.id,
                user_tg_id=user.id,
                amount=order.amount,
                description=desc,
                return_url=return_url,
            )
        except Exception as e:
            await session.rollback()
            raise HTTPException(502, f"platega: {e}")
        order.payment_id = inv["payment_id"]
        order.payment_url = inv["payment_url"]
    elif method == PaymentMethod.CRYPTOBOT:
        try:
            inv = await CryptoBotClient().create_invoice(
                order.id, order.amount, desc, return_url
            )
        except Exception as e:
            await session.rollback()
            raise HTTPException(502, f"cryptobot: {e}")
        order.payment_id = inv["payment_id"]
        order.payment_url = inv["payment_url"]
    else:
        raise HTTPException(400, "unsupported method")

    await session.commit()
    return OrderOut(
        id=order.id,
        status=order.status,
        amount=order.amount,
        payment_url=order.payment_url,
        payment_method=order.payment_method,
        created_at=order.created_at,
    )


@router.get("/orders", response_model=list[OrderListOut])
async def my_orders(
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    auth = await _auth(x_init_data)
    user_id = auth["user"]["id"]
    rows = (
        await session.execute(
            select(Order, Product)
            .join(Product, Product.id == Order.product_id)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(50)
        )
    ).all()
    return [
        OrderListOut(
            id=o.id,
            status=o.status,
            amount=o.amount,
            product_name=p.name,
            created_at=o.created_at,
            delivered_payload=o.delivered_payload if o.status == OrderStatus.DELIVERED else None,
        )
        for o, p in rows
    ]
