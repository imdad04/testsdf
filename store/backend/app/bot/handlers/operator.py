"""Operator flow: takes order, pastes key, marks delivered."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import get_settings
from app.models import Order
from app.services.orders import operator_deliver, operator_refund, operator_take

router = Router(name="operator")


class DeliverStates(StatesGroup):
    waiting_payload = State()


def _is_operator(uid: int) -> bool:
    s = get_settings()
    return uid == s.operator_chat_id or uid in s.admin_id_set


@router.callback_query(F.data.startswith("op:take:"))
async def cb_take(cq: CallbackQuery, sessionmaker: async_sessionmaker) -> None:
    if not _is_operator(cq.from_user.id):
        await cq.answer("Только для оператора", show_alert=True)
        return
    order_id = int(cq.data.split(":")[2])
    async with sessionmaker() as session:
        order = await operator_take(session, order_id, cq.from_user.id)
    if not order:
        await cq.answer("Заказ уже взят или не найден", show_alert=True)
        return
    await cq.answer(f"Взял #{order_id}")
    await cq.message.reply(
        f"📌 Заказ #{order_id} назначен на @{cq.from_user.username or cq.from_user.id}.\n"
        f"После покупки — пришли ключ ответом на это сообщение командой:\n"
        f"<code>/key {order_id} ТУТ_КЛЮЧ</code>"
    )


@router.callback_query(F.data.startswith("op:done:"))
async def cb_done(cq: CallbackQuery, state: FSMContext) -> None:
    if not _is_operator(cq.from_user.id):
        await cq.answer("Только для оператора", show_alert=True)
        return
    order_id = int(cq.data.split(":")[2])
    await state.set_state(DeliverStates.waiting_payload)
    await state.update_data(order_id=order_id)
    await cq.message.reply(
        f"Отправь ключ/код для заказа #{order_id} следующим сообщением.\n"
        f"(или /cancel чтобы отменить)"
    )
    await cq.answer()


@router.message(DeliverStates.waiting_payload)
async def receive_payload(message: Message, state: FSMContext, bot, sessionmaker: async_sessionmaker) -> None:
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.reply("Отменено.")
        return
    data = await state.get_data()
    order_id = data["order_id"]
    payload = (message.text or "").strip()
    if not payload:
        await message.reply("Пусто, пришли текстом.")
        return
    async with sessionmaker() as session:
        order = await operator_deliver(session, bot, order_id, message.from_user.id, payload)
    await state.clear()
    if order:
        await message.reply(f"✅ Заказ #{order_id} доставлен клиенту.")
    else:
        await message.reply("Не нашёл заказ или он не в статусе оплаченного.")


@router.message(F.text.regexp(r"^/key\s+\d+\s+.+"))
async def cmd_key(message: Message, bot, sessionmaker: async_sessionmaker) -> None:
    if not _is_operator(message.from_user.id):
        return
    parts = message.text.split(None, 2)
    order_id = int(parts[1])
    payload = parts[2]
    async with sessionmaker() as session:
        order = await operator_deliver(session, bot, order_id, message.from_user.id, payload)
    if order:
        await message.reply(f"✅ Заказ #{order_id} доставлен.")
    else:
        await message.reply("Не нашёл заказ.")


@router.callback_query(F.data.startswith("op:refund:"))
async def cb_refund(cq: CallbackQuery, bot, sessionmaker: async_sessionmaker) -> None:
    if not _is_operator(cq.from_user.id):
        await cq.answer("Только для оператора", show_alert=True)
        return
    order_id = int(cq.data.split(":")[2])
    async with sessionmaker() as session:
        order = await operator_refund(session, bot, order_id, cq.from_user.id)
    if order:
        await cq.answer(f"Возврат #{order_id}")
        await cq.message.reply(f"❌ Заказ #{order_id} помечен возвратом, клиент уведомлён.")
    else:
        await cq.answer("Не получилось", show_alert=True)
