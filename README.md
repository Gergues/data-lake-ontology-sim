# Data Lake Simulation — Bronze / Silver / Gold

A tiny, dependency-free teaching project that demonstrates the **medallion
architecture** used by modern data lakes. Two source systems — an **orders**
system (CSV) and an **invoicing/payment** middleware (**SOAP/XML**) — feed messy
data through three layers, and *converge into one clean table at silver* so
students see that the pattern is format-agnostic.

Runs on **native Python 3.9+ with the standard library only** — no `pip install`
(XML is parsed with the built-in `xml.etree.ElementTree`).

```
 CSV orders  \
              >  landing -> bronze -> silver (merge) -> gold
 XML invoices /
```

## Quick start

```bash
# From the project root:
python run.py --stage all --reset
```

Then browse the generated `data/` folder.

### Run it stage by stage (recommended for a class)

```bash
python run.py --stage generate   # messy raw files  -> data/landing/<source>/
python run.py --stage bronze     # stored as-is      -> data/bronze/<source>/
python run.py --stage silver     # merged & validated -> data/silver/sales/
python run.py --stage gold       # aggregates        -> data/gold/
```

| Flag | Effect |
| --- | --- |
| `--stage all\|generate\|bronze\|silver\|gold` | Choose what to run (default `all`) |
| `--source all\|orders\|invoicing` | Which source(s) to generate/ingest (default `all`) |
| `--reset` | Delete `data/` before running |

## What each layer does

| Layer | Folder | Responsibility |
| --- | --- | --- |
| **Bronze** | `data/bronze/<source>/` | Store raw data verbatim (CSV rows / XML envelopes) + ingestion metadata (append-only) |
| **Silver** | `data/silver/sales/` | Shred XML, clean, type, dedupe, validate, and **merge both sources** into one conformed table; bad rows → `_quarantine/` |
| **Gold** | `data/gold/` | Business aggregates: daily revenue, revenue by category, top customers, revenue by source |

## Project layout

```
lake-simulation/
├── run.py                   # CLI orchestrator
├── requirements.txt         # (stdlib only)
├── architecture/            # design docs — start with architecture/README.md
├── src/
│   ├── common.py            # paths, CSV I/O, logging, metadata helpers
│   ├── generate_orders.py   # synthetic messy CSV orders
│   ├── generate_invoices.py # synthetic messy SOAP/XML invoices
│   ├── bronze_orders.py     # ingest CSV  -> bronze/orders
│   ├── bronze_invoices.py   # ingest XML  -> bronze/invoices (+ manifest)
│   ├── silver.py            # conform + merge both sources -> silver/sales
│   └── gold.py              # aggregate -> gold
└── data/                    # the "lake" (created when you run)
```

## Learn more

Full design and teaching material live in [architecture/](architecture/README.md):
overview, architecture, data model/dictionary, pipeline details, and lesson
notes with exercises and verification checks.

---

**Contact:** George Gergues
