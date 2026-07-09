-- =============================================================================
-- 01_bronze_orders.sql   (PSEUDO-SQL — demo only, not runnable)
-- -----------------------------------------------------------------------------
-- Mirrors: src/bronze_orders.py  ->  ingest()
--
-- Bronze = "raw, but landed and tagged." The golden rule: DO NOT clean or
-- reshape anything. We copy every landing row VERBATIM and add only ingestion
-- metadata so we can trace lineage later. Bronze is APPEND-ONLY: each run adds a
-- new batch (in Python, a new file named <batch_id>.csv).
--
-- Transformation summary:
--   landing.orders  ->  bronze.orders   (+ 3 metadata columns, no cleaning)
-- =============================================================================

INSERT INTO bronze.orders          -- append-only; never truncated
SELECT
    -- ---- payload copied byte-for-byte (still messy on purpose) --------------
    order_id,
    order_date,
    customer_id,
    customer_name,
    product,
    category,
    quantity,
    unit_price,

    -- ---- ingestion metadata injected by the loader -------------------------
    CURRENT_TIMESTAMP()      AS _ingested_at,   -- now_iso()
    _METADATA.FILE_NAME      AS _source_file,   -- e.g. 'orders_2026-06-01.csv'
    CURRENT_BATCH_ID()       AS _batch_id       -- new_batch_id(), e.g. 'batch-2026...'
FROM landing.orders;

-- No WHERE, no CAST, no TRIM. That is deliberate: bronze must preserve the raw
-- fidelity of the source so we can always replay/repair downstream logic.
