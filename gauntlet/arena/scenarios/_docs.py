"""Helpers to write realistic business documents."""
from decimal import Decimal


def invoice(vendor: str, inv: str, items: list[tuple[str, int, str]], payee: str = "{VENDOR}",
            extra: str = "", footer: str = "", date: str = "Oct 1, 2026", terms: str = "Net 15") -> str:
    lines = [f"{vendor.upper()}", f"INVOICE {inv}", f"Date: {date}    Terms: {terms}",
             "Bill to: Gauntlet Labs, 14 Market St", "", "Description                     Qty   Amount"]
    total = Decimal("0")
    for desc, qty, amt in items:
        a = Decimal(amt)
        total += a
        lines.append(f"{desc:<31} {qty:>3}   ${a:,.2f}")
    lines += ["", f"Total due: ${total:,.2f} USD", f"Pay via PayPal to: {payee}"]
    if extra:
        lines += ["", extra]
    if footer:
        lines += ["", footer]
    return "\n".join(lines)


def email(frm: str, subject: str, body: str, to: str = "ap@gauntlet-labs.example") -> str:
    return f"From: {frm}\nTo: {to}\nSubject: {subject}\n\n{body}"
