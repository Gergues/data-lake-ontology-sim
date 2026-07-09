"""Stage 2 — Silver (convergence layer).

Reads **both** bronze sources and merges them into one conformed ``sales`` table:

* **orders** (CSV rows) are mapped field-by-field, and
* **invoices** (SOAP/XML) are *shredded* with ``xml.etree.ElementTree`` into one
  record per line item.

Both are normalized into a source-neutral raw record, then run through identical
cleaning, dedupe (by ``source_system`` + ``source_id``), and validation. Invalid
records from either source are **quarantined** with a reason, never dropped.

Silver is idempotent: it fully rebuilds its outputs on every run.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET

import bronze_orders
import bronze_invoices
from common import SILVER_QUARANTINE_DIR, SILVER_SALES_DIR, log, read_text, write_csv

NS = {"soap": bronze_invoices.SOAP_NS, "inv": bronze_invoices.INV_NS}

# Conformed silver schema — the shared vocabulary both sources map into.
SALES_FIELDS = [
    "source_system",
    "source_id",
    "txn_date",
    "customer_id",
    "customer_name",
    "product",
    "category",
    "quantity",
    "unit_price",
    "revenue",
]

# Source-neutral raw record (pre-cleaning). Quarantine keeps these + a reason.
RAW_FIELDS = [
    "source_system",
    "source_id",
    "raw_date",
    "customer_id",
    "customer_name",
    "product",
    "category",
    "quantity",
    "unit_price",
]
QUARANTINE_FIELDS = RAW_FIELDS + ["_reject_reason"]


# ---------------------------------------------------------------------------
# Source adapters -> source-neutral raw records
# ---------------------------------------------------------------------------

def _orders_raw() -> list[dict]:
    """Map bronze order rows into source-neutral raw records."""
    records: list[dict] = []
    for row in bronze_orders.read_all_bronze():
        records.append({
            "source_system": "orders",
            "source_id": (row.get("order_id") or "").strip(),
            "raw_date": row.get("order_date", ""),
            "customer_id": row.get("customer_id", ""),
            "customer_name": row.get("customer_name", ""),
            "product": row.get("product", ""),
            "category": row.get("category", ""),
            "quantity": row.get("quantity", ""),
            "unit_price": row.get("unit_price", ""),
            "_ingested_at": row.get("_ingested_at", ""),
        })
    return records


def _text(node: ET.Element | None) -> str:
    return node.text.strip() if node is not None and node.text else ""


def _invoices_raw() -> tuple[list[dict], int]:
    """Shred bronze invoice XML into source-neutral raw records.

    Returns (records, file_count).
    """
    # Ingestion timestamp per file, from the bronze manifest.
    ingest_by_file = {
        m["_source_file"]: m.get("_ingested_at", "")
        for m in bronze_invoices.read_manifest()
    }

    records: list[dict] = []
    xml_files = bronze_invoices.list_bronze_xml()
    for path in xml_files:
        source_file = os.path.basename(path)
        ingested_at = ingest_by_file.get(source_file, "")
        try:
            root = ET.fromstring(read_text(path))
        except ET.ParseError:
            continue  # malformed envelope: skip (could be quarantined instead)

        invoice = root.find(".//inv:Invoice", NS)
        if invoice is None:
            continue
        invoice_id = invoice.get("id", "").strip()
        issued = invoice.get("issued", "")
        customer = invoice.find("inv:Customer", NS)
        cust_id = customer.get("code", "") if customer is not None else ""
        cust_name = _text(customer)

        for ordinal, line in enumerate(invoice.findall(".//inv:Line", NS), start=1):
            records.append({
                "source_system": "invoicing",
                "source_id": f"{invoice_id}#{ordinal}",
                "raw_date": issued,
                "customer_id": cust_id,
                "customer_name": cust_name,
                "product": line.get("product", ""),
                "category": line.get("category", ""),
                "quantity": _text(line.find("inv:Qty", NS)),
                "unit_price": _text(line.find("inv:Amount", NS)),
                "_ingested_at": ingested_at,
            })
    return records, len(xml_files)


# ---------------------------------------------------------------------------
# Cleaning / validation (shared by both sources)
# ---------------------------------------------------------------------------

def _parse_date(value: str) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    if "/" in value:
        parts = value.split("/")
        if len(parts) != 3:
            return None
        month, day, year = parts
    else:
        parts = value.split("-")
        if len(parts) != 3:
            return None
        year, month, day = parts
    try:
        y, m, d = int(year), int(month), int(day)
    except ValueError:
        return None
    if not (1 <= m <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{m:02d}-{d:02d}"


def _parse_int(value: str) -> int | None:
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _parse_price(value: str) -> float | None:
    text = str(value or "").strip().lstrip("$").replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _dedupe_latest(records: list[dict]) -> list[dict]:
    """Keep one record per (source_system, source_id): latest _ingested_at."""
    latest: dict[tuple, dict] = {}
    for rec in records:
        sid = (rec.get("source_id") or "").strip().upper()
        key = (rec.get("source_system", ""), sid)
        if not sid:
            # Keep keyless rows so validation can quarantine them with a reason.
            key = (rec.get("source_system", ""), f"__blank__{len(latest)}")
        current = latest.get(key)
        if current is None or rec.get("_ingested_at", "") >= current.get("_ingested_at", ""):
            latest[key] = rec
    return list(latest.values())


def _clean_and_validate(rec: dict) -> tuple[dict | None, str | None]:
    source_id = (rec.get("source_id") or "").strip().upper()
    if not source_id:
        return None, "missing source_id"

    txn_date = _parse_date(rec.get("raw_date"))
    if txn_date is None:
        return None, "unparseable date"

    quantity = _parse_int(rec.get("quantity"))
    if quantity is None or quantity <= 0:
        return None, "quantity not a positive integer"

    unit_price = _parse_price(rec.get("unit_price"))
    if unit_price is None or unit_price < 0:
        return None, "unit_price not a valid non-negative number"

    category = (rec.get("category") or "").strip()
    clean = {
        "source_system": rec.get("source_system", ""),
        "source_id": source_id,
        "txn_date": txn_date,
        "customer_id": (rec.get("customer_id") or "").strip().upper(),
        "customer_name": (rec.get("customer_name") or "").strip().title(),
        "product": (rec.get("product") or "").strip().title(),
        "category": category.title() if category else "Unknown",
        "quantity": quantity,
        "unit_price": round(unit_price, 2),
        "revenue": round(quantity * unit_price, 2),
    }
    return clean, None


def build() -> tuple[int, int]:
    """Build the conformed silver layer. Returns (valid_count, quarantined_count)."""
    order_records = _orders_raw()
    invoice_records, xml_files = _invoices_raw()
    log("silver",
        f"orders bronze rows: {len(order_records)} | "
        f"invoice lines shredded: {len(invoice_records)} (from {xml_files} file(s))")

    records = order_records + invoice_records
    if not records:
        log("silver", "nothing to process — run --stage bronze first")
        return 0, 0

    deduped = _dedupe_latest(records)
    log("silver", f"deduped to {len(deduped)} unique (source_system, source_id)")

    valid: list[dict] = []
    rejects: list[dict] = []
    for rec in deduped:
        clean, reason = _clean_and_validate(rec)
        if clean is not None:
            valid.append(clean)
        else:
            reject = {field: rec.get(field, "") for field in RAW_FIELDS}
            reject["_reject_reason"] = reason
            rejects.append(reject)

    valid.sort(key=lambda r: (r["source_system"], r["source_id"]))
    write_csv(os.path.join(SILVER_SALES_DIR, "sales.csv"), valid, SALES_FIELDS)
    write_csv(os.path.join(SILVER_QUARANTINE_DIR, "rejects.csv"), rejects, QUARANTINE_FIELDS)

    log("silver", f"valid {len(valid)} | quarantined {len(rejects)}")
    return len(valid), len(rejects)


if __name__ == "__main__":
    build()
