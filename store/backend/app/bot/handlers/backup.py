from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.config import get_settings
from app.services.backup import make_backup, restore_backup

router = Router(name="backup")


def _is_admin(uid: int) -> bool:
    return uid in get_settings().admin_id_set


@router.message(Command("backup"))
async def cmd_backup(message: Message, bot) -> None:
    if not _is_admin(message.from_user.id):
        return
    await message.answer("⏳ Делаю бэкап...")
    try:
        path = await make_backup(bot, manual=True, requested_by=message.from_user.id)
        await message.answer(f"✅ Бэкап готов: <code>{path}</code>")
    except Exception as e:
        await message.answer(f"❌ Ошибка: <code>{e}</code>")


@router.callback_query(F.data == "adm:backup")
async def cb_backup(cq: CallbackQuery, bot) -> None:
    if not _is_admin(cq.from_user.id):
        await cq.answer()
        return
    await cq.answer("Делаю бэкап...")
    try:
        path = await make_backup(bot, manual=True, requested_by=cq.from_user.id)
        await cq.message.answer(f"✅ Бэкап готов: <code>{path}</code>")
    except Exception as e:
        await cq.message.answer(f"❌ Ошибка: <code>{e}</code>")


@router.message(Command("restore"))
async def cmd_restore(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "Использование: пришли файл бэкапа в чат, ответь на него командой /restore"
        )
        return
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.answer("Ответь /restore на сообщение с файлом бэкапа.")
        return
    await message.answer("⏳ Восстанавливаю...")
    try:
        await restore_backup(message.bot, message.reply_to_message.document)
        await message.answer("✅ Восстановлено")
    except Exception as e:
        await message.answer(f"❌ Ошибка: <code>{e}</code>")
