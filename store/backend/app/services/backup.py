"""Daily encrypted DB backup → private Telegram channel.

Uses pg_dump (in container) → AES-encrypted zip (pyzipper) → upload as document.
Old backups are pruned locally (keep last 30).
"""

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path

import pyzipper
from aiogram import Bot
from aiogram.types import BufferedInputFile, FSInputFile

from app.config import get_settings

BACKUP_DIR = Path("/app/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
KEEP_DAYS = 30


async def _pg_dump() -> bytes:
    s = get_settings()
    env = os.environ.copy()
    env["PGPASSWORD"] = s.postgres_password
    proc = await asyncio.create_subprocess_exec(
        "pg_dump",
        "-h", s.postgres_host,
        "-p", str(s.postgres_port),
        "-U", s.postgres_user,
        "-d", s.postgres_db,
        "--no-owner",
        "--no-privileges",
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {err.decode()}")
    return out


def _encrypt_zip(data: bytes, password: str, inner_name: str) -> bytes:
    import io
    buf = io.BytesIO()
    with pyzipper.AESZipFile(
        buf, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES
    ) as zf:
        zf.setpassword(password.encode())
        zf.writestr(inner_name, data)
    return buf.getvalue()


def _prune_old() -> None:
    cutoff = datetime.utcnow() - timedelta(days=KEEP_DAYS)
    for p in BACKUP_DIR.glob("buta-*.zip"):
        try:
            ts = datetime.strptime(p.stem.split("-", 1)[1].split(".")[0], "%Y%m%d_%H%M%S")
            if ts < cutoff:
                p.unlink()
        except (ValueError, IndexError):
            continue


async def make_backup(bot: Bot, manual: bool = False, requested_by: int | None = None) -> str:
    s = get_settings()
    now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    sql_name = f"buta-{now}.sql"
    zip_name = f"buta-{now}.zip"
    zip_path = BACKUP_DIR / zip_name

    sql = await _pg_dump()
    encrypted = _encrypt_zip(sql, s.backup_password, sql_name)
    zip_path.write_bytes(encrypted)

    caption = (
        f"💾 <b>BUTA STORE backup</b>\n"
        f"🕒 {now} UTC\n"
        f"📁 {len(encrypted) // 1024} KB\n"
        f"🔐 пароль из BACKUP_PASSWORD"
    )
    if manual and requested_by:
        caption += f"\n👤 by {requested_by}"

    file = BufferedInputFile(encrypted, filename=zip_name)
    await bot.send_document(s.backup_chat_id, file, caption=caption)

    _prune_old()
    return str(zip_path)


async def restore_backup(bot: Bot, document) -> None:
    """Restore from a Telegram document (encrypted zip)."""
    s = get_settings()
    file = await bot.get_file(document.file_id)
    raw = await bot.download_file(file.file_path)
    raw_bytes = raw.read()

    import io
    sql_data: bytes | None = None
    with pyzipper.AESZipFile(io.BytesIO(raw_bytes)) as zf:
        zf.setpassword(s.backup_password.encode())
        for name in zf.namelist():
            if name.endswith(".sql"):
                sql_data = zf.read(name)
                break
    if not sql_data:
        raise RuntimeError("no .sql in zip")

    env = os.environ.copy()
    env["PGPASSWORD"] = s.postgres_password
    proc = await asyncio.create_subprocess_exec(
        "psql",
        "-h", s.postgres_host,
        "-p", str(s.postgres_port),
        "-U", s.postgres_user,
        "-d", s.postgres_db,
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate(sql_data)
    if proc.returncode != 0:
        raise RuntimeError(f"psql failed: {err.decode()[:300]}")
