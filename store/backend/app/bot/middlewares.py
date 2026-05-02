"""Middleware: inject sessionmaker + simple Redis throttling."""

import time

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import SessionLocal


class SessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        data["sessionmaker"] = SessionLocal
        return await handler(event, data)


class ThrottleMiddleware(BaseMiddleware):
    """In-memory leaky bucket — fine for one-process deployment.
    For multi-worker, swap to Redis."""

    def __init__(self, rate: float = 0.5):
        self.rate = rate
        self.last: dict[int, float] = {}

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        if user:
            now = time.monotonic()
            prev = self.last.get(user.id, 0)
            if now - prev < self.rate:
                return
            self.last[user.id] = now
        return await handler(event, data)
