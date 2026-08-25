-- ============================================================================
--  FINANCIAL DATA MANAGEMENT SYSTEM — CASHFLOW & LEDGER
--  DQL ONLY  (SELECT-based queries — no CREATE / INSERT / UPDATE / DELETE)
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. CLIENT LOOKUP
-- ----------------------------------------------------------------------------
SELECT client_id, name, mail_id, login_id
FROM clients
WHERE login_id = 'acpl001';


-- ----------------------------------------------------------------------------
-- 2. RECONCILIATION — balance roll-forward check
--    Today's opening balance should equal yesterday's closing balance.
-- ----------------------------------------------------------------------------
SELECT * FROM (
  SELECT
    a.id, a.Name, a.`Date`,
    a.prev_free_cash_bal AS today_opening,
    LAG(a.Current_Cash) OVER (PARTITION BY a.id ORDER BY a.`Date`) AS prior_closing
  FROM apricus a
) x
WHERE prior_closing IS NOT NULL
  AND today_opening <> prior_closing;


-- ----------------------------------------------------------------------------
-- 3. RECONCILIATION — cash_record entries with no matching trade_data entry
-- ----------------------------------------------------------------------------
SELECT c.id, c.name, c.`date`
FROM cash_record c
LEFT JOIN trade_data t
  ON t.id = c.id AND t.`date` = c.`date`
WHERE t.id IS NULL;


-- ----------------------------------------------------------------------------
-- 4. RECONCILIATION — client IDs used in cash/trade tables but not onboarded
-- ----------------------------------------------------------------------------
SELECT DISTINCT s.id
FROM (
  SELECT id FROM cash_record
  UNION
  SELECT id FROM trade_data
) s
LEFT JOIN clients cl ON cl.login_id = s.id
WHERE cl.client_id IS NULL;


-- ----------------------------------------------------------------------------
-- 5. CLIENT-WISE CASH-FLOW SUMMARY (total in / out / net)
-- ----------------------------------------------------------------------------
SELECT
  id, name,
  SUM(funds_added)     AS total_funds_added,
  SUM(funds_withdrawn) AS total_funds_withdrawn,
  SUM(funds_added) - SUM(funds_withdrawn) AS net_cash_flow
FROM cash_record
GROUP BY id, name
ORDER BY net_cash_flow DESC;


-- ----------------------------------------------------------------------------
-- 6. LATEST LEDGER SNAPSHOT PER CLIENT (current balance + cumulative MTM)
-- ----------------------------------------------------------------------------
SELECT a.*
FROM apricus a
JOIN (
  SELECT id, MAX(`Date`) AS max_date
  FROM apricus
  GROUP BY id
) latest
  ON a.id = latest.id AND a.`Date` = latest.max_date;


-- ----------------------------------------------------------------------------
-- 7. MONTH-ON-MONTH CUMULATIVE MTM TREND (drives the chart on the deck)
-- ----------------------------------------------------------------------------
SELECT
  id, name,
  DATE_FORMAT(`date`, '%Y-%m') AS month,
  MAX(cumulative_mtm) AS month_end_cumulative_mtm
FROM trade_data
WHERE id = 'acpl001'
GROUP BY id, name, DATE_FORMAT(`date`, '%Y-%m')
ORDER BY month;


-- ----------------------------------------------------------------------------
-- 8. ALERT — clients currently on a negative free-cash balance
-- ----------------------------------------------------------------------------
SELECT id, name, `date`, Current_Cash
FROM cash_record
WHERE Current_Cash < 0
ORDER BY `date` DESC;


-- ----------------------------------------------------------------------------
-- 9. ALERT — large single-day MTM drawdown (> 200,000 loss)
-- ----------------------------------------------------------------------------
SELECT id, name, `date`, mtm
FROM trade_data
WHERE mtm < -200000
ORDER BY mtm ASC;


-- ----------------------------------------------------------------------------
-- 10. PORTFOLIO-LEVEL DAILY CASH POSITION (all clients combined)
-- ----------------------------------------------------------------------------
SELECT `date`, SUM(Current_Cash) AS total_cash_across_clients
FROM cash_record
GROUP BY `date`
ORDER BY `date`;


-- ----------------------------------------------------------------------------
-- 11. DUPLICATE-ENTRY CHECK (read-only detection, e.g. 2025-10-28 double entry)
-- ----------------------------------------------------------------------------
SELECT id, `date`, Current_Cash, funds_added, funds_withdrawn, COUNT(*) AS copies
FROM cash_record
GROUP BY id, `date`, Current_Cash, funds_added, funds_withdrawn
HAVING COUNT(*) > 1;

-- ============================================================================
-- END OF DQL
-- ============================================================================
