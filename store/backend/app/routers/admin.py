"""Admin REST API consumed by the WebApp /admin section.

Auth: Telegram initData + admin id check (header X-Init-Data).
"""

from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.bot_singleton import get_bot
from app.db import get_session
from app.models import (
    Category,
    Operator,
    Order,
    OrderStatus,
    Product,
    Promo,
    User,
)
from app.security import AuthError, is_admin, parse_init_data
from app.services.orders import operator_refund

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


# ============== Stats ==============
@router.get("/stats")
async def stats(
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    paid_statuses = [OrderStatus.PAID, OrderStatus.IN_PROGRESS, OrderStatus.DELIVERED]
    revenue = (
        await session.execute(
            select(func.coalesce(func.sum(Order.amount), 0)).where(Order.status.in_(paid_statuses))
        )
    ).scalar()
    today = datetime.utcnow().date()
    revenue_today = (
        await session.execute(
            select(func.coalesce(func.sum(Order.amount), 0)).where(
                Order.status.in_(paid_statuses),
                Order.paid_at >= today,
            )
        )
    ).scalar()
    orders = (await session.execute(select(func.count(Order.id)))).scalar()
    delivered = (
        await session.execute(
            select(func.count(Order.id)).where(Order.status == OrderStatus.DELIVERED)
        )
    ).scalar()
    pending = (
        await session.execute(
            select(func.count(Order.id)).where(Order.status.in_([OrderStatus.PAID, OrderStatus.IN_PROGRESS]))
        )
    ).scalar()
    users = (await session.execute(select(func.count(User.id)))).scalar()
    return {
        "revenue": float(revenue or 0),
        "revenue_today": float(revenue_today or 0),
        "orders": orders,
        "delivered": delivered,
        "pending": pending,
        "users": users,
    }


# ============== Products ==============
class ProductIn(BaseModel):
    category_id: int
    name: str
    subtitle: str | None = None
    description: str | None = None
    price: Decimal
    icon_url: str | None = None
    source_url: str | None = None
    source_note: str | None = None
    is_active: bool = True
    in_stock: bool = True
    sort_order: int = 0


@router.get("/products")
async def list_products(
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    rows = (await session.execute(select(Product).order_by(Product.id.desc()))).scalars().all()
    return [
        {
            "id": p.id,
            "category_id": p.category_id,
            "name": p.name,
            "subtitle": p.subtitle,
            "description": p.description,
            "price": float(p.price),
            "icon_url": p.icon_url,
            "source_url": p.source_url,
            "source_note": p.source_note,
            "is_active": p.is_active,
            "in_stock": p.in_stock,
            "sort_order": p.sort_order,
        }
        for p in rows
    ]


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


# ============== Categories ==============
class CategoryIn(BaseModel):
    slug: str
    name: str
    icon: str | None = None
    sort_order: int = 0
    is_active: bool = True


@router.get("/categories")
async def list_categories(
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    rows = (await session.execute(select(Category).order_by(Category.sort_order, Category.id))).scalars().all()
    return [
        {
            "id": c.id,
            "slug": c.slug,
            "name": c.name,
            "icon": c.icon,
            "sort_order": c.sort_order,
            "is_active": c.is_active,
        }
        for c in rows
    ]


@router.post("/categories")
async def create_category(
    body: CategoryIn,
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    c = Category(**body.model_dump())
    session.add(c)
    await session.commit()
    return {"id": c.id}


@router.put("/categories/{cat_id}")
async def update_category(
    cat_id: int,
    body: CategoryIn,
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    c = await session.get(Category, cat_id)
    if not c:
        raise HTTPException(404, "not found")
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    await session.commit()
    return {"ok": True}


@router.delete("/categories/{cat_id}")
async def delete_category(
    cat_id: int,
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    c = await session.get(Category, cat_id)
    if not c:
        raise HTTPException(404, "not found")
    c.is_active = False
    await session.commit()
    return {"ok": True}


# ============== Orders ==============
@router.get("/orders")
async def list_orders(
    status: str | None = None,
    limit: int = 50,
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    q = (
        select(Order, Product)
        .join(Product, Product.id == Order.product_id)
        .order_by(Order.created_at.desc())
        .limit(min(limit, 200))
    )
    if status:
        q = q.where(Order.status == status)
    rows = (await session.execute(q)).all()
    return [
        {
            "id": o.id,
            "user_id": o.user_id,
            "product_name": p.name,
            "amount": float(o.amount),
            "status": o.status,
            "payment_method": o.payment_method,
            "created_at": o.created_at.isoformat(),
            "paid_at": o.paid_at.isoformat() if o.paid_at else None,
            "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
            "delivered_payload": o.delivered_payload,
            "operator_id": o.operator_id,
        }
        for o, p in rows
    ]


@router.post("/orders/{order_id}/refund")
async def admin_refund(
    order_id: int,
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    uid = await _admin(x_init_data)
    bot = get_bot()
    order = await operator_refund(session, bot, order_id, uid)
    if not order:
        raise HTTPException(404, "not found or wrong status")
    return {"ok": True}


# ============== Promos ==============
class PromoIn(BaseModel):
    code: str
    discount_pct: int = Field(default=0, ge=0, le=100)
    discount_fixed: Decimal = Decimal("0")
    max_uses: int | None = None
    days: int | None = None
    is_active: bool = True


@router.get("/promos")
async def list_promos(
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    rows = (await session.execute(select(Promo).order_by(Promo.id.desc()))).scalars().all()
    return [
        {
            "id": p.id,
            "code": p.code,
            "discount_pct": p.discount_pct,
            "discount_fixed": float(p.discount_fixed),
            "max_uses": p.max_uses,
            "used_count": p.used_count,
            "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            "is_active": p.is_active,
        }
        for p in rows
    ]


@router.post("/promos")
async def create_promo(
    body: PromoIn,
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    code = body.code.upper().strip()
    existing = (await session.execute(select(Promo).where(Promo.code == code))).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "code already exists")
    expires = datetime.utcnow() + timedelta(days=body.days) if body.days else None
    p = Promo(
        code=code,
        discount_pct=body.discount_pct,
        discount_fixed=body.discount_fixed,
        max_uses=body.max_uses,
        expires_at=expires,
        is_active=body.is_active,
    )
    session.add(p)
    await session.commit()
    return {"id": p.id}


@router.delete("/promos/{promo_id}")
async def delete_promo(
    promo_id: int,
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    p = await session.get(Promo, promo_id)
    if not p:
        raise HTTPException(404, "not found")
    p.is_active = False
    await session.commit()
    return {"ok": True}


# ============== Operators ==============
class OperatorIn(BaseModel):
    id: int
    name: str | None = None
    is_active: bool = True


@router.get("/operators")
async def list_operators(
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    rows = (await session.execute(select(Operator).order_by(Operator.id))).scalars().all()
    return [{"id": o.id, "name": o.name, "is_active": o.is_active} for o in rows]


@router.post("/operators")
async def create_operator(
    body: OperatorIn,
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    existing = await session.get(Operator, body.id)
    if existing:
        existing.name = body.name or existing.name
        existing.is_active = body.is_active
    else:
        session.add(Operator(id=body.id, name=body.name, is_active=body.is_active))
    await session.commit()
    return {"ok": True}


@router.delete("/operators/{op_id}")
async def delete_operator(
    op_id: int,
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    o = await session.get(Operator, op_id)
    if not o:
        raise HTTPException(404, "not found")
    o.is_active = False
    await session.commit()
    return {"ok": True}


# ============== Broadcast ==============
class BroadcastIn(BaseModel):
    text: str


@router.post("/broadcast")
async def broadcast(
    body: BroadcastIn,
    x_init_data: str = Header(None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    await _admin(x_init_data)
    bot = get_bot()
    user_ids = (
        await session.execute(select(User.id).where(User.is_banned == False))
    ).scalars().all()
    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, body.text)
            sent += 1
        except Exception:
            failed += 1
    return {"sent": sent, "failed": failed}


# ============== Backup trigger ==============
@router.post("/backup")
async def trigger_backup(
    x_init_data: str = Header(None, alias="X-Init-Data"),
):
    uid = await _admin(x_init_data)
    from app.services.backup import make_backup
    bot = get_bot()
    path = await make_backup(bot, manual=True, requested_by=uid)
    return {"path": path}
