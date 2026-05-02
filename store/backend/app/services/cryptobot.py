"""CryptoBot (Crypto Pay) integration.

Docs: https://help.crypt.bot/crypto-pay-api
"""

import hashlib
import hmac
from decimal import Decimal

import httpx

from app.config import get_settings


class CryptoBotError(Exception):
    pass


class CryptoBotClient:
    def __init__(self) -> None:
        s = get_settings()
        self.token = s.cryptobot_token
        self.base_url = s.cryptobot_base_url.rstrip("/")

    def _headers(self) -> dict:
        return {"Crypto-Pay-API-Token": self.token}

    async def create_invoice(
        self,
        order_id: int,
        amount: Decimal,
        description: str,
        return_url: str,
        fiat: str = "RUB",
    ) -> dict:
        """Create CryptoBot invoice in fiat (auto-converted to crypto on pay)."""
        payload = {
            "currency_type": "fiat",
            "fiat": fiat,
            "amount": str(amount),
            "description": description,
            "payload": str(order_id),
            "paid_btn_name": "callback",
            "paid_btn_url": return_url,
            "expires_in": 1800,
        }
        async with httpx.AsyncClient(timeout=15) as cli:
            r = await cli.post(
                f"{self.base_url}/createInvoice",
                json=payload,
                headers=self._headers(),
            )
        data = r.json()
        if not data.get("ok"):
            raise CryptoBotError(f"cryptobot error: {data}")
        result = data["result"]
        return {
            "payment_id": str(result["invoice_id"]),
            "payment_url": result.get("mini_app_invoice_url") or result.get("bot_invoice_url") or result["pay_url"],
            "raw": result,
        }

    def verify_webhook(self, body_bytes: bytes, signature: str) -> bool:
        """Verify HMAC signature of webhook body."""
        secret = hashlib.sha256(self.token.encode()).digest()
        calc = hmac.new(secret, body_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(calc, signature)

    @staticmethod
    def parse_webhook(payload: dict) -> dict | None:
        if payload.get("update_type") != "invoice_paid":
            return None
        result = payload.get("payload") or {}
        order_id_raw = result.get("payload")
        if not order_id_raw:
            return None
        try:
            order_id = int(order_id_raw)
        except ValueError:
            return None
        return {
            "order_id": order_id,
            "payment_id": str(result.get("invoice_id")),
            "status": "paid",
            "amount": Decimal(str(result.get("amount") or 0)),
        }
