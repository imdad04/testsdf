"""Single-process entry: FastAPI + aiogram polling + scheduler.

Run with `python -m app.main` (Dockerfile CMD).
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bot.bot_singleton import get_bot
from app.bot.dispatcher import build_dispatcher
from app.config import get_settings
from app.routers import admin as admin_router
from app.routers import webapp as webapp_router
from app.routers import webhooks as webhooks_router
from app.services.scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("buta")


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot = get_bot()
    dp = build_dispatcher()
    sched = setup_scheduler(bot)

    polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    sched.start()
    log.info("BUTA STORE backend started")

    try:
        yield
    finally:
        sched.shutdown(wait=False)
        await dp.stop_polling()
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()


app = FastAPI(title="BUTA STORE API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # WebApp same-origin in prod via nginx; relaxed for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webapp_router.router)
app.include_router(webhooks_router.router)
app.include_router(admin_router.router)


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "env": get_settings().app_env}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
