"""Stage 0 (invoicing) — synthetic SOAP/XML generator.

Simulates a payment/invoicing middleware that speaks SOAP. Emits one messy SOAP
envelope per invoice into ``data/landing/invoices/``. Each invoice contains one
or more line items.

The mess mirrors the CSV feed so silver has parity work to do:
* missing ``<inv:Amount>`` (blank price),
* invalid ``<inv:Qty>`` (0 / negative / non-numeric),
* missing ``category`` attribute,
* mixed date formats on ``@issued``,
* a duplicate invoice "resend" (same id in a second file).

XML is produced as text templates on purpose so the raw envelopes are easy to
read in class; they are still well-formed and parse cleanly with the stdlib
``xml.etree.ElementTree`` in silver.
"""

from __future__ import annotations

import os
import random

from common import LANDING_INVOICES_DIR, ensure_dir, list_files, log, write_text

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
INV_NS = "urn:demo:invoicing"

CUSTOMERS = [
    ("C-1", "alice"),
    ("C-2", "bob"),
    ("C-3", "carol"),
    ("C-4", "dave"),
    ("C-5", "erin"),
]

PRODUCTS = [
    ("Gadget", "Electronics", 24.50),
    ("Gizmo", "Electronics", 49.00),
    ("Widget", "Home", 9.99),
    ("Trinket", "Toys", 3.75),
]

DAYS = ["2026-06-01", "2026-06-02", "2026-06-03"]


def _messy_date(iso_day: str, rng: random.Random) -> str:
    year, month, day = iso_day.split("-")
    style = rng.choice(["iso", "slash", "loose"])
    if style == "iso":
        return iso_day
    if style == "slash":
        return f"{month}/{day}/{year}"
    return f"{year}-{int(month)}-{int(day)}"


def _messy_qty(rng: random.Random) -> str:
    roll = rng.random()
    if roll < 0.08:
        return "0"
    if roll < 0.13:
        return "-2"
    if roll < 0.17:
        return "n/a"
    return str(rng.randint(1, 4))


def _messy_amount(price: float, rng: random.Random) -> str | None:
    """Return an amount string, or None to omit the element entirely."""
    if rng.random() < 0.12:
        return None  # missing Amount -> silver quarantines the line
    return f"{price:.2f}"


def _line_xml(product: str, category: str | None, qty: str, amount: str | None) -> str:
    cat_attr = f' category="{category}"' if category else ""
    amount_el = (
        f'          <inv:Amount currency="USD">{amount}</inv:Amount>\n'
        if amount is not None
        else ""
    )
    return (
        f'        <inv:Line product="{product}"{cat_attr}>\n'
        f"          <inv:Qty>{qty}</inv:Qty>\n"
        f"{amount_el}"
        f"        </inv:Line>\n"
    )


def _envelope_xml(invoice_id: str, issued: str, msg_id: str,
                  cust_id: str, cust_name: str, lines_xml: str) -> str:
    return (
        f'<soap:Envelope xmlns:soap="{SOAP_NS}" xmlns:inv="{INV_NS}">\n'
        f"  <soap:Header>\n"
        f"    <inv:MessageId>{msg_id}</inv:MessageId>\n"
        f"  </soap:Header>\n"
        f"  <soap:Body>\n"
        f'    <inv:Invoice id="{invoice_id}" issued="{issued}">\n'
        f'      <inv:Customer code="{cust_id}">{cust_name}</inv:Customer>\n'
        f"      <inv:Lines>\n"
        f"{lines_xml}"
        f"      </inv:Lines>\n"
        f"    </inv:Invoice>\n"
        f"  </soap:Body>\n"
        f"</soap:Envelope>\n"
    )


def _write_envelope(invoice_id: str, issued: str, rng: random.Random,
                    suffix: str = "") -> None:
    cust_id, cust_name = rng.choice(CUSTOMERS)
    msg_id = "MSG-" + "".join(rng.choice("0123456789abcdef") for _ in range(4))

    lines_xml = ""
    for _ in range(rng.randint(1, 3)):
        product, category, price = rng.choice(PRODUCTS)
        cat = None if rng.random() < 0.1 else category
        lines_xml += _line_xml(product, cat, _messy_qty(rng), _messy_amount(price, rng))

    xml = _envelope_xml(invoice_id, issued, msg_id, cust_id, cust_name, lines_xml)
    out_path = os.path.join(LANDING_INVOICES_DIR, f"{invoice_id}{suffix}.xml")
    write_text(out_path, xml)


def generate(seed: int = 7) -> int:
    """Generate messy SOAP/XML invoice envelopes. Returns file count."""
    rng = random.Random(seed)
    ensure_dir(LANDING_INVOICES_DIR)

    invoice_counter = 5000
    first_invoice_id: str | None = None
    first_invoice_issued: str | None = None

    for day in DAYS:
        for _ in range(rng.randint(3, 5)):
            invoice_counter += 1
            invoice_id = f"INV-{invoice_counter}"
            issued = _messy_date(day, rng)
            _write_envelope(invoice_id, issued, rng)
            if first_invoice_id is None:
                first_invoice_id, first_invoice_issued = invoice_id, issued

    # Emit a duplicate "resend" of the first invoice (same id, later file) so
    # silver's dedupe-by-(source_system, source_id) has something to resolve.
    if first_invoice_id is not None:
        _write_envelope(first_invoice_id, first_invoice_issued, rng, suffix="_resend")

    count = len(list_files(LANDING_INVOICES_DIR, ".xml"))
    log("generate", f"invoices: wrote {count} SOAP envelope(s)")
    return count


if __name__ == "__main__":
    generate()
