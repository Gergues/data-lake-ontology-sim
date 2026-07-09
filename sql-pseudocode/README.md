# SQL Pseudocode — Medallion Transformations (Demo Only)

> ⚠️ **This is PSEUDO-SQL, not runnable SQL.**
> These scripts exist purely to *explain* the intra-layer transformations in a
> familiar, declarative language for the data-engineering class. **The actual
> pipeline is implemented in pure Python** (`src/*.py`) over CSV/XML files on the
> local filesystem — there is no database, no SQL engine, and no tables here.

## Why pseudo-SQL?

The Python code shreds XML, cleans messy strings, dedupes, validates, and
aggregates row-by-row. That logic is easy to *run* but harder to *read at a
glance*. Expressing the same intent as `SELECT ... FROM ... WHERE ...` makes the
**shape** of each transformation obvious:

- what feeds each layer,
- which columns are added or conformed,
- how records are filtered, cleaned, deduped, and aggregated.

Think of each file as the "if we had a warehouse, this is the query we'd write"
version of the corresponding Python module.

## How the pseudo-SQL maps to the real code

| Pseudo-SQL script | Real implementation | Layer transition |
|---|---|---|
| [00_landing_sources.sql](00_landing_sources.sql) | `generate_orders.py`, `generate_invoices.py` | (external raw feeds) |
| [01_bronze_orders.sql](01_bronze_orders.sql) | `bronze_orders.py` | landing/orders → bronze/orders |
| [02_bronze_invoices.sql](02_bronze_invoices.sql) | `bronze_invoices.py` | landing/invoices → bronze/invoices + manifest |
| [03_silver_sales.sql](03_silver_sales.sql) | `silver.py` | bronze (both) → silver/sales + quarantine |
| [04_gold_marts.sql](04_gold_marts.sql) | `gold.py` | silver/sales → gold aggregates |

## What is intentionally faked

Because the real "tables" are files, the pseudo-SQL leans on a few conventions
that would need real infrastructure in production:

- `CREATE EXTERNAL TABLE ... USING (FORMAT 'CSV'|'XML')` stands in for reading a
  folder of files.
- XML shredding is written with a made-up `XMLTABLE(...)` / `xpath()` style;
  the Python code does this with `xml.etree.ElementTree`.
- File-level metadata (`_source_file`, `_ingested_at`, `_batch_id`) is treated as
  if the engine injected it per row.
- `source_id` uppercasing, title-casing names, `$`/comma stripping on prices, and
  the multi-format date parser are shown as scalar functions
  (`UPPER`, `INITCAP`, `PARSE_DATE`, …) — in Python they are small helper funcs.

## Reading order

Follow the numbered files `00 → 04`. Each file starts with a comment block that
names the Python module it mirrors and calls out any place where the pseudo-SQL
simplifies the real logic.

---
*For teaching/demo purposes only. Do not attempt to execute these against a real
database — column functions, `XMLTABLE`, and external-table syntax are
illustrative and dialect-agnostic.*

---

**Contact:** George Gergues
