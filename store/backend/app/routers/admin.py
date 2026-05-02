"""Admin REST API for managing products / categories from a panel.

Auth: Telegram initData + admin id check.
The bot also exposes the same operations via /admin in the bot itself —
this router exists for the future web admin panel.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Category, Order, OrderStatus, Product, User
from app.security import AuthError, is_admin, parse_init_data

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def _admin(init_data: str | None) -> int:
    if not init_data:
        raise HTTPException(401, "missing initData")
    try:
        auth = parse_init_data(init_data)
    except AuthError as e:
        raise HTTPException(401, str(e))
    uid = auth["user"]["id"]
    if not is_admin(uid):
        raise HTTPException(403, "not admin")
    return uid


class ProductIn(BaseModel):
    category_id: int
    name: str
    subtitle: str | None = None
    description: str | None = None
    price: Decimal
    icon_url: str | None = None
    source_url: str | None = None
    source_note: str | None = None
    in_stock: bool = True
    sort_order: int = 0


@router.get("/stats")
async def stats(
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    paid_total = (
        await session.execute(
            select(func.coalesce(func.sum(Order.amount), 0)).where(
                Order.status.in_([OrderStatus.PAID, OrderStatus.IN_PROGRESS, OrderStatus.DELIVERED])
            )
        )
    ).scalar()
    orders_count = (await session.execute(select(func.count(Order.id)))).scalar()
    users_count = (await session.execute(select(func.count(User.id)))).scalar()
    return {
        "revenue": float(paid_total or 0),
        "orders": orders_count,
        "users": users_count,
    }


@router.post("/products")
async def create_product(
    body: ProductIn,
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    p = Product(**body.model_dump())
    session.add(p)
    await session.commit()
    return {"id": p.id}


@router.put("/products/{product_id}")
async def update_product(
    product_id: int,
    body: ProductIn,
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    p = await session.get(Product, product_id)
    if not p:
        raise HTTPException(404, "not found")
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    await session.commit()
    return {"ok": True}


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    p = await session.get(Product, product_id)
    if not p:
        raise HTTPException(404, "not found")
    p.is_active = False
    await session.commit()
    return {"ok": True}
