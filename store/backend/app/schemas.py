from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


class CategoryOut(BaseModel):
    id: int
    slug: str
    name: str
    icon: str | None = None


class ProductOut(BaseModel):
    id: int
    category_id: int
    name: str
    subtitle: str | None = None
    description: str | None = None
    price: Decimal
    icon_url: str | None = None
    in_stock: bool


class CatalogOut(BaseModel):
    categories: list[CategoryOut]
    products: list[ProductOut]


class OrderCreateIn(BaseModel):
    init_data: str
    product_id: int
    quantity: int = Field(default=1, ge=1, le=10)
    payment_method: str  # platega | cryptobot
    promo_code: str | None = None


class OrderOut(BaseModel):
    id: int
    status: str
    amount: Decimal
    payment_url: str | None
    payment_method: str
    created_at: datetime


class OrderListOut(BaseModel):
    id: int
    status: str
    amount: Decimal
    product_name: str
    created_at: datetime
    delivered_payload: str | None = None


class MeOut(BaseModel):
    id: int
    username: str | None
    first_name: str | None
    balance: Decimal
    cashback: Decimal
    is_admin: bool


class PromoCheckIn(BaseModel):
    init_data: str
    code: str
    product_id: int
    quantity: int = Field(default=1, ge=1, le=10)


class PromoCheckOut(BaseModel):
    code: str
    discount_pct: int
    discount_fixed: Decimal
    discount: Decimal
    amount: Decimal
    base: Decimal
