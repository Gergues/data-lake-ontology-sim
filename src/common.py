"""Shared helpers for the data lake simulation.

Pure standard library. Provides layer paths, CSV read/write, a tiny logger,
and ingestion-metadata helpers used by every stage.
"""

from __future__ import annotations

import csv
import os
import shutil
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths — the "lake" lives under <project root>/data
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Landing — one drop zone per source system.
LANDING_DIR = os.path.join(DATA_DIR, "landing")
LANDING_ORDERS_DIR = os.path.join(LANDING_DIR, "orders")
LANDING_INVOICES_DIR = os.path.join(LANDING_DIR, "invoices")

# Bronze — raw, per source, in native format.
BRONZE_DIR = os.path.join(DATA_DIR, "bronze")
BRONZE_ORDERS_DIR = os.path.join(BRONZE_DIR, "orders")
BRONZE_INVOICES_DIR = os.path.join(BRONZE_DIR, "invoices")

# Silver — a single conformed table where both sources converge.
SILVER_DIR = os.path.join(DATA_DIR, "silver")
SILVER_SALES_DIR = os.path.join(SILVER_DIR, "sales")
SILVER_QUARANTINE_DIR = os.path.join(SILVER_DIR, "_quarantine")

GOLD_DIR = os.path.join(DATA_DIR, "gold")

# Metadata columns added at the bronze layer.
META_COLUMNS = ["_ingested_at", "_source_file", "_batch_id"]


def log(stage: str, message: str) -> None:
    """Print a namespaced status line, e.g. ``[silver] ...``."""
    print(f"[{stage}] {message}")


def new_batch_id() -> str:
    """Return a run identifier such as ``batch-20260709101500``."""
    return "batch-" + datetime.now().strftime("%Y%m%d%H%M%S")


def now_iso() -> str:
    """Current timestamp as an ISO-8601 string (seconds precision)."""
    return datetime.now().replace(microsecond=0).isoformat()


def ensure_dir(path: str) -> None:
    """Create ``path`` (and parents) if it does not already exist."""
    os.makedirs(path, exist_ok=True)


def reset_lake() -> None:
    """Delete the entire ``data/`` directory for a clean start."""
    if os.path.isdir(DATA_DIR):
        shutil.rmtree(DATA_DIR)


def list_csv_files(directory: str) -> list[str]:
    """Return sorted absolute paths of ``*.csv`` files in ``directory``."""
    return list_files(directory, ".csv")


def list_files(directory: str, ext: str) -> list[str]:
    """Return sorted absolute paths of files ending in ``ext`` in ``directory``."""
    if not os.path.isdir(directory):
        return []
    ext = ext.lower()
    names = [n for n in os.listdir(directory) if n.lower().endswith(ext)]
    return [os.path.join(directory, n) for n in sorted(names)]


def read_text(path: str) -> str:
    """Read a whole text file (e.g. an XML envelope) as a string."""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def write_text(path: str, content: str) -> None:
    """Write ``content`` to ``path``, creating parent folders as needed."""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def read_csv(path: str) -> list[dict]:
    """Read a CSV file into a list of dicts. Missing file -> empty list."""
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: str, rows: list[dict], fieldnames: list[str]) -> None:
    """Write ``rows`` to ``path`` as CSV, creating parent folders as needed."""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
