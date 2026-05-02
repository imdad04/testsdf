"""Operator notifications and client status updates."""

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import get_settings
from app.models import Order, Product, User


def operator_card_text(order: Order, product: Product, user: User) -> str:
    username = f"@{user.username}" if user.username else f"id:{user.id}"
    src_link = f'<a href="{product.source_url}">КУПИТЬ ЗДЕСЬ</a>' if product.source_url else "источник не указан"
    note = f"\n📝 <i>{product.source_note}</i>" if product.source_note else ""
    return (
        f"🆕 <b>Заказ #{order.id}</b>\n"
        f"👤 {username}\n\n"
        f"🛒 <b>{product.name}</b>\n"
        f"   {product.subtitle or ''}\n"
        f"   x{order.quantity}\n\n"
        f"💰 Сумма: <b>{order.amount} ₽</b>\n"
        f"💳 Метод: {order.payment_method}\n\n"
        f"🔗 Источник: {src_link}{note}"
    )


def operator_card_kb(order_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✋ Взять", callback_data=f"op:take:{order_id}")
    b.button(text="✅ Готово", callback_data=f"op:done:{order_id}")
    b.button(text="❌ Отказ + возврат", callback_data=f"op:refund:{order_id}")
    b.adjust(2, 1)
    return b.as_markup()


async def notify_operator(bot: Bot, order: Order, product: Product, user: User) -> int:
    """Send order card to operator chat. Returns message id."""
    chat_id = get_settings().operator_chat_id
    msg = await bot.send_message(
        chat_id,
        operator_card_text(order, product, user),
        reply_markup=operator_card_kb(order.id),
        disable_web_page_preview=False,
    )
    return msg.message_id


async def notify_client_processing(bot: Bot, user_id: int, order_id: int) -> None:
    """Reassuring message — does NOT mention operator."""
    await bot.send_message(
        user_id,
        f"✅ Оплата заказа <b>#{order_id}</b> принята.\n\n"
        f"⏳ Ваш заказ обрабатывается. Товар придёт сюда в течение 2 минут.",
    )


async def notify_client_delivered(bot: Bot, user_id: int, order_id: int, payload: str) -> None:
    await bot.send_message(
        user_id,
        f"🎁 <b>Заказ #{order_id} готов!</b>\n\n"
        f"<code>{payload}</code>\n\n"
        f"Спасибо за покупку! Если что-то не так — напишите в поддержку.",
    )


async def notify_client_refund(bot: Bot, user_id: int, order_id: int) -> None:
    await bot.send_message(
        user_id,
        f"⚠️ К сожалению, по заказу <b>#{order_id}</b> оформлен возврат.\n"
        f"Средства вернутся на способ оплаты в течение нескольких часов.",
    )


async def notify_admins(bot: Bot, text: str) -> None:
    for admin_id in get_settings().admin_id_set:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass
