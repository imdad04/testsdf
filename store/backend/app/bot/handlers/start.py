from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from app.config import get_settings

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    s = get_settings()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🛒 Открыть магазин",
                web_app=WebAppInfo(url=s.webapp_url),
            )],
            [InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders")],
            [InlineKeyboardButton(text="🆘 Поддержка", url=f"tg://user?id={list(s.admin_id_set)[0]}" if s.admin_id_set else "https://t.me/")],
        ]
    )
    await message.answer(
        f"<b>Добро пожаловать в BUTA STORE</b>\n\n"
        f"Подписки, ключи, цифровые товары.\n"
        f"Жми кнопку ниже — выбирай и плати в пару тапов.",
        reply_markup=kb,
    )
