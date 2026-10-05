"""Approve a sandbox order as the buyer, using a browser robot (Playwright).

This stands in for "the user already authorized their agent to pay".
It is plumbing, not part of what Gauntlet measures.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright


def approve_order(approve_url: str, email: str | None = None, password: str | None = None,
                  headless: bool = True, timeout_ms: int = 60_000) -> None:
    load_dotenv()
    email = email or os.environ["BUYER_EMAIL"]
    password = password or os.environ["BUYER_PASSWORD"]
    if "sandbox.paypal.com" not in approve_url:
        raise RuntimeError("refusing to approve a non-sandbox URL")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.set_default_timeout(timeout_ms)
        page.goto(approve_url)

        # Login: PayPal sometimes shows email+password on one page, sometimes two steps.
        page.fill("#email", email)
        nxt = page.locator("#btnNext")
        if nxt.is_visible():
            nxt.click()
        page.wait_for_selector("#password:visible")
        page.fill("#password", password)
        page.click("#btnLogin")

        # Review page: click the pay/continue button.
        pay = page.locator(
            "#payment-submit-btn, [data-testid='submit-button-initial'], "
            "button:has-text('Complete Purchase'), button:has-text('Pay Now'), "
            "button:has-text('Continue to Review Order'), button:has-text('Continue')"
        ).first
        pay.wait_for(state="visible")
        pay.click()

        try:
            page.wait_for_url("**/gauntlet/return**", timeout=timeout_ms)
        except PWTimeout:
            shot = "approve_failed.png"
            page.screenshot(path=shot, full_page=True)
            browser.close()
            raise RuntimeError(f"approval did not finish; screenshot saved to {shot}")
        browser.close()
