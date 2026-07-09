-- =============================================================================
-- 03_silver_sales.sql   (PSEUDO-SQL — demo only, not runnable)
-- -----------------------------------------------------------------------------
-- Mirrors: src/silver.py  ->  build()
--
-- *** THIS IS THE CONVERGENCE LAYER — the heart of the demo. ***
-- Two very different bronze feeds (flat CSV orders + nested SOAP/XML invoices)
-- are each mapped into ONE source-neutral vocabulary, then run through the SAME
-- cleaning, dedupe, and validation. Valid rows land in silver.sales; invalid
-- rows are QUARANTINED with a reason (never silently dropped).
--
-- Pipeline shape:
--   bronze.orders    --\
--                       >--> [normalize] --> [dedupe] --> [validate] --> sales
--   bronze.invoices  --/                                            \--> quarantine
--
-- Conformed silver schema (SALES_FIELDS):
--   source_system, source_id, txn_date, customer_id, customer_name,
--   product, category, quantity, unit_price, revenue
-- =============================================================================


-- -----------------------------------------------------------------------------
-- CTE 1a: ORDERS adapter — flat bronze rows -> source-neutral raw records.
--         (Python: silver._orders_raw)
-- -----------------------------------------------------------------------------
WITH orders_raw AS (
    SELECT
        'orders'            AS source_system,
        order_id            AS source_id,
        order_date          AS raw_date,       -- still messy text
        customer_id,
        customer_name,
        product,
        category,
        quantity            AS quantity,       -- still text
        unit_price          AS unit_price,     -- still text
        _ingested_at
    FROM bronze.orders
),

-- -----------------------------------------------------------------------------
-- CTE 1b: INVOICES adapter — SHRED nested XML into one record per <Line>.
--         (Python: silver._invoices_raw, using xml.etree.ElementTree)
--         source_id = '<invoice_id>#<line_ordinal>' guarantees line uniqueness.
--         _ingested_at is looked up from the bronze manifest by file name.
-- -----------------------------------------------------------------------------
invoices_raw AS (
    SELECT
        'invoicing'                                       AS source_system,
        CONCAT(inv.invoice_id, '#', line.ordinal)         AS source_id,
        inv.issued                                        AS raw_date,
        inv.customer_code                                 AS customer_id,
        inv.customer_name                                 AS customer_name,
        line.product                                      AS product,
        line.category                                     AS category,
        line.qty                                          AS quantity,   -- text
        line.amount                                       AS unit_price, -- text
        mfst._ingested_at                                 AS _ingested_at
    FROM bronze.invoices AS b
    JOIN bronze.invoice_manifest AS mfst
      ON mfst._source_file = b._source_file
    -- XMLTABLE stands in for the ElementTree walk over //inv:Invoice//inv:Line
    CROSS APPLY XMLTABLE(
        '//inv:Invoice' PASSING b.xml_document
        COLUMNS
            invoice_id    STRING  PATH '@id',
            issued        STRING  PATH '@issued',
            customer_code STRING  PATH 'inv:Customer/@code',
            customer_name STRING  PATH 'inv:Customer/text()'
    ) AS inv
    CROSS APPLY XMLTABLE(
        '//inv:Invoice//inv:Line' PASSING b.xml_document
        COLUMNS
            ordinal   FOR ORDINALITY,             -- 1,2,3... per line item
            product   STRING PATH '@product',
            category  STRING PATH '@category',
            qty       STRING PATH 'inv:Qty/text()',
            amount    STRING PATH 'inv:Amount/text()'
    ) AS line
),

-- -----------------------------------------------------------------------------
-- CTE 2: UNION the two feeds into one raw stream. From here on, the logic is
--        identical for both — schema-on-read has made format irrelevant.
-- -----------------------------------------------------------------------------
merged_raw AS (
    SELECT * FROM orders_raw
    UNION ALL
    SELECT * FROM invoices_raw
),

-- -----------------------------------------------------------------------------
-- CTE 3: DEDUPE — keep one record per (source_system, source_id), preferring the
--        latest _ingested_at. (Python: silver._dedupe_latest)
--        This is how invoice "_resend" duplicates get collapsed.
-- -----------------------------------------------------------------------------
deduped AS (
    SELECT * FROM (
        SELECT
            m.*,
            ROW_NUMBER() OVER (
                PARTITION BY source_system, UPPER(TRIM(source_id))
                ORDER BY _ingested_at DESC
            ) AS rn
        FROM merged_raw AS m
    )
    WHERE rn = 1
),

-- -----------------------------------------------------------------------------
-- CTE 4: CLEAN + TYPE the survivors. Scalar functions below stand in for the
--        Python helpers (_parse_date, _parse_int, _parse_price) and the
--        casing/normalization rules in silver._clean_and_validate.
-- -----------------------------------------------------------------------------
cleaned AS (
    SELECT
        source_system,
        UPPER(TRIM(source_id))                              AS source_id,
        PARSE_DATE_MULTI(raw_date)                          AS txn_date,     -- YYYY-MM-DD or NULL
        UPPER(TRIM(customer_id))                            AS customer_id,
        INITCAP(TRIM(customer_name))                        AS customer_name,
        INITCAP(TRIM(product))                              AS product,
        COALESCE(NULLIF(INITCAP(TRIM(category)), ''), 'Unknown') AS category,
        TRY_CAST(TRIM(quantity) AS INT)                     AS quantity,     -- NULL if non-numeric
        TRY_CAST(REPLACE(LTRIM(TRIM(unit_price), '$'), ',', '') AS DECIMAL(10,2)) AS unit_price
    FROM deduped
)

-- -----------------------------------------------------------------------------
-- FINAL: split into VALID (-> silver.sales) vs INVALID (-> quarantine) using the
--        exact validation rules from silver._clean_and_validate. Revenue is
--        derived only for valid rows.
--
-- Validation rules (any failure => quarantine, with the matching reason):
--   1. source_id present                       -> 'missing source_id'
--   2. date parseable                          -> 'unparseable date'
--   3. quantity is a positive integer          -> 'quantity not a positive integer'
--   4. unit_price is a non-negative number     -> 'unit_price not a valid non-negative number'
-- -----------------------------------------------------------------------------

-- (a) VALID rows -> conformed sales table
INSERT INTO silver.sales
SELECT
    source_system,
    source_id,
    txn_date,
    customer_id,
    customer_name,
    product,
    category,
    quantity,
    unit_price,
    ROUND(quantity * unit_price, 2) AS revenue     -- derived measure
FROM cleaned
WHERE source_id   IS NOT NULL AND source_id <> ''
  AND txn_date    IS NOT NULL
  AND quantity    IS NOT NULL AND quantity  > 0
  AND unit_price  IS NOT NULL AND unit_price >= 0;

-- (b) INVALID rows -> quarantine, tagged with the FIRST failing rule's reason
INSERT INTO silver._quarantine       -- rejects.csv (QUARANTINE_FIELDS + _reject_reason)
SELECT
    source_system,
    source_id,
    raw_date,                        -- keep the ORIGINAL messy values for triage
    customer_id,
    customer_name,
    product,
    category,
    quantity,
    unit_price,
    CASE
        WHEN source_id IS NULL OR source_id = ''            THEN 'missing source_id'
        WHEN PARSE_DATE_MULTI(raw_date) IS NULL             THEN 'unparseable date'
        WHEN TRY_CAST(quantity AS INT) IS NULL
          OR TRY_CAST(quantity AS INT) <= 0                 THEN 'quantity not a positive integer'
        ELSE 'unit_price not a valid non-negative number'
    END AS _reject_reason
FROM deduped
WHERE NOT (
        source_id IS NOT NULL AND source_id <> ''
    AND PARSE_DATE_MULTI(raw_date) IS NOT NULL
    AND TRY_CAST(quantity AS INT) IS NOT NULL AND TRY_CAST(quantity AS INT) > 0
    AND TRY_CAST(REPLACE(LTRIM(unit_price,'$'), ',', '') AS DECIMAL) IS NOT NULL
    AND TRY_CAST(REPLACE(LTRIM(unit_price,'$'), ',', '') AS DECIMAL) >= 0
);

-- Invariant (verified in the Python run):
--   COUNT(silver.sales) + COUNT(silver._quarantine)
--     = COUNT(distinct (source_system, source_id) across both bronze feeds)
