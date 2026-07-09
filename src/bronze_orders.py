"""Stage 1 (orders) — Bronze ingest for the CSV orders system.

Copies every file in ``data/landing/orders/`` into ``data/bronze/orders/``
**verbatim**, adding only ingestion metadata (`_ingested_at`, `_source_file`,
`_batch_id`). Append-only: each run writes a new batch file.
"""

from __future__ import annotations

import os

from common import (
    BRONZE_ORDERS_DIR,
    LANDING_ORDERS_DIR,
    META_COLUMNS,
    ensure_dir,
    list_csv_files,
    log,
    new_batch_id,
    now_iso,
    read_csv,
    write_csv,
)
from generate_orders import ORDER_FIELDS

BRONZE_FIELDS = ORDER_FIELDS + META_COLUMNS


def ingest() -> int:
    """Ingest orders landing files into a new bronze batch. Returns rows written."""
    landing_files = list_csv_files(LANDING_ORDERS_DIR)
    if not landing_files:
        log("bronze", "orders: no landing files — run --stage generate first")
        return 0

    ensure_dir(BRONZE_ORDERS_DIR)
    batch_id = new_batch_id()
    ingested_at = now_iso()

    out_rows: list[dict] = []
    for path in landing_files:
        source = os.path.basename(path)
        rows = read_csv(path)
        for row in rows:
            enriched = dict(row)
            enriched["_ingested_at"] = ingested_at
            enriched["_source_file"] = source
            enriched["_batch_id"] = batch_id
            out_rows.append(enriched)

    out_path = os.path.join(BRONZE_ORDERS_DIR, f"{batch_id}.csv")
    write_csv(out_path, out_rows, BRONZE_FIELDS)
    log("bronze", f"orders: wrote {len(out_rows)} rows ({batch_id})")
    return len(out_rows)


def read_all_bronze() -> list[dict]:
    """Read and concatenate every orders bronze batch file."""
    rows: list[dict] = []
    for path in list_csv_files(BRONZE_ORDERS_DIR):
        rows.extend(read_csv(path))
    return rows


if __name__ == "__main__":
    ingest()
