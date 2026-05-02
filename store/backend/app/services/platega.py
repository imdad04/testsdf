"""Platega payment integration.

Docs: https://docs.platega.io

Required fields per current API:
- id: GUID/UUID (NOT a string like "buta-1-abc")
- command: operation type ("pay" or whatever Platega expects)
- paymentMethod: int
- paymentDetails: { amount, currency }
- description, return, failedUrl, webhookUrl, payload
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
        # Platega requires a valid UUID for `id`
        invoice_uuid = str(uuid4())
        payload = {
            "command": "pay",                          # required by Platega
            "paymentMethod": get_settings().platega_method,
            "id": invoice_uuid,
            "paymentDetails": {
                "amount": float(amount),
                "currency": "RUB",
            },
            "description": description,
            "return": return_url,
            "failedUrl": return_url,
            # `payload` carries our internal order id back through the webhook
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
            "payment_id": invoice_uuid,
            "payment_url": (
                data.get("redirect")
                or data.get("url")
                or data.get("paymentUrl")
                or data.get("paymentLink")
            ),
            "raw": data,
        }

    @staticmethod
    def parse_webhook(payload: dict) -> dict | None:
        """Return {order_id, payment_id, status, amount} from webhook body or None.

        Our internal order id was passed in `payload` field at create time,
        so we read it back from there.
        """
        status_raw = (payload.get("status") or "").upper()
        if status_raw not in {"CONFIRMED", "PAID", "SUCCESS"}:
            return None
        order_id_raw = payload.get("payload") or payload.get("orderId")
        if not order_id_raw:
            return None
        try:
            order_id = int(str(order_id_raw))
        except ValueError:
            return None
        return {
            "order_id": order_id,
            "payment_id": str(payload.get("id") or ""),
            "status": "paid",
            "amount": Decimal(str(payload.get("amount") or 0)),
        }
