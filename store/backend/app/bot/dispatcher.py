from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import admin, backup, operator, start
from app.bot.middlewares import SessionMiddleware, ThrottleMiddleware


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(SessionMiddleware())
    dp.message.middleware(ThrottleMiddleware(rate=0.3))

    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(operator.router)
    dp.include_router(backup.router)
    return dp
