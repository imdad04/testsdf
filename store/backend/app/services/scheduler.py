"""APScheduler jobs: daily backup + order timeouts + operator pings."""

from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Order, OrderStatus
from app.services.backup import make_backup
from app.services.notifications import notify_admins
from app.services.orders import operator_refund


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    s = get_settings()
    sched = AsyncIOScheduler(timezone="UTC")

    # daily backup @ 04:00 UTC
    sched.add_job(make_backup, "cron", hour=4, minute=0, args=[bot])

    # every 5 min: ping admins about stuck orders / auto-refund timed out ones
    async def watchdog():
        async with SessionLocal() as session:
            now = datetime.utcnow()
            ping_threshold = now - timedelta(minutes=s.operator_ping_min)
            timeout_threshold = now - timedelta(minutes=s.order_timeout_min)

            stuck = (
                await session.execute(
                    select(Order).where(
                        Order.status == OrderStatus.PAID,
                        Order.paid_at < ping_threshold,
                        Order.paid_at >= timeout_threshold,
                    )
                )
            ).scalars().all()
            for o in stuck:
                await notify_admins(
                    bot,
                    f"⚠️ Заказ #{o.id} оплачен {(now - o.paid_at).seconds // 60} мин назад — оператор не взял.",
                )

            timed_out = (
                await session.execute(
                    select(Order).where(
                        Order.status.in_([OrderStatus.PAID, OrderStatus.IN_PROGRESS]),
                        Order.paid_at < timeout_threshold,
                    )
                )
            ).scalars().all()
            for o in timed_out:
                await operator_refund(session, bot, o.id, 0)
                await notify_admins(bot, f"⏱ Авто-возврат по заказу #{o.id} (таймаут).")

    sched.add_job(watchdog, "interval", minutes=5)
    return sched
