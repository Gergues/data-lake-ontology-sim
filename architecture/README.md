# Data Lake Simulation — Architecture Docs

A hands-on teaching project that demonstrates the **medallion architecture**
(bronze → silver → gold) using nothing but the Python standard library.

The simulation ingests intentionally *messy* synthetic data from **two source
systems** — an orders system (CSV) and an invoicing/payment middleware (SOAP/XML)
— and walks both through three refinement layers, so students can see exactly
what each layer of a real data lake is responsible for and how heterogeneous
sources converge.

## Read these in order

| Doc | What it covers |
| --- | --- |
| [01-overview.md](01-overview.md) | Goal, audience, and the medallion concept |
| [02-architecture.md](02-architecture.md) | Folder layout, data flow, layer responsibilities |
| [03-data-model.md](03-data-model.md) | Schemas and data dictionary for every layer |
| [04-pipeline.md](04-pipeline.md) | Stage-by-stage transformations and CLI usage |
| [05-teaching-notes.md](05-teaching-notes.md) | Exercises, discussion prompts, verification |
| [06-ontology.md](06-ontology.md) | The meaning layer — schema vs. ontology, and how silver already conforms meaning |
| [07-lakehouse-and-ontology-store.md](07-lakehouse-and-ontology-store.md) | Platform theory — why a lakehouse, why an ontology store, integration levels, and why to separate them |
| [08-add-a-json-source.md](08-add-a-json-source.md) | Live exercise — add a third (JSON) source and see that only meaning changes, gold doesn't |

## TL;DR

```
 CSV orders  \
              >  landing -> bronze -> silver (merge) -> gold
 XML invoices /
```

- **Pure Python**, standard library only, zero `pip install` (XML via
  `xml.etree.ElementTree`).
- Run everything with `python run.py --stage all`.
- Two sources land and store in their native format, then converge into one
  conformed `silver/sales/` table.
- Every stage prints what it did (rows in / out / rejected).

---

**Contact:** George Gergues
