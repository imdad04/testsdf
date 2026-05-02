"""Initial categories + sample products. Idempotent: safe to run multiple times."""

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Category, Product

CATEGORIES = [
    {"slug": "games", "name": "Игры", "icon": "🎮", "sort_order": 1},
    {"slug": "subscriptions", "name": "Подписки", "icon": "▶️", "sort_order": 2},
    {"slug": "soft", "name": "Софт", "icon": "💿", "sort_order": 3},
    {"slug": "other", "name": "Другое", "icon": "✨", "sort_order": 4},
]

PRODUCTS = [
    {
        "category_slug": "subscriptions",
        "name": "Spotify Premium",
        "subtitle": "1 месяц",
        "price": Decimal("199"),
        "icon_url": "https://upload.wikimedia.org/wikipedia/commons/1/19/Spotify_logo_without_text.svg",
        "sort_order": 1,
    },
    {
        "category_slug": "subscriptions",
        "name": "YouTube Premium",
        "subtitle": "1 месяц",
        "price": Decimal("169"),
        "icon_url": "https://upload.wikimedia.org/wikipedia/commons/0/09/YouTube_full-color_icon_%282017%29.svg",
        "sort_order": 2,
    },
    {
        "category_slug": "subscriptions",
        "name": "Discord Nitro",
        "subtitle": "1 месяц",
        "price": Decimal("139"),
        "icon_url": "https://upload.wikimedia.org/wikipedia/commons/4/4f/Discord_Logo_sans_text.svg",
        "sort_order": 3,
    },
]


async def main():
    async with SessionLocal() as session:
        # categories
        existing = {c.slug for c in (await session.execute(select(Category))).scalars()}
        slug_to_id: dict[str, int] = {}
        for c in CATEGORIES:
            if c["slug"] not in existing:
                cat = Category(**c)
                session.add(cat)
                await session.flush()
                slug_to_id[c["slug"]] = cat.id
        await session.commit()

        cats = (await session.execute(select(Category))).scalars().all()
        slug_to_id = {c.slug: c.id for c in cats}

        # products
        existing_names = {p.name for p in (await session.execute(select(Product))).scalars()}
        for p in PRODUCTS:
            if p["name"] in existing_names:
                continue
            session.add(
                Product(
                    name=p["name"],
                    subtitle=p["subtitle"],
                    price=p["price"],
                    icon_url=p["icon_url"],
                    sort_order=p.get("sort_order", 0),
                    category_id=slug_to_id[p["category_slug"]],
                )
            )
        await session.commit()
    print("Seed done.")


if __name__ == "__main__":
    asyncio.run(main())
