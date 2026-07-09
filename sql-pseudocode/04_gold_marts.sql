-- =============================================================================
-- 04_gold_marts.sql   (PSEUDO-SQL — demo only, not runnable)
-- -----------------------------------------------------------------------------
-- Mirrors: src/gold.py  ->  build()
--
-- Gold = business-ready aggregates. All four marts read ONLY from the trusted,
-- conformed silver.sales table (never from bronze). Because both sources already
-- converged in silver, every gold number blends orders + invoicing automatically
-- — except revenue_by_source, which deliberately splits them back apart.
--
-- Gold is idempotent: each run fully rebuilds these tables from silver.
--
-- Produces (mirrors the 4 CSVs written by gold.build):
--   gold.daily_revenue        gold.revenue_by_category
--   gold.top_customers        gold.revenue_by_source
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Mart 1: DAILY REVENUE — line items and revenue per day (all sources combined).
--         (Python: gold._daily_revenue)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE gold.daily_revenue AS
SELECT
    txn_date,
    COUNT(*)            AS orders,      -- line-item count for the day
    ROUND(SUM(revenue), 2) AS revenue
FROM silver.sales
GROUP BY txn_date
ORDER BY txn_date;                      -- sorted by day


-- -----------------------------------------------------------------------------
-- Mart 2: REVENUE BY CATEGORY — units sold and revenue per product category.
--         (Python: gold._revenue_by_category)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE gold.revenue_by_category AS
SELECT
    category,
    SUM(quantity)          AS units,
    ROUND(SUM(revenue), 2) AS revenue
FROM silver.sales
GROUP BY category
ORDER BY revenue DESC;                  -- biggest earners first


-- -----------------------------------------------------------------------------
-- Mart 3: TOP CUSTOMERS — customers ranked by total spend.
--         (Python: gold._top_customers)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE gold.top_customers AS
SELECT
    customer_id,
    ANY_VALUE(customer_name)  AS customer_name,   -- one representative name
    COUNT(*)                  AS orders,          -- line-item count
    ROUND(SUM(revenue), 2)    AS total_spend
FROM silver.sales
GROUP BY customer_id
ORDER BY total_spend DESC;


-- -----------------------------------------------------------------------------
-- Mart 4: REVENUE BY SOURCE — the CSV-vs-XML split (orders vs invoicing).
--         (Python: gold._revenue_by_source)
--         This is the teaching payoff: proof that ONE silver table carries BOTH
--         formats, and we can still attribute revenue back to each system.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE gold.revenue_by_source AS
SELECT
    source_system,                       -- 'orders' or 'invoicing'
    COUNT(*)               AS records,
    ROUND(SUM(revenue), 2) AS revenue
FROM silver.sales
GROUP BY source_system
ORDER BY source_system;

-- Reconciliation check (verified in the Python run):
--   SUM(gold.daily_revenue.revenue)
--     = SUM(gold.revenue_by_category.revenue)
--     = SUM(gold.revenue_by_source.revenue)
--     = SUM(silver.sales.revenue)
