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

from datetime import datetime, timedelta

from app.config import get_settings
from app.models import Category, Operator, Order, OrderStatus, Product, Promo, User

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


# ============== Категории ==============
@router.callback_query(F.data == "adm:cats")
async def cb_cats(cq: CallbackQuery, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(cq.from_user.id):
        await cq.answer()
        return
    async with sessionmaker() as session:
        cats = (await session.execute(select(Category).order_by(Category.sort_order, Category.id))).scalars().all()
    if cats:
        lines = ["🗂 <b>Категории</b>\n"]
        for c in cats:
            mark = "✅" if c.is_active else "⛔"
            lines.append(f"{mark} #{c.id} {c.icon or '✨'} {c.name} <i>({c.slug})</i>")
    else:
        lines = ["🗂 <b>Категории</b>\n", "<i>Пока ни одной категории.</i>"]
    lines.append(
        "\n<b>Команды:</b>\n"
        "<code>/addcat slug Название 🎮</code> — создать\n"
        "<code>/delcat &lt;id&gt;</code> — деактивировать"
    )
    await cq.message.edit_text("\n".join(lines), reply_markup=admin_menu_kb())
    await cq.answer()


@router.message(Command("delcat"))
async def cmd_delcat(message: Message, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: <code>/delcat &lt;id&gt;</code>")
        return
    try:
        cid = int(parts[1])
    except ValueError:
        return
    async with sessionmaker() as session:
        c = await session.get(Category, cid)
        if not c:
            await message.answer("Не найдена")
            return
        c.is_active = False
        await session.commit()
    await message.answer(f"✅ Категория #{cid} деактивирована")


# ============== Заказы ==============
_ORDER_STATUS_RU = {
    "pending": "⏳ Ожидает оплаты",
    "paid": "💰 Оплачен",
    "in_progress": "🔧 В работе",
    "delivered": "✅ Доставлен",
    "cancelled": "❌ Отменён",
    "refunded": "↩️ Возврат",
}


@router.callback_query(F.data == "adm:orders")
async def cb_orders(cq: CallbackQuery, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(cq.from_user.id):
        await cq.answer()
        return
    async with sessionmaker() as session:
        rows = (
            await session.execute(
                select(Order, Product)
                .join(Product, Product.id == Order.product_id)
                .order_by(Order.created_at.desc())
                .limit(15)
            )
        ).all()
    if rows:
        lines = ["📦 <b>Последние заказы</b>\n"]
        for o, p in rows:
            st = _ORDER_STATUS_RU.get(o.status, o.status)
            lines.append(f"#{o.id} · {p.name} · {o.amount}₽ · {st}\n  <i>от user {o.user_id}, {o.created_at:%d.%m %H:%M}</i>")
    else:
        lines = ["📦 <b>Последние заказы</b>\n", "<i>Пока нет.</i>"]
    lines.append(
        "\n<b>Команды:</b>\n"
        "<code>/order &lt;id&gt;</code> — детали заказа\n"
        "<code>/refund &lt;id&gt;</code> — пометить возвратом"
    )
    await cq.message.edit_text("\n".join(lines), reply_markup=admin_menu_kb())
    await cq.answer()


@router.message(Command("order"))
async def cmd_order(message: Message, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: <code>/order &lt;id&gt;</code>")
        return
    try:
        oid = int(parts[1])
    except ValueError:
        return
    async with sessionmaker() as session:
        o = await session.get(Order, oid)
        if not o:
            await message.answer("Не найден")
            return
        p = await session.get(Product, o.product_id)
    st = _ORDER_STATUS_RU.get(o.status, o.status)
    await message.answer(
        f"📦 <b>Заказ #{o.id}</b>\n"
        f"Товар: <b>{p.name}</b> x{o.quantity}\n"
        f"Сумма: <b>{o.amount} ₽</b>\n"
        f"Статус: {st}\n"
        f"Метод: {o.payment_method}\n"
        f"User: <code>{o.user_id}</code>\n"
        f"Создан: {o.created_at:%d.%m.%Y %H:%M}\n"
        f"Оплачен: {o.paid_at:%d.%m.%Y %H:%M}" if o.paid_at else f"Оплата: ещё не пришла"
    )


@router.message(Command("refund"))
async def cmd_refund(message: Message, bot, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        return
    try:
        oid = int(parts[1])
    except ValueError:
        return
    from app.services.orders import operator_refund
    async with sessionmaker() as session:
        o = await operator_refund(session, bot, oid, message.from_user.id)
    await message.answer(f"↩️ Заказ #{oid} помечен возвратом" if o else "Не найден или уже не в статусе для возврата")


# ============== Операторы ==============
@router.callback_query(F.data == "adm:ops")
async def cb_ops(cq: CallbackQuery, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(cq.from_user.id):
        await cq.answer()
        return
    async with sessionmaker() as session:
        ops = (await session.execute(select(Operator).order_by(Operator.id))).scalars().all()
    s = get_settings()
    if ops:
        lines = ["👥 <b>Операторы</b>\n"]
        for o in ops:
            mark = "✅" if o.is_active else "⛔"
            lines.append(f"{mark} <code>{o.id}</code> {o.name or ''}")
    else:
        lines = ["👥 <b>Операторы</b>\n", "<i>Пока нет операторов в БД.</i>"]
    lines.append(f"\n<b>Главный оператор</b> (из .env): <code>{s.operator_chat_id}</code>")
    lines.append(
        "\n<b>Команды:</b>\n"
        "<code>/addop &lt;telegram_id&gt; &lt;имя&gt;</code> — добавить\n"
        "<code>/delop &lt;telegram_id&gt;</code> — отключить"
    )
    await cq.message.edit_text("\n".join(lines), reply_markup=admin_menu_kb())
    await cq.answer()


@router.message(Command("addop"))
async def cmd_addop(message: Message, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split(None, 2)
    if len(parts) < 2:
        await message.answer("Использование: <code>/addop &lt;telegram_id&gt; [имя]</code>")
        return
    try:
        op_id = int(parts[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    name = parts[2] if len(parts) > 2 else None
    async with sessionmaker() as session:
        existing = await session.get(Operator, op_id)
        if existing:
            existing.is_active = True
            existing.name = name or existing.name
        else:
            session.add(Operator(id=op_id, name=name, is_active=True))
        await session.commit()
    await message.answer(f"✅ Оператор {op_id} добавлен/активирован")


@router.message(Command("delop"))
async def cmd_delop(message: Message, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        return
    try:
        op_id = int(parts[1])
    except ValueError:
        return
    async with sessionmaker() as session:
        o = await session.get(Operator, op_id)
        if o:
            o.is_active = False
            await session.commit()
    await message.answer(f"⛔ Оператор {op_id} отключён")


# ============== Промокоды ==============
@router.callback_query(F.data == "adm:promos")
async def cb_promos(cq: CallbackQuery, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(cq.from_user.id):
        await cq.answer()
        return
    async with sessionmaker() as session:
        promos = (await session.execute(select(Promo).order_by(Promo.id.desc()).limit(20))).scalars().all()
    if promos:
        lines = ["🎟 <b>Промокоды</b>\n"]
        for p in promos:
            mark = "✅" if p.is_active else "⛔"
            disc = f"{p.discount_pct}%" if p.discount_pct else f"{p.discount_fixed}₽"
            uses = f"{p.used_count}/{p.max_uses}" if p.max_uses else f"{p.used_count}/∞"
            exp = f", до {p.expires_at:%d.%m}" if p.expires_at else ""
            lines.append(f"{mark} <code>{p.code}</code> · -{disc} · {uses}{exp}")
    else:
        lines = ["🎟 <b>Промокоды</b>\n", "<i>Пока ни одного.</i>"]
    lines.append(
        "\n<b>Команды:</b>\n"
        "<code>/addpromo КОД 10 100 30</code>\n"
        "<i>= скидка 10%, лимит 100 активаций, срок 30 дней</i>\n"
        "<code>/addpromofix КОД 50 100 30</code>\n"
        "<i>= скидка 50₽ (фиксированная)</i>\n"
        "<code>/delpromo КОД</code> — отключить"
    )
    await cq.message.edit_text("\n".join(lines), reply_markup=admin_menu_kb())
    await cq.answer()


@router.message(Command("addpromo"))
async def cmd_addpromo(message: Message, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: <code>/addpromo КОД процент [лимит] [дней]</code>")
        return
    code = parts[1].upper()
    try:
        pct = int(parts[2])
        max_uses = int(parts[3]) if len(parts) > 3 else None
        days = int(parts[4]) if len(parts) > 4 else None
    except ValueError:
        await message.answer("Цифры некорректны")
        return
    expires = datetime.utcnow() + timedelta(days=days) if days else None
    async with sessionmaker() as session:
        existing = (await session.execute(select(Promo).where(Promo.code == code))).scalar_one_or_none()
        if existing:
            await message.answer(f"Промокод {code} уже существует")
            return
        session.add(Promo(code=code, discount_pct=pct, max_uses=max_uses, expires_at=expires, is_active=True))
        await session.commit()
    await message.answer(f"✅ Промокод <code>{code}</code> создан: -{pct}%")


@router.message(Command("addpromofix"))
async def cmd_addpromofix(message: Message, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: <code>/addpromofix КОД сумма_₽ [лимит] [дней]</code>")
        return
    code = parts[1].upper()
    try:
        fixed = Decimal(parts[2])
        max_uses = int(parts[3]) if len(parts) > 3 else None
        days = int(parts[4]) if len(parts) > 4 else None
    except (ValueError, InvalidOperation):
        await message.answer("Цифры некорректны")
        return
    expires = datetime.utcnow() + timedelta(days=days) if days else None
    async with sessionmaker() as session:
        existing = (await session.execute(select(Promo).where(Promo.code == code))).scalar_one_or_none()
        if existing:
            await message.answer(f"Промокод {code} уже существует")
            return
        session.add(Promo(code=code, discount_fixed=fixed, max_uses=max_uses, expires_at=expires, is_active=True))
        await session.commit()
    await message.answer(f"✅ Промокод <code>{code}</code> создан: -{fixed}₽")


@router.message(Command("delpromo"))
async def cmd_delpromo(message: Message, sessionmaker: async_sessionmaker) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        return
    code = parts[1].upper()
    async with sessionmaker() as session:
        p = (await session.execute(select(Promo).where(Promo.code == code))).scalar_one_or_none()
        if p:
            p.is_active = False
            await session.commit()
    await message.answer(f"⛔ Промокод {code} отключён")
