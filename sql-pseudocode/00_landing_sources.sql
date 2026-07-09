-- =============================================================================
-- 00_landing_sources.sql   (PSEUDO-SQL — demo only, not runnable)
-- -----------------------------------------------------------------------------
-- Mirrors: src/generate_orders.py  and  src/generate_invoices.py
--
-- The "landing" zone is just two folders of raw files that upstream systems
-- drop off. There is no transformation here — this script only *declares* the
-- shape of each raw feed so the later scripts have something to select FROM.
--
-- Real world: these are files on disk.
--   data/landing/orders/orders_YYYY-MM-DD.csv     (messy CSV)
--   data/landing/invoices/INV-500X.xml            (one SOAP envelope per file)
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Source A: E-commerce ORDERS  (CSV, deliberately messy)
--   - dates come in mixed formats: 2026-06-01 and 06/01/2026
--   - prices may carry '$' or ','   -> '$19.99', '1,299.00'
--   - quantity/price may be blank, zero, negative, or non-numeric
--   - customer_name / product casing is inconsistent
-- -----------------------------------------------------------------------------
CREATE EXTERNAL TABLE landing.orders
USING (FORMAT 'CSV', LOCATION 'data/landing/orders/')
AS COLUMNS (
    order_id        STRING,   -- natural key, e.g. 'ORD-1042'
    order_date      STRING,   -- RAW text, multiple formats (not yet a DATE)
    customer_id     STRING,   -- e.g. 'C007'
    customer_name   STRING,
    product         STRING,
    category        STRING,
    quantity        STRING,   -- RAW text (may be '', '0', '-2', 'n/a')
    unit_price      STRING    -- RAW text (may be '$19.99', '1,299.00', '')
);


-- -----------------------------------------------------------------------------
-- Source B: INVOICING  (SOAP/XML middleware — one envelope per file)
--   Each file is a full SOAP envelope. One invoice can contain MANY line items,
--   so this is a nested/hierarchical document, not a flat row.
--
--   Envelope shape (namespaces trimmed for readability):
--     <soap:Envelope>
--       <soap:Header><MessageId>MSG-...</MessageId></soap:Header>
--       <soap:Body>
--         <Invoice id="INV-5001" issued="2026-06-01">
--           <Customer code="C007">Ada Lovelace</Customer>
--           <Lines>
--             <Line product="Keyboard" category="Accessories">
--               <Qty>2</Qty><Amount>19.99</Amount>
--             </Line>
--             ... more <Line> ...
--           </Lines>
--         </Invoice>
--       </soap:Body>
--     </soap:Envelope>
--
--   We declare it as a raw document table; SHREDDING happens in silver, NOT here.
-- -----------------------------------------------------------------------------
CREATE EXTERNAL TABLE landing.invoices
USING (FORMAT 'XML', LOCATION 'data/landing/invoices/')
AS COLUMNS (
    _source_file    STRING,   -- filename, e.g. 'INV-5001.xml'
    xml_document    XML       -- the entire SOAP envelope, verbatim
);

-- NOTE: bronze/silver keep both feeds separate and raw until silver, where they
--       finally converge into ONE conformed table (see 03_silver_sales.sql).
