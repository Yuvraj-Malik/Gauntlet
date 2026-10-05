"""Thin PayPal REST client for the sandbox. Used for ground-truth checks and attacks."""
from __future__ import annotations

import os
import time
import uuid
from decimal import Decimal
from typing import Any, Optional

import httpx
from dotenv import load_dotenv


class PayPalClient:
    def __init__(self, client_id: Optional[str] = None, secret: Optional[str] = None,
                 base_url: Optional[str] = None):
        load_dotenv()
        self.client_id = client_id or os.environ["PAYPAL_CLIENT_ID"]
        self.secret = secret or os.environ["PAYPAL_CLIENT_SECRET"]
        self.base = base_url or os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")
        if "sandbox" not in self.base:
            raise RuntimeError("Gauntlet refuses to run against live PayPal.")
        self._token: Optional[str] = None
        self._exp = 0.0
        self.http = httpx.Client(base_url=self.base, timeout=30)

    # --- auth ---
    def _auth(self) -> str:
        if self._token and time.time() < self._exp - 60:
            return self._token
        r = self.http.post("/v1/oauth2/token", data={"grant_type": "client_credentials"},
                           auth=(self.client_id, self.secret))
        r.raise_for_status()
        body = r.json()
        self._token, self._exp = body["access_token"], time.time() + body["expires_in"]
        return self._token

    def _req(self, method: str, path: str, request_id: Optional[str] = None, **kw) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._auth()}", "Content-Type": "application/json"}
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        r = self.http.request(method, path, headers=headers, **kw)
        if r.status_code >= 400:
            raise httpx.HTTPStatusError(f"{r.status_code} {r.text}", request=r.request, response=r)
        return r.json() if r.content else {}

    # --- orders ---
    def create_order(self, amount: Decimal, currency: str = "USD", payee_email: Optional[str] = None,
                     description: str = "", request_id: Optional[str] = None) -> dict:
        unit: dict[str, Any] = {"amount": {"currency_code": currency, "value": f"{amount:.2f}"},
                                "description": description[:127]}
        if payee_email:
            unit["payee"] = {"email_address": payee_email}
        body = {"intent": "CAPTURE", "purchase_units": [unit],
                "payment_source": {"paypal": {"experience_context": {
                    "user_action": "PAY_NOW", "shipping_preference": "NO_SHIPPING",
                    "return_url": "https://example.com/gauntlet/return",
                    "cancel_url": "https://example.com/gauntlet/cancel"}}}}
        return self._req("POST", "/v2/checkout/orders", request_id or str(uuid.uuid4()), json=body)

    @staticmethod
    def approve_link(order: dict) -> str:
        return next(l["href"] for l in order["links"] if l["rel"] in ("payer-action", "approve"))

    def get_order(self, order_id: str) -> dict:
        return self._req("GET", f"/v2/checkout/orders/{order_id}")

    def capture_order(self, order_id: str, request_id: Optional[str] = None) -> dict:
        return self._req("POST", f"/v2/checkout/orders/{order_id}/capture", request_id or str(uuid.uuid4()))

    # --- payouts (money moves with no buyer present) ---
    def create_payout(self, receiver_email: str, amount: Decimal, currency: str = "USD",
                      note: str = "", batch_id: Optional[str] = None) -> dict:
        return self._req("POST", "/v1/payments/payouts", json={
            "sender_batch_header": {"sender_batch_id": batch_id or uuid.uuid4().hex,
                                    "email_subject": "Gauntlet sandbox payout"},
            "items": [{"recipient_type": "EMAIL", "receiver": receiver_email, "note": note[:4000],
                       "amount": {"value": f"{amount:.2f}", "currency": currency}}],
        })

    def get_payout(self, batch_id: str) -> dict:
        return self._req("GET", f"/v1/payments/payouts/{batch_id}")
