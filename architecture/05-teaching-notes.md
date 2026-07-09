# 05 — Teaching Notes

Use this file to run the session. It has talking points, exercises, and the
verification checks that prove the pipeline is behaving.

## Suggested lesson flow (≈45 min)

1. **Concept (10 min)** — walk through [01-overview.md](01-overview.md) and the
   medallion diagram. Ask: *why keep a raw copy at all?*
2. **See the mess (5 min)** — `python run.py --stage generate`, then open a file
   in `data/landing/`. Have students spot the quality problems.
3. **Bronze (5 min)** — `--stage bronze`. Compare a bronze row to its landing
   row. Discuss the metadata columns and "append-only".
4. **Silver (10 min)** — `--stage silver`. Open `sales.csv` and the quarantine
   file. Discuss dedupe and *quarantine vs. drop*.
5. **Gold (5 min)** — `--stage gold`. Open the four aggregate tables. Tie a
   gold number back to silver rows.
6. **Two formats, one table (10 min)** — the highlight: show that a CSV source
   and a SOAP/XML source both land in the *same* `silver/sales/` table.
   `--stage all --reset`, open `sales.csv`, sort by `source_system`, and open a
   raw `landing/invoices/*.xml` next to it. Discuss *schema-on-read* and why
   integration happens at silver, not earlier.
7. **Exercises (10 min)** — pick from below.

## Discussion prompts

- Why does bronze keep bad data instead of cleaning it immediately?
- What could go wrong if silver *dropped* invalid rows silently?
- When cleaning rules change, which layers do you rebuild — and why can you?
- Where would partitioning (e.g. by date) help at real scale?
- Which layer would a BI dashboard read from? Which would a data scientist use?
- **Why keep the raw XML in bronze instead of shredding it immediately?**
- **Why do the two systems only merge at silver and not in landing/bronze?**
- What would it take to add a *third* source (e.g. a JSON REST API)? Which layer
  changes, and which stay the same?

## Exercises

1. **Add a validation rule** — reject rows where `unit_price` is absurdly high
   (e.g. `> 100000`). Add the reason and re-run silver.
2. **New gold table** — build `gold/monthly_revenue.csv` by grouping on the
   year-month of `txn_date`.
3. **New quality problem** — make a generator emit a duplicate with a
   *different* price, then confirm silver keeps the latest ingested one.
4. **Idempotency test** — run `--stage gold` twice and confirm outputs are
   identical (no doubling).
5. **Partitioning** — change bronze to write into `bronze/<source>/date=<day>/`
   folders and discuss the trade-offs.
6. **Add a third source** — write `generate_events.py` + `bronze_events.py` for a
   JSON feed and a silver adapter that maps it into the same `sales` schema.
   Notice gold needs *no* changes.
7. **Break the XML** — add an envelope with a missing `<inv:Amount>` and confirm
   that line is quarantined with a clear reason while the rest still load.

## Verification checklist

Run `python run.py --stage all --reset`, then confirm:

- [ ] `data/landing/orders/` has CSVs with visible dupes/nulls/bad values, and
      `data/landing/invoices/` has SOAP `.xml` envelopes.
- [ ] **Orders row count:** `bronze/orders` row count == total `landing/orders`
      rows.
- [ ] **Invoice catalog:** `bronze/invoices/manifest.csv` has one row per XML
      file in `landing/invoices/`, and the raw XML is copied verbatim.
- [ ] **Reconciliation:** `silver valid + quarantined == distinct
      (source_system, source_id)` across both bronze sources.
- [ ] `silver/_quarantine/rejects.csv` lists each bad record (from either
      source) with a `_reject_reason`.
- [ ] **Both sources present:** `silver/sales/sales.csv` contains rows with
      `source_system = orders` **and** `source_system = invoicing`.
- [ ] **Revenue ties out:** sum of `revenue` in `silver/sales/sales.csv` equals
      the sum in `gold/daily_revenue.csv`, `gold/revenue_by_category.csv`, and
      `gold/revenue_by_source.csv`.
- [ ] Re-running `--stage gold` produces identical files (idempotent).

## Common misconceptions to correct

- *"Bronze is useless because it's dirty."* → It's the system of record and your
  safety net for reprocessing.
- *"Silver and gold are the same thing."* → Silver is clean **detail**; gold is
  **aggregated** for a purpose.
- *"Dropping bad rows is fine."* → You lose visibility into data-quality issues;
  quarantining keeps them countable and fixable.

---

**Contact:** George Gergues
