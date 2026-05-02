"""Platega payment integration.

Docs: https://docs.platega.io
"""

from decimal import Decimal
from uuid import uuid4

import httpx

from app.config import get_settings


class PlategaError(Exception):
    pass


class PlategaClient:
    def __init__(self) -> None:
        s = get_settings()
        self.base_url = s.platega_base_url.rstrip("/")
        self.merchant_id = s.platega_merchant_id
        self.api_key = s.platega_api_key

    def _headers(self) -> dict:
        return {
            "X-MerchantId": self.merchant_id,
            "X-Secret": self.api_key,
            "Content-Type": "application/json",
        }

    async def create_invoice(
        self,
        order_id: int,
        amount: Decimal,
        description: str,
        return_url: str,
        webhook_url: str,
    ) -> dict:
        """Create payment session, return {payment_id, payment_url}."""
        payment_id = f"buta-{order_id}-{uuid4().hex[:8]}"
        payload = {
            "paymentMethod": 1,
            "id": payment_id,
            "paymentDetails": {
                "amount": float(amount),
                "currency": "RUB",
            },
            "description": description,
            "return": return_url,
            "failedUrl": return_url,
            "payload": str(order_id),
            "webhookUrl": webhook_url,
        }
        async with httpx.AsyncClient(timeout=15) as cli:
            r = await cli.post(
                f"{self.base_url}/process",
                json=payload,
                headers=self._headers(),
            )
        if r.status_code >= 400:
            raise PlategaError(f"platega error {r.status_code}: {r.text}")
        data = r.json()
        return {
            "payment_id": payment_id,
            "payment_url": data.get("redirect") or data.get("url") or data.get("paymentUrl"),
            "raw": data,
        }

    @staticmethod
    def parse_webhook(payload: dict) -> dict | None:
        """Return {order_id, payment_id, status, amount} from webhook body or None."""
        status_raw = (payload.get("status") or "").upper()
        if status_raw not in {"CONFIRMED", "PAID", "SUCCESS"}:
            return None
        order_id_raw = payload.get("payload") or payload.get("orderId") or payload.get("id")
        if not order_id_raw:
            return None
        try:
            order_id = int(str(order_id_raw).split("-")[1]) if "-" in str(order_id_raw) else int(order_id_raw)
        except (ValueError, IndexError):
            return None
        return {
            "order_id": order_id,
            "payment_id": str(payload.get("id") or order_id_raw),
            "status": "paid",
            "amount": Decimal(str(payload.get("amount") or 0)),
        }
