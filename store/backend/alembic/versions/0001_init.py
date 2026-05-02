"""init schema

Revision ID: 0001_init
Revises:
Create Date: 2026-05-02

"""
from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("username", sa.String(64)),
        sa.Column("first_name", sa.String(64)),
        sa.Column("language_code", sa.String(8)),
        sa.Column("balance", sa.Numeric(12, 2), server_default="0"),
        sa.Column("cashback", sa.Numeric(12, 2), server_default="0"),
        sa.Column("is_banned", sa.Boolean, server_default=sa.text("false")),
        sa.Column("referrer_id", sa.BigInteger, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(64), unique=True, nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("icon", sa.String(32)),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("subtitle", sa.String(128)),
        sa.Column("description", sa.Text),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("icon_url", sa.String(512)),
        sa.Column("source_url", sa.String(512)),
        sa.Column("source_note", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("in_stock", sa.Boolean, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "promos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(32), unique=True, nullable=False),
        sa.Column("discount_pct", sa.Integer, server_default="0"),
        sa.Column("discount_fixed", sa.Numeric(12, 2), server_default="0"),
        sa.Column("max_uses", sa.Integer),
        sa.Column("used_count", sa.Integer, server_default="0"),
        sa.Column("expires_at", sa.DateTime),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer, server_default="1"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("promo_id", sa.Integer, sa.ForeignKey("promos.id")),
        sa.Column("status", sa.String(16), server_default="pending"),
        sa.Column("payment_method", sa.String(16), nullable=False),
        sa.Column("payment_id", sa.String(128)),
        sa.Column("payment_url", sa.String(512)),
        sa.Column("operator_id", sa.BigInteger),
        sa.Column("operator_msg_id", sa.BigInteger),
        sa.Column("delivered_payload", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("paid_at", sa.DateTime),
        sa.Column("delivered_at", sa.DateTime),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_table(
        "operators",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("name", sa.String(64)),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("actor_id", sa.BigInteger),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target", sa.String(128)),
        sa.Column("payload", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    for t in ("audit_log", "operators", "orders", "promos", "products", "categories", "users"):
        op.drop_table(t)
