"""Stage 0 (orders) — synthetic raw CSV generator.

Fabricates *intentionally messy* e-commerce order lines and drops one CSV per
day into ``data/landing/orders/``. The mess is what gives the silver layer work
to do: duplicates, blanks, mixed casing, mixed date formats, currency symbols,
and invalid quantities.
"""

from __future__ import annotations

import os
import random

from common import LANDING_ORDERS_DIR, ensure_dir, list_csv_files, log, write_csv

# Landing columns (raw, all text). No metadata yet — bronze adds that.
ORDER_FIELDS = [
    "order_id",
    "order_date",
    "customer_id",
    "customer_name",
    "product",
    "category",
    "quantity",
    "unit_price",
]

CUSTOMERS = [
    ("C-1", "alice"),
    ("C-2", "bob"),
    ("C-3", "carol"),
    ("C-4", "dave"),
    ("C-5", "erin"),
]

PRODUCTS = [
    ("Widget", "Home", 9.99),
    ("Gadget", "Electronics", 24.50),
    ("Doohickey", "Home", 4.25),
    ("Gizmo", "Electronics", 49.00),
    ("Trinket", "Toys", 3.75),
]

DAYS = ["2026-06-01", "2026-06-02", "2026-06-03"]


def _messy_date(iso_day: str, rng: random.Random) -> str:
    """Return the day in one of three formats to mimic inconsistent sources."""
    year, month, day = iso_day.split("-")
    style = rng.choice(["iso", "slash", "loose"])
    if style == "iso":
        return iso_day
    if style == "slash":
        return f"{month}/{day}/{year}"
    # loose: strip leading zeros -> e.g. 2026-6-1
    return f"{year}-{int(month)}-{int(day)}"


def _messy_case(text: str, rng: random.Random) -> str:
    """Randomly upper/lower/pad the text so casing needs normalizing."""
    choice = rng.choice(["lower", "upper", "pad", "title"])
    if choice == "lower":
        return text.lower()
    if choice == "upper":
        return text.upper()
    if choice == "pad":
        return f"  {text}  "
    return text.title()


def _messy_price(price: float, rng: random.Random) -> str:
    """Sometimes prefix a currency symbol; occasionally blank it out."""
    roll = rng.random()
    if roll < 0.15:
        return ""  # missing price -> silver will quarantine
    if roll < 0.45:
        return f"${price:.2f}"
    return f"{price:.2f}"


def _messy_quantity(rng: random.Random) -> str:
    """Mostly valid, but seed some invalid values to be quarantined."""
    roll = rng.random()
    if roll < 0.08:
        return "0"
    if roll < 0.14:
        return "-1"
    if roll < 0.18:
        return "abc"
    return str(rng.randint(1, 5))


def generate(seed: int = 42) -> int:
    """Generate messy orders landing files. Returns total rows written."""
    rng = random.Random(seed)
    ensure_dir(LANDING_ORDERS_DIR)

    total = 0
    order_counter = 1000

    for day in DAYS:
        rows: list[dict] = []
        line_count = rng.randint(15, 20)

        for _ in range(line_count):
            order_counter += 1
            cust_id, cust_name = rng.choice(CUSTOMERS)
            product, category, base_price = rng.choice(PRODUCTS)

            # Occasionally blank the category so silver fills "Unknown".
            category_val = "" if rng.random() < 0.1 else _messy_case(category, rng)

            row = {
                "order_id": f"ORD-{order_counter}",
                "order_date": _messy_date(day, rng),
                "customer_id": _messy_case(cust_id, rng),
                "customer_name": _messy_case(cust_name, rng),
                "product": _messy_case(product, rng),
                "category": category_val,
                "quantity": _messy_quantity(rng),
                "unit_price": _messy_price(base_price, rng),
            }
            rows.append(row)

            # ~20% chance to emit a duplicate order_id (a source "retry").
            if rng.random() < 0.2:
                dup = dict(row)
                dup["quantity"] = _messy_quantity(rng)
                rows.append(dup)

        out_path = os.path.join(LANDING_ORDERS_DIR, f"orders_{day}.csv")
        write_csv(out_path, rows, ORDER_FIELDS)
        total += len(rows)
        log("generate", f"orders: wrote {len(rows):>3} rows -> {os.path.basename(out_path)}")

    log("generate",
        f"orders: {total} raw rows across {len(list_csv_files(LANDING_ORDERS_DIR))} file(s)")
    return total


if __name__ == "__main__":
    generate()
