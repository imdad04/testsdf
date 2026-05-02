"""Admin commands inside the bot itself.

Quick CRUD for products without leaving Telegram. The full admin panel
lives in the WebApp, but day-to-day adding/editing happens here.
"""

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import get_settings
from app.models import Category, Operator, Order, OrderStatus, Product, User

router = Router(name="admin")


def _is_admin(uid: int) -> bool:
    return uid in get_settings().admin_id_set


def admin_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 Статистика", callback_data="adm:stats")
    b.button(text="🛒 Товары", callback_data="adm:products")
    b.button(text="🗂 Категории", callback_data="adm:cats")
    b.button(text="🎟 Промокоды", callback_data="adm:promos")
    b.button(text="📦 Заказы", callback_data="adm:orders")
    b.button(text="👥 Операторы", callback_data="adm:ops")
    b.button(text="📣 Рассылка", callback_data="adm:broadcast")
    b.button(text="💾 Бэкап сейчас", callback_data="adm:backup")
    b.adjust(2)
    return b.as_markup()


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    await message.answer("⚙️ <b>Админ-меню BUTA STORE</b>", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "adm:stats")
async def cb_stats(cq: CallbackQuery, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(cq.from_user.id):
        await cq.answer()
        return
    async with sessionmaker() as session:
        revenue = (
            await session.execute(
                select(func.coalesce(func.sum(Order.amount), 0)).where(
                    Order.status.in_([OrderStatus.PAID, OrderStatus.IN_PROGRESS, OrderStatus.DELIVERED])
                )
            )
        ).scalar()
        orders = (await session.execute(select(func.count(Order.id)))).scalar()
        users = (await session.execute(select(func.count(User.id)))).scalar()
        delivered = (
            await session.execute(
                select(func.count(Order.id)).where(Order.status == OrderStatus.DELIVERED)
            )
        ).scalar()
    await cq.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"💰 Выручка: <b>{revenue} ₽</b>\n"
        f"📦 Заказов: <b>{orders}</b>\n"
        f"   ✅ Доставлено: {delivered}\n"
        f"👥 Юзеров: <b>{users}</b>",
        reply_markup=admin_menu_kb(),
    )
    await cq.answer()


@router.callback_query(F.data == "adm:products")
async def cb_products(cq: CallbackQuery, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(cq.from_user.id):
        await cq.answer()
        return
    async with sessionmaker() as session:
        prods = (
            await session.execute(
                select(Product).where(Product.is_active == True).order_by(Product.id).limit(20)
            )
        ).scalars().all()
    lines = ["🛒 <b>Товары</b>\n"]
    for p in prods:
        mark = "✅" if p.in_stock else "⛔"
        lines.append(f"{mark} #{p.id} {p.name} — {p.price} ₽")
    lines.append("\nДобавить: /addproduct\nРедактировать: /editproduct &lt;id&gt;\nИсточник: /setsrc &lt;id&gt; &lt;url&gt;")
    await cq.message.edit_text("\n".join(lines), reply_markup=admin_menu_kb())
    await cq.answer()


# --- /addproduct FSM ---
class AddProduct(StatesGroup):
    name = State()
    category = State()
    subtitle = State()
    price = State()
    source_url = State()


@router.message(Command("addproduct"))
async def cmd_addproduct(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.set_state(AddProduct.name)
    await message.answer("1/5  Название товара? (например: Spotify Premium)")


@router.message(AddProduct.name)
async def ap_name(message: Message, state: FSMContext, sessionmaker: async_sessionmaker) -> None:
    await state.update_data(name=message.text.strip())
    async with sessionmaker() as session:
        cats = (await session.execute(select(Category).order_by(Category.id))).scalars().all()
    if not cats:
        await message.answer("Нет категорий. Сначала создай через /addcat")
        await state.clear()
        return
    cats_text = "\n".join(f"{c.id} — {c.name}" for c in cats)
    await state.set_state(AddProduct.category)
    await message.answer(f"2/5  ID категории?\n\n{cats_text}")


@router.message(AddProduct.category)
async def ap_cat(message: Message, state: FSMContext) -> None:
    try:
        await state.update_data(category_id=int(message.text.strip()))
    except ValueError:
        await message.answer("Введи число — ID категории")
        return
    await state.set_state(AddProduct.subtitle)
    await message.answer("3/5  Подзаголовок? (например: 1 месяц) или - чтобы пропустить")


@router.message(AddProduct.subtitle)
async def ap_sub(message: Message, state: FSMContext) -> None:
    sub = message.text.strip()
    await state.update_data(subtitle=None if sub == "-" else sub)
    await state.set_state(AddProduct.price)
    await message.answer("4/5  Цена в ₽? (например: 199)")


@router.message(AddProduct.price)
async def ap_price(message: Message, state: FSMContext) -> None:
    try:
        await state.update_data(price=Decimal(message.text.strip().replace(",", ".")))
    except (InvalidOperation, ValueError):
        await message.answer("Введи число")
        return
    await state.set_state(AddProduct.source_url)
    await message.answer("5/5  Ссылка где оператор купит этот товар? (полный URL) или - чтобы пропустить")


@router.message(AddProduct.source_url)
async def ap_src(message: Message, state: FSMContext, sessionmaker: async_sessionmaker) -> None:
    src = message.text.strip()
    data = await state.get_data()
    async with sessionmaker() as session:
        p = Product(
            name=data["name"],
            category_id=data["category_id"],
            subtitle=data.get("subtitle"),
            price=data["price"],
            source_url=None if src == "-" else src,
            is_active=True,
            in_stock=True,
        )
        session.add(p)
        await session.commit()
        pid = p.id
    await state.clear()
    await message.answer(f"✅ Создан товар #{pid}: {data['name']} — {data['price']} ₽")


@router.message(Command("setsrc"))
async def cmd_setsrc(message: Message, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split(None, 2)
    if len(parts) < 3:
        await message.answer("Использование: /setsrc &lt;product_id&gt; &lt;url&gt;")
        return
    try:
        pid = int(parts[1])
    except ValueError:
        await message.answer("ID должно быть числом")
        return
    url = parts[2]
    async with sessionmaker() as session:
        p = await session.get(Product, pid)
        if not p:
            await message.answer("Товар не найден")
            return
        p.source_url = url
        await session.commit()
    await message.answer(f"✅ Источник для #{pid} обновлён")


# --- /addcat ---
@router.message(Command("addcat"))
async def cmd_addcat(message: Message, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split(None, 3)
    if len(parts) < 3:
        await message.answer("Использование: /addcat &lt;slug&gt; &lt;name&gt; [icon-emoji]")
        return
    slug, name = parts[1], parts[2]
    icon = parts[3] if len(parts) > 3 else None
    async with sessionmaker() as session:
        c = Category(slug=slug, name=name, icon=icon)
        session.add(c)
        await session.commit()
    await message.answer(f"✅ Категория {name} создана")


# --- broadcast ---
class Broadcast(StatesGroup):
    text = State()


@router.callback_query(F.data == "adm:broadcast")
async def cb_broadcast(cq: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(cq.from_user.id):
        await cq.answer()
        return
    await state.set_state(Broadcast.text)
    await cq.message.answer("Пришли текст рассылки. /cancel чтобы отменить.")
    await cq.answer()


@router.message(Broadcast.text)
async def broadcast_send(message: Message, state: FSMContext, bot, sessionmaker: async_sessionmaker) -> None:
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("Отменено")
        return
    text = message.html_text
    await state.clear()
    async with sessionmaker() as session:
        users = (await session.execute(select(User.id).where(User.is_banned == False))).scalars().all()
    sent, failed = 0, 0
    for uid in users:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"📣 Рассылка завершена: ✅ {sent}  ❌ {failed}")


@router.message(Command("ban"))
async def cmd_ban(message: Message, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /ban &lt;user_id&gt;")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        return
    async with sessionmaker() as session:
        u = await session.get(User, uid)
        if not u:
            await message.answer("Юзер не найден")
            return
        u.is_banned = True
        await session.commit()
    await message.answer(f"🚫 {uid} забанен")


@router.message(Command("unban"))
async def cmd_unban(message: Message, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        return
    try:
        uid = int(parts[1])
    except ValueError:
        return
    async with sessionmaker() as session:
        u = await session.get(User, uid)
        if u:
            u.is_banned = False
            await session.commit()
    await message.answer(f"✅ {uid} разбанен")
