"""Payment provider webhooks (Platega + CryptoBot).

These are called by the providers' servers, not the WebApp. They're idempotent:
calling them multiple times for the same payment is safe.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.bot_singleton import get_bot
from app.db import get_session
from app.services.cryptobot import CryptoBotClient
from app.services.orders import mark_paid
from app.services.platega import PlategaClient

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/platega")
async def platega_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    payload = await request.json()
    parsed = PlategaClient.parse_webhook(payload)
    if not parsed:
        return {"ok": True, "ignored": True}
    bot = get_bot()
    ok = await mark_paid(session, bot, parsed["order_id"], parsed["payment_id"])
    return {"ok": True, "marked": ok}


@router.post("/cryptobot")
async def cryptobot_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    crypto_pay_api_signature: str = Header(None, alias="crypto-pay-api-signature"),
):
    body = await request.body()
    client = CryptoBotClient()
    if crypto_pay_api_signature and not client.verify_webhook(body, crypto_pay_api_signature):
        raise HTTPException(401, "bad signature")
    payload = await request.json()
    parsed = CryptoBotClient.parse_webhook(payload)
    if not parsed:
        return {"ok": True, "ignored": True}
    bot = get_bot()
    ok = await mark_paid(session, bot, parsed["order_id"], parsed["payment_id"])
    return {"ok": True, "marked": ok}
