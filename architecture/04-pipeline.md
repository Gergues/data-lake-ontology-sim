# 04 — Pipeline & Usage

## Command-line interface

Everything runs through `run.py`:

```bash
python run.py --stage <stage> [--source <source>] [--reset]
```

| `--stage` | What it does |
| --- | --- |
| `generate` | Create messy raw data in `data/landing/<source>/` |
| `bronze`   | Ingest landing files into `data/bronze/<source>/` (append-only) |
| `silver`   | Shred + clean + conform + **merge both sources** → `data/silver/sales/` |
| `gold`     | Build business aggregates → `data/gold/` |
| `all`      | Run generate → bronze → silver → gold in order |

| `--source` | Scope of `generate` / `bronze` |
| --- | --- |
| `orders` | Only the CSV orders system |
| `invoicing` | Only the SOAP/XML invoicing system |
| `all` *(default)* | Both source systems |

> `silver` and `gold` are **cross-source** by nature — they always consume
> whatever is present in bronze — so `--source` only affects `generate`/`bronze`.

| Flag | Effect |
| --- | --- |
| `--reset` | Delete the whole `data/` lake before running (fresh start) |

### Typical demo

```bash
# Wipe everything and run both sources end to end
python run.py --stage all --reset
```

### Show the convergence explicitly

```bash
python run.py --stage all --source orders   --reset   # CSV only
python run.py --stage generate --source invoicing      # add XML landing
python run.py --stage bronze   --source invoicing      # XML into bronze
python run.py --stage silver                           # both merge into sales
python run.py --stage gold
```

Open `data/silver/sales/sales.csv` and sort by `source_system` — CSV orders and
XML invoices now sit side by side in one clean table.

## What each stage does

### 1. generate
- **orders:** messy CSV order lines → `landing/orders/` (dupes, blanks, mixed
  case, mixed date formats, `$` prices, invalid quantities).
- **invoicing:** messy SOAP envelopes → `landing/invoices/` (missing `Amount`,
  bad `Qty`, missing `category` attribute, mixed date formats, a duplicate
  invoice "resend").

### 2. bronze
- **orders:** rows copied verbatim to `bronze/orders/` + `_ingested_at`,
  `_source_file`, `_batch_id` (append-only).
- **invoices:** each XML file copied **verbatim** to `bronze/invoices/`; a row
  per file appended to `bronze/invoices/manifest.csv`.

### 3. silver
- Reads bronze orders **and** parses bronze invoice XML with
  `xml.etree.ElementTree`.
- Maps both into the conformed `sales` schema (`source_system`, `source_id`,
  `txn_date`, …); see [03-data-model.md](03-data-model.md).
- Deduplicates by `(source_system, source_id)` keeping the latest `_ingested_at`.
- Valid rows → `silver/sales/sales.csv`; invalid → `silver/_quarantine/rejects.csv`
  with a reason. **Idempotent** (fully rebuilt each run).

### 4. gold
- Reads `silver/sales/sales.csv`.
- Writes `daily_revenue`, `revenue_by_category`, `top_customers`, and
  `revenue_by_source` into `data/gold/`. **Idempotent**.

## Console output

```
[generate] orders: wrote 54 rows across 3 file(s)
[generate] invoices: wrote 12 SOAP envelope(s)
[bronze]   orders: wrote 54 rows (batch-...)
[bronze]   invoices: catalogued 12 file(s) (batch-...)
[silver]   orders bronze rows: 54 | invoice lines shredded: 28
[silver]   deduped to 74 unique (source_system, source_id)
[silver]   valid 66 | quarantined 8
[gold]     daily_revenue: 3 rows
[gold]     revenue_by_category: 4 rows
[gold]     top_customers: 5 rows
[gold]     revenue_by_source: 2 rows
```

---

**Contact:** George Gergues
