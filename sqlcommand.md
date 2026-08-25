-- ============================================================================
--  FINANCIAL DATA MANAGEMENT SYSTEM — CASHFLOW & LEDGER
--  SQL COMMAND FLOW (in the order the system actually executes them)
--
--  Flow:
--   STEP 0  Database setup
--   STEP 1  Schema creation          (clients, cash_record, trade_data, apricus)
--   STEP 2  Client onboarding
--   STEP 3  Daily cash-flow entry
--   STEP 4  Daily trade / MTM entry
--   STEP 5  Ledger consolidation     (cash_record + trade_data -> apricus)
--   STEP 6  Reconciliation checks    (data integrity / balance verification)
--   STEP 7  Reporting & dashboard queries
--   STEP 8  Views for repeat use
--   STEP 9  Maintenance / housekeeping
-- ============================================================================


-- ============================================================================
-- STEP 0 — DATABASE SETUP
-- ============================================================================
CREATE DATABASE IF NOT EXISTS acpl
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

USE acpl;


-- ============================================================================
-- STEP 1 — SCHEMA CREATION
-- Four core tables, matching the source data files.
-- ============================================================================

-- 1.1  Master client list -----------------------------------------------------
CREATE TABLE IF NOT EXISTS clients (
  client_id  INT NOT NULL AUTO_INCREMENT,
  name       TEXT,
  mail_id    TEXT,
  login_id   VARCHAR(50),
  PRIMARY KEY (client_id),
  KEY idx_clients_login (login_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.2  Daily cash movement per client -----------------------------------------
CREATE TABLE IF NOT EXISTS cash_record (
  `date`               DATE,
  id                   VARCHAR(50),
  name                 VARCHAR(255),
  funds_added          DECIMAL(15,2),
  funds_withdrawn      DECIMAL(15,2),
  prev_free_cash_bal   DECIMAL(15,2),
  Current_Cash         DECIMAL(15,2),
  Difference           DECIMAL(15,2),
  KEY idx_cash_id_date (id, `date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.3  Daily trade / mark-to-market per client --------------------------------
CREATE TABLE IF NOT EXISTS trade_data (
  `date`           DATE,
  id               VARCHAR(50),
  name             VARCHAR(255),
  investmt_amt     DECIMAL(15,2),
  mtm              DECIMAL(15,2),
  cumulative_mtm   DECIMAL(15,2),
  KEY idx_trade_id_date (id, `date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 1.4  Consolidated ledger — combines cash_record + trade_data ---------------
CREATE TABLE IF NOT EXISTS apricus (
  `Date`               DATE,
  id                   VARCHAR(50),
  Name                 VARCHAR(255),
  Investmt_Amt         DECIMAL(15,2),
  funds_added          DECIMAL(15,2),
  funds_withdrawn      DECIMAL(15,2),
  MTM                  DECIMAL(15,2),
  prev_free_cash_bal   DECIMAL(15,2),
  Current_Cash         DECIMAL(15,2),
  Difference           DECIMAL(15,2),
  Cumulative_MTM       DECIMAL(15,2),
  KEY idx_apricus_id (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================================
-- STEP 2 — CLIENT ONBOARDING
-- Run once per new client, before any cash or trade entries reference them.
-- ============================================================================
INSERT INTO clients (name, mail_id, login_id)
VALUES ('Rohit Sharma', 'acpl001@gmail.com', 'acpl001');

-- Confirm the client_id assigned (used to cross-check login_id mapping)
SELECT client_id, name, login_id
FROM clients
WHERE login_id = 'acpl001';


-- ============================================================================
-- STEP 3 — DAILY CASH-FLOW ENTRY
-- Executed each trading day for every active client.
-- ============================================================================
INSERT INTO cash_record
  (`date`, id, name, funds_added, funds_withdrawn, prev_free_cash_bal, Current_Cash, Difference)
VALUES
  ('2026-08-16', 'acpl001', 'Rohit Sharma', 100000.00, 10000.00, 10000.00, 1000.00, 109000.00);


-- ============================================================================
-- STEP 4 — DAILY TRADE / MTM ENTRY
-- Executed each trading day, in parallel with STEP 3.
-- ============================================================================
INSERT INTO trade_data
  (`date`, id, name, investmt_amt, mtm, cumulative_mtm)
VALUES
  ('2026-08-16', 'acpl001', 'Rohit Sharma', 1000100.00, 10000.00, 235463.24);


-- ============================================================================
-- STEP 5 — LEDGER CONSOLIDATION
-- Merge the day's cash_record and trade_data rows into the single-source-of-
-- truth ledger (apricus). Run after STEP 3 and STEP 4 complete for the day.
-- ============================================================================
INSERT INTO apricus
  (`Date`, id, Name, Investmt_Amt, funds_added, funds_withdrawn, MTM,
   prev_free_cash_bal, Current_Cash, Difference, Cumulative_MTM)
SELECT
  t.`date`, t.id, t.name, t.investmt_amt,
  c.funds_added, c.funds_withdrawn, t.mtm,
  c.prev_free_cash_bal, c.Current_Cash, c.Difference, t.cumulative_mtm
FROM trade_data t
JOIN cash_record c
  ON c.id = t.id AND c.`date` = t.`date`
WHERE t.`date` = '2026-08-16' AND t.id = 'acpl001';


-- ============================================================================
-- STEP 6 — RECONCILIATION CHECKS
-- Run after consolidation to catch data-entry errors before reporting.
-- ============================================================================

-- 6.1  Flag rows where Current_Cash doesn't roll forward correctly
--      (today's prev_free_cash_bal should equal yesterday's Current_Cash)
SELECT * FROM (
  SELECT
    a.id, a.Name, a.`Date`,
    a.prev_free_cash_bal AS today_opening,
    LAG(a.Current_Cash) OVER (PARTITION BY a.id ORDER BY a.`Date`) AS prior_closing
  FROM apricus a
) x
WHERE prior_closing IS NOT NULL
  AND today_opening <> prior_closing;

-- 6.2  Flag any cash_record entry with no matching trade_data entry (orphans)
SELECT c.id, c.name, c.`date`
FROM cash_record c
LEFT JOIN trade_data t
  ON t.id = c.id AND t.`date` = c.`date`
WHERE t.id IS NULL;

-- 6.3  Flag any client_id in cash_record/trade_data not present in clients
SELECT DISTINCT s.id
FROM (
  SELECT id FROM cash_record
  UNION
  SELECT id FROM trade_data
) s
LEFT JOIN clients cl ON cl.login_id = s.id
WHERE cl.client_id IS NULL;


-- ============================================================================
-- STEP 7 — REPORTING & DASHBOARD QUERIES
-- Read-only queries that power the presentation layer / dashboard.
-- ============================================================================

-- 7.1  Client-wise cash-flow summary (total in / out / net)
SELECT
  id, name,
  SUM(funds_added)     AS total_funds_added,
  SUM(funds_withdrawn) AS total_funds_withdrawn,
  SUM(funds_added) - SUM(funds_withdrawn) AS net_cash_flow
FROM cash_record
GROUP BY id, name
ORDER BY net_cash_flow DESC;

-- 7.2  Latest ledger snapshot per client (current balance + cumulative MTM)
SELECT a.*
FROM apricus a
JOIN (
  SELECT id, MAX(`Date`) AS max_date
  FROM apricus
  GROUP BY id
) latest
  ON a.id = latest.id AND a.`Date` = latest.max_date;

-- 7.3  Month-on-month cumulative MTM trend (drives the chart on the deck)
SELECT
  id, name,
  DATE_FORMAT(`date`, '%Y-%m') AS month,
  MAX(cumulative_mtm) AS month_end_cumulative_mtm
FROM trade_data
WHERE id = 'acpl001'
GROUP BY id, name, DATE_FORMAT(`date`, '%Y-%m')
ORDER BY month;

-- 7.4  Alert: clients currently sitting on a negative free-cash balance
SELECT id, name, `date`, Current_Cash
FROM cash_record
WHERE Current_Cash < 0
ORDER BY `date` DESC;

-- 7.5  Alert: clients with a large single-day MTM drawdown (> 200,000 loss)
SELECT id, name, `date`, mtm
FROM trade_data
WHERE mtm < -200000
ORDER BY mtm ASC;

-- 7.6  Portfolio-level daily cash position (all clients combined)
SELECT `date`, SUM(Current_Cash) AS total_cash_across_clients
FROM cash_record
GROUP BY `date`
ORDER BY `date`;


-- ============================================================================
-- STEP 8 — VIEWS FOR REPEAT USE
-- Wrap the most-used reporting queries as views so the app/dashboard layer
-- can just SELECT from them instead of re-writing the logic each time.
-- ============================================================================

CREATE OR REPLACE VIEW vw_client_latest_balance AS
SELECT a.id, a.Name, a.`Date`, a.Current_Cash, a.Cumulative_MTM
FROM apricus a
JOIN (
  SELECT id, MAX(`Date`) AS max_date FROM apricus GROUP BY id
) latest
  ON a.id = latest.id AND a.`Date` = latest.max_date;

CREATE OR REPLACE VIEW vw_client_cashflow_summary AS
SELECT
  id, name,
  SUM(funds_added)     AS total_funds_added,
  SUM(funds_withdrawn) AS total_funds_withdrawn,
  SUM(funds_added) - SUM(funds_withdrawn) AS net_cash_flow
FROM cash_record
GROUP BY id, name;

CREATE OR REPLACE VIEW vw_negative_balance_alerts AS
SELECT id, name, `date`, Current_Cash
FROM cash_record
WHERE Current_Cash < 0;

-- usage:
-- SELECT * FROM vw_client_latest_balance;
-- SELECT * FROM vw_client_cashflow_summary ORDER BY net_cash_flow DESC;
-- SELECT * FROM vw_negative_balance_alerts;


-- ============================================================================
-- STEP 9 — MAINTENANCE / HOUSEKEEPING
-- Run periodically, not as part of the daily flow.
-- ============================================================================

-- 9.1  Detect exact duplicate cash_record rows (e.g. double-entry on 2025-10-28)
--      Review the output before deleting anything by hand.
SELECT id, `date`, Current_Cash, funds_added, funds_withdrawn, COUNT(*) AS copies
FROM cash_record
GROUP BY id, `date`, Current_Cash, funds_added, funds_withdrawn
HAVING COUNT(*) > 1;

-- Recommended fix: add a surrogate primary key (e.g. row_id INT AUTO_INCREMENT)
-- to cash_record / trade_data / apricus so duplicates can be deleted by id
-- instead of by matching every column. Then:
--   ALTER TABLE cash_record ADD COLUMN row_id INT AUTO_INCREMENT PRIMARY KEY FIRST;
--   DELETE c1 FROM cash_record c1
--   JOIN cash_record c2
--     ON c1.id = c2.id AND c1.`date` = c2.`date`
--    AND c1.Current_Cash = c2.Current_Cash
--    AND c1.row_id > c2.row_id;

-- 9.2  Rebuild indexes after a large bulk load
ANALYZE TABLE clients, cash_record, trade_data, apricus;

-- ============================================================================
-- END OF FLOW
-- ============================================================================
