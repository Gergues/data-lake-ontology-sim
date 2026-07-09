"""Stage 3 — Gold.

Read the trusted, merged ``silver/sales/sales.csv`` and produce small,
business-ready aggregate tables:

* ``daily_revenue.csv``        — line items and revenue per day (all sources)
* ``revenue_by_category.csv``  — units and revenue per product category
* ``top_customers.csv``        — customers ranked by total spend
* ``revenue_by_source.csv``    — the CSV-vs-XML split (orders vs invoicing)

Gold is idempotent: it overwrites its outputs from silver on every run.
"""

from __future__ import annotations

import os
from collections import defaultdict

from common import GOLD_DIR, SILVER_SALES_DIR, log, read_csv, write_csv


def _read_silver() -> list[dict]:
    return read_csv(os.path.join(SILVER_SALES_DIR, "sales.csv"))


def _daily_revenue(rows: list[dict]) -> list[dict]:
    orders: dict[str, int] = defaultdict(int)
    revenue: dict[str, float] = defaultdict(float)
    for row in rows:
        day = row["txn_date"]
        orders[day] += 1
        revenue[day] += float(row["revenue"])
    return [
        {"txn_date": day, "orders": orders[day], "revenue": round(revenue[day], 2)}
        for day in sorted(orders)
    ]


def _revenue_by_category(rows: list[dict]) -> list[dict]:
    units: dict[str, int] = defaultdict(int)
    revenue: dict[str, float] = defaultdict(float)
    for row in rows:
        cat = row["category"]
        units[cat] += int(row["quantity"])
        revenue[cat] += float(row["revenue"])
    ordered = sorted(revenue, key=lambda c: revenue[c], reverse=True)
    return [
        {"category": cat, "units": units[cat], "revenue": round(revenue[cat], 2)}
        for cat in ordered
    ]


def _top_customers(rows: list[dict]) -> list[dict]:
    names: dict[str, str] = {}
    orders: dict[str, int] = defaultdict(int)
    spend: dict[str, float] = defaultdict(float)
    for row in rows:
        cid = row["customer_id"]
        names[cid] = row["customer_name"]
        orders[cid] += 1
        spend[cid] += float(row["revenue"])
    ordered = sorted(spend, key=lambda c: spend[c], reverse=True)
    return [
        {
            "customer_id": cid,
            "customer_name": names[cid],
            "orders": orders[cid],
            "total_spend": round(spend[cid], 2),
        }
        for cid in ordered
    ]


def _revenue_by_source(rows: list[dict]) -> list[dict]:
    records: dict[str, int] = defaultdict(int)
    revenue: dict[str, float] = defaultdict(float)
    for row in rows:
        src = row["source_system"]
        records[src] += 1
        revenue[src] += float(row["revenue"])
    return [
        {"source_system": src, "records": records[src], "revenue": round(revenue[src], 2)}
        for src in sorted(records)
    ]


def build() -> int:
    """Build all gold tables. Returns the number of tables written."""
    rows = _read_silver()
    if not rows:
        log("gold", "no silver data — run --stage silver first")
        return 0

    daily = _daily_revenue(rows)
    by_cat = _revenue_by_category(rows)
    top = _top_customers(rows)
    by_source = _revenue_by_source(rows)

    write_csv(os.path.join(GOLD_DIR, "daily_revenue.csv"), daily,
              ["txn_date", "orders", "revenue"])
    write_csv(os.path.join(GOLD_DIR, "revenue_by_category.csv"), by_cat,
              ["category", "units", "revenue"])
    write_csv(os.path.join(GOLD_DIR, "top_customers.csv"), top,
              ["customer_id", "customer_name", "orders", "total_spend"])
    write_csv(os.path.join(GOLD_DIR, "revenue_by_source.csv"), by_source,
              ["source_system", "records", "revenue"])

    log("gold", f"daily_revenue: {len(daily)} rows")
    log("gold", f"revenue_by_category: {len(by_cat)} rows")
    log("gold", f"top_customers: {len(top)} rows")
    log("gold", f"revenue_by_source: {len(by_source)} rows")
    return 4


if __name__ == "__main__":
    build()
