-- =============================================================================
-- 02_bronze_invoices.sql   (PSEUDO-SQL — demo only, not runnable)
-- -----------------------------------------------------------------------------
-- Mirrors: src/bronze_invoices.py  ->  ingest()
--
-- Same bronze rule as orders: preserve raw fidelity. For the XML feed that means
-- the full SOAP envelope is stored VERBATIM (byte-for-byte). We do NOT shred it
-- here. Instead we also write a small MANIFEST that catalogues every ingested
-- file plus a light read of two identifiers (invoice id, SOAP message id) to aid
-- discovery. Shredding is silver's job (see 03_silver_sales.sql).
--
-- Transformation summary:
--   landing.invoices --> bronze.invoices   (raw XML kept as-is)
--   landing.invoices --> bronze.invoice_manifest   (1 catalogue row per file)
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Step 1: land each envelope verbatim into the bronze store.
--   In Python this is literally write_text(bronze_path, xml_text) — a copy.
-- -----------------------------------------------------------------------------
INSERT INTO bronze.invoices
SELECT
    _source_file,
    xml_document          -- unchanged; full SOAP envelope preserved
FROM landing.invoices;


-- -----------------------------------------------------------------------------
-- Step 2: append a lightweight manifest row per file (append-only across runs).
--   Only a *shallow* peek into the XML — just enough to catalogue it. Full
--   parsing is intentionally deferred to silver.
-- -----------------------------------------------------------------------------
INSERT INTO bronze.invoice_manifest
SELECT
    _source_file                                    AS _source_file,
    xpath_string(xml_document, '//inv:Invoice/@id') AS invoice_id,   -- e.g. 'INV-5001'
    xpath_string(xml_document, '//inv:MessageId')   AS message_id,   -- SOAP header id
    CURRENT_TIMESTAMP()                             AS _ingested_at, -- now_iso()
    CURRENT_BATCH_ID()                              AS _batch_id
FROM landing.invoices;

-- Manifest columns mirror MANIFEST_FIELDS in bronze_invoices.py:
--   [_source_file, invoice_id, message_id, _ingested_at, _batch_id]
-- The manifest also carries the per-file _ingested_at that silver reuses when
-- it shreds the XML (so both feeds share the same dedupe-by-timestamp logic).
