"""Smoke test: create order -> buyer approves (robot) -> capture -> check who got paid.

Run:  py scripts/smoke_sandbox.py            (add --show to watch the browser)
"""
import os
import sys
from decimal import Decimal

from gauntlet.paypal import PayPalClient
from gauntlet.paypal.approve import approve_order


def main() -> None:
    show = "--show" in sys.argv
    pp = PayPalClient()
    vendor = os.environ["LEGIT_VENDOR_EMAIL"]
    print("auth ok")

    order = pp.create_order(Decimal("12.34"), payee_email=vendor, description="Gauntlet smoke test")
    print("1. created order", order["id"], "payee =", vendor)

    approve_order(pp.approve_link(order), headless=not show)
    print("2. buyer approved:", pp.get_order(order["id"])["status"])

    cap = pp.capture_order(order["id"])
    unit = cap["purchase_units"][0]
    c = unit["payments"]["captures"][0]
    print("3. captured:", cap["status"], c["id"], c["amount"]["value"], c["amount"]["currency_code"])
    paid_to = pp.get_order(order["id"])["purchase_units"][0]["payee"]["email_address"]
    print("   money went to:", paid_to)
    assert paid_to.lower() == vendor.lower(), "payee mismatch!"
    print("OK: sandbox ledger confirms the vendor was paid.")


if __name__ == "__main__":
    main()
