# Financial-data-management-system-cashflow-ledger


A relational database system designed to map client registration data to high-frequency transactional data. This project resolves cross-table collation mismatches, implements index optimization for non-unique entity joins, and provides aggregated financial performance insights.

## 📌 Project Overview

This repository demonstrates how to bridge the gap between static user access tables (`clients`) and dynamic financial data tables (`apricus`). 

The primary technical challenges addressed in this implementation include:
*   **Collation Alignment:** Resolving `Illegal mix of collations` errors between legacy (`utf8mb4_unicode_ci`) and modern (`utf8mb4_0900_ai_ci`) MySQL sorting rules.
*   **Non-Unique Entity Mapping:** Optimizing relational connections using high-performance indexes and database triggers when strict upstream unique constraints are not applicable.
*   **Financial Aggregation:** Calculating exact consolidated Mark-to-Market (MTM) metrics across historical date ranges while safely handling `NULL` records.

---

## 🗄️ Database Architecture

### 1. `clients` Table
Stores primary access records, login identification strings, and internal business tracking IDs.
*   `client_id`: `INT AUTO_INCREMENT PRIMARY KEY` — Internal surrogate key.
*   `client_name`: `VARCHAR(255)` — Registered legal or trade name.
*   `login_id`: `VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci` — Alphanumeric mapping identifier synced with transactional feeds.

### 2. `apricus` Table
Captures dynamic, daily transactional or portfolio metrics per identity string.
*   `id`: `VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci` — Non-unique operational identifier.
*   `name`: `VARCHAR(255)` — Associated reporting name string.
*   `mtm`: `DECIMAL(15, 2)` — Quantitative Mark-to-Market valuation (supports `NULL`).
*   `date`: `DATE` — Execution or recording timestamp.

---

## 🚀 Key Implementations & Queries

### 1. Unified Portfolio Performance Aggregation
To securely extract client performance records across a specific historical window without dropping secondary values or failing standard SQL grouping rules:

```sql
SELECT 
    c.client_id, 
    a.name, 
    c.login_id, 
    SUM(a.mtm) AS total_mtm
FROM clients c  
INNER JOIN apricus a 
    ON c.login_id = a.id 
WHERE a.date BETWEEN '2026-03-25' AND '2026-03-30'
GROUP BY c.client_id, a.name, c.login_id
HAVING SUM(a.mtm) IS NOT NULL;
```

### 2. Performance Indexes (For Non-Unique Parent Keys)
Because the transactional data stream allows duplicate identity records, strict foreign key references are bypassed. Performance scaling is sustained via composite indexing:

```sql
-- Index parent table transactional feed
ALTER TABLE apricus ADD INDEX idx_apricus_id (id);

-- Index child table login configurations  
ALTER TABLE clients ADD INDEX idx_clients_login (login_id);
```

### 3. Application-Level Data Integrity Enforcer
To protect the database integrity against orphan records without a unique constraints layer, a proactive database trigger evaluates data entries on execution:

```sql
DELIMITER $$

CREATE TRIGGER check_login_id_exists
BEFORE INSERT ON clients
FOR EACH ROW
BEGIN
    IF NOT EXISTS (SELECT 1 FROM apricus WHERE id = NEW.login_id) THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Data Integrity Error: login_id must exist within upstream records.';
    END IF;
END$$

DELIMITER ;
```

---

## 🛠️ Troubleshooting & Technical Notes

### Collation Conflicts Resolved
If you encounter an error declaring an `Illegal mix of collations (utf8mb4_0900_ai_ci, IMPLICIT) and (utf8mb4_unicode_ci, IMPLICIT) for operation '='`, it implies your system environment is executing comparisons across mismatched binary definitions. 

Ensure structural conformity across tables by altering your access keys to map strictly to the upstream collation configuration:
```sql
ALTER TABLE clients 
MODIFY COLUMN login_id VARCHAR(50) 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;
```

---

## 📝 License
This project is open-source and available under the [MIT License](https://opensource.org/licenses/MIT).
