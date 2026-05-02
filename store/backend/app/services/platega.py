"""Platega payment integration.

Real API per https://docs.platega.io/

Endpoint: POST /transaction/process
Headers:  X-MerchantId, X-Secret, Content-Type: application/json
Body:
  paymentMethod  int  required   (2=SBP-QR, 11=Card, 3=ERIP, 12=Intl, 13=Crypto)
  paymentDetails {amount, currency}  required
  description    str  required   (must contain TgId:<id> or UserId:<id>)
  return         str  optional
  failedUrl      str  optional
  payload        str  optional   (our metadata, NOT echoed back in callback)

Response:
  transactionId  uuid  - Platega's id
  redirect       str   - URL to redirect user for payment
  status         str   - PENDING / CONFIRMED / CANCELED

Callback (configured at merchant level in Platega cabinet, not per-request):
  id, amount, currency, status (CONFIRMED|CANCELED), paymentMethod

Since callback doesn't echo `payload`, we identify the order by storing
Platega's transactionId in Order.payment_id at create time, then look up
the order by that id when the webhook fires.
"""

from decimal import Decimal

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
        self.method = s.platega_method

    def _headers(self) -> dict:
        return {
            "X-MerchantId": self.merchant_id,
            "X-Secret": self.api_key,
            "Content-Type": "application/json",
        }

    async def create_invoice(
        self,
        order_id: int,
        user_tg_id: int,
        amount: Decimal,
        description: str,
        return_url: str,
    ) -> dict:
        """Create payment, return {payment_id, payment_url}."""
        payload = {
            "paymentMethod": self.method,
            "paymentDetails": {
                "amount": float(amount),
                "currency": "RUB",
            },
            # description must include TgId:<id> per Platega docs
            "description": f"TgId:{user_tg_id} | {description}",
            "return": return_url,
            "failedUrl": return_url,
            "payload": f"order:{order_id}",
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
            "payment_id": str(data.get("transactionId") or ""),
            "payment_url": data.get("redirect") or data.get("paymentUrl") or data.get("url"),
            "raw": data,
        }

    @staticmethod
    def parse_webhook(payload: dict) -> dict | None:
        """Return {platega_id, status, amount} or None for ignored events.

        Callback per docs:
          id, amount, currency, status, paymentMethod
          status: CONFIRMED | CANCELED
        """
        status = (payload.get("status") or "").upper()
        platega_id = payload.get("id")
        if not platega_id:
            return None
        if status == "CONFIRMED":
            return {
                "platega_id": str(platega_id),
                "status": "paid",
                "amount": Decimal(str(payload.get("amount") or 0)),
            }
        if status == "CANCELED":
            return {
                "platega_id": str(platega_id),
                "status": "canceled",
                "amount": Decimal(str(payload.get("amount") or 0)),
            }
        return None
