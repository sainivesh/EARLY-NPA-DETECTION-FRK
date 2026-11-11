# NPA Early Detection - Comprehensive Data Validation Report

**Execution Timestamp:** 2026-11-10 16:21:04  
**Audited Location:** `C:\Users\nivesh.bagavatham\Desktop\NPA-AGENT\NPA_DATA_PIPELINE`  
**SQLite Database:** `C:\Users\nivesh.bagavatham\Desktop\NPA-AGENT\NPA_DATA_PIPELINE\04_SQL_DATABASE\npa_project.sqlite`  
**Overall Validation Verdict:** **PASS - Ready for SAS Handoff**

---

## 1. Executive Summary

| Status | Rule Count | Percentage |
|---|---:|---:|
| **PASS** | **61** | **100.0%** |
| **WARNING** | **0** | **0.0%** |
| **FAIL** | **0** | **0.0%** |
| **Total Rules Evaluated** | **61** | **100.0%** |

> [!NOTE]
> SAS Viya execution is pending manual upload and run in SAS Viya for Learners. All Python-side datasets, SQLite tables, mathematical constraints, and handoff contracts have been fully validated.

---

## 2. Population Breakdown & Disjoint Verification

| Population Role | Split Set | Customers | Target Labelled? | Purpose |
|---|---|---:|---|---|
| DEVELOPMENT | TRAIN | 7,000 | Yes (`npa_flag` in 0, 1) | Model Studio Training |
| DEVELOPMENT | TEST | 3,000 | Yes (`npa_flag` in 0, 1) | Independent Champion Evaluation |
| SCORING | SCORING | 2,000 | No (Unlabelled, 0 target data) | Webpage / Live Scoring |
| **Total Customers** | | **12,000** | | |

- **Customer Disjointness:** Verified 100% disjoint at customer level. Zero overlap between Train, Test, and Scoring.
- **Scoring Population Isolation:** The 2,000 scoring customers have **no future simulation rows**, **no future outcome rows**, and **no target leakage**.

---

## 3. Future Outcome Calibration & Simulation Reconciliation

- **Total Labelled Customers:** 10,000
- **Future Simulation Rows:** 60,000 (exactly 6 future months per customer)
- **Observed Positive NPA Events:** `1,216`
- **Observed Positive NPA Rate:** `12.16%`
- **Prototype Calibration Target Range:** 8.00% – 15.00% (**PASS**)
- **Target Reconciliation:** `future_outcome.npa_flag` matches `max(days_past_due) >= 90` across the 6 future months with **100% mathematical precision (0 mismatches)**.

---

## 4. Current Loan Strictly Clean Performance

All current loan observations adhere strictly to non-delinquent performing customer requirements:
1. `emi_history.csv`: 144,000 rows (12 per customer). `emi_paid == emi_due`, `days_past_due == 0`, `npa_indicator == 0`.
2. `payment_history.csv`: 144,000 rows (12 per customer). `payment_delay == 0`, `bounce_flag == 0`, `late_payment_flag == 0`.
3. `credit_bureau.csv`: 12,000 rows. `overdue_accounts == 0`, `bureau_dpd == 0`, `writeoff_accounts == 0`.
4. `loan_account.csv`: All 12,000 loans have `loan_age_months >= 12` to support the 12-month current loan history. Amortization and balance calculations reconcile.

---

## 5. Prior Loan NPA History (NPA_History)

- **Total Prior History Rows:** `115,512` (24 monthly records per sampled customer)
- **Chronological Isolation:** Prior loans end before current loans begin (`prior_loan_end_date < current_loan_start_date`).
- **All 7 Repayment Patterns Implemented:**
  1. `ALL_PAID_ON_TIME`
  2. `OCCASIONAL_LATE_BUT_CURED`
  3. `INTERMITTENT_MISSED_REPAID`
  4. `PAID_3_MONTHS_THEN_STOPPED`
  5. `PAID_6_MONTHS_THEN_STOPPED`
  6. `PRIOR_NPA_UNRESOLVED`
  7. `PRIOR_NPA_RESOLVED_RECOVERED`
- **Historical Customer Summary:** Unsampled customers explicitly assigned `history_available = 0`, ensuring unavailable history is never misconstrued as clean repayment.

---

## 6. Customer Company Details (30-Column Schema)

- **Record Count:** 12,000 rows (1 per customer).
- **String Integrity:** Verified safe string handling. **0 truncated categories** (specifically verified absence of `PROFESSIONAL_P`; `PROFESSIONAL_PRACTICE` preserved intact).
- **Occupation Mapping:**
  - `SALARIED` -> `EMPLOYER` (100% compliant)
  - `BUSINESS` / `SELF_EMPLOYED` -> `CUSTOMER_OWNED` (100% compliant)
  - `PROFESSIONAL` -> `PROFESSIONAL_PRACTICE` or `EMPLOYER` (100% compliant)
- **Synthetic Guardrails:** All 12,000 records marked with `company_data_is_synthetic = 1`.

---

## 7. CSV and SQLite Database Reconciliation

| Dataset / Table Name | CSV Row Count | SQLite Row Count | Status |
|---|---:|---:|---|
| `customer_master` | 12,000 | 12,000 | **PASS** |
| `loan_account` | 12,000 | 12,000 | **PASS** |
| `emi_history` | 144,000 | 144,000 | **PASS** |
| `payment_history` | 144,000 | 144,000 | **PASS** |
| `credit_bureau` | 12,000 | 12,000 | **PASS** |
| `transaction_history` | 144,000 | 144,000 | **PASS** |
| `NPA_History` | 115,512 | 115,512 | **PASS** |
| `customer_company_details` | 12,000 | 12,000 | **PASS** |
| `future_repayment_simulation` | 60,000 | 60,000 | **PASS** |
| `future_outcome` | 10,000 | 10,000 | **PASS** |
| `NPA_CUSTOMER_SPLIT` | 12,000 | 12,000 | **PASS** |
| `npa_history_customer_summary` | 12,000 | 12,000 | **PASS** |

---

## 8. Detailed Validation Rule Inventory

| Rule ID | Dataset | Description | Expected | Actual | Status |
|---|---|---|---|---|---|
| `FILE_EXIST_CUSTOMER_MASTER` | `customer_master` | Verify customer_master.csv exists on disk | File exists | File exists | **PASS** |
| `FILE_EXIST_LOAN_ACCOUNT` | `loan_account` | Verify loan_account.csv exists on disk | File exists | File exists | **PASS** |
| `FILE_EXIST_EMI_HISTORY` | `emi_history` | Verify emi_history.csv exists on disk | File exists | File exists | **PASS** |
| `FILE_EXIST_PAYMENT_HISTORY` | `payment_history` | Verify payment_history.csv exists on disk | File exists | File exists | **PASS** |
| `FILE_EXIST_CREDIT_BUREAU` | `credit_bureau` | Verify credit_bureau.csv exists on disk | File exists | File exists | **PASS** |
| `FILE_EXIST_TRANSACTION_HISTORY` | `transaction_history` | Verify transaction_history.csv exists on disk | File exists | File exists | **PASS** |
| `FILE_EXIST_NPA_HISTORY` | `NPA_History` | Verify NPA_History.csv exists on disk | File exists | File exists | **PASS** |
| `FILE_EXIST_CUSTOMER_COMPANY_DETAILS` | `customer_company_details` | Verify customer_company_details.csv exists on disk | File exists | File exists | **PASS** |
| `FILE_EXIST_FUTURE_REPAYMENT_SIMULATION` | `future_repayment_simulation` | Verify future_repayment_simulation.csv exists on disk | File exists | File exists | **PASS** |
| `FILE_EXIST_FUTURE_OUTCOME` | `future_outcome` | Verify future_outcome.csv exists on disk | File exists | File exists | **PASS** |
| `FILE_EXIST_NPA_CUSTOMER_SPLIT` | `NPA_CUSTOMER_SPLIT` | Verify NPA_CUSTOMER_SPLIT.csv exists on disk | File exists | File exists | **PASS** |
| `FILE_EXIST_NPA_HISTORY_CUSTOMER_SUMMARY` | `npa_history_customer_summary` | Verify npa_history_customer_summary.csv exists on disk | File exists | File exists | **PASS** |
| `SQL_DB_EXISTS` | `npa_project.sqlite` | Verify npa_project.sqlite database exists | Database exists | Database exists | **PASS** |
| `SQL_TABLE_CUSTOMER_MASTER` | `customer_master` | Verify table customer_master exists in SQLite | Table exists | Table exists (12,000 rows) | **PASS** |
| `SQL_TABLE_LOAN_ACCOUNT` | `loan_account` | Verify table loan_account exists in SQLite | Table exists | Table exists (12,000 rows) | **PASS** |
| `SQL_TABLE_EMI_HISTORY` | `emi_history` | Verify table emi_history exists in SQLite | Table exists | Table exists (144,000 rows) | **PASS** |
| `SQL_TABLE_PAYMENT_HISTORY` | `payment_history` | Verify table payment_history exists in SQLite | Table exists | Table exists (144,000 rows) | **PASS** |
| `SQL_TABLE_CREDIT_BUREAU` | `credit_bureau` | Verify table credit_bureau exists in SQLite | Table exists | Table exists (12,000 rows) | **PASS** |
| `SQL_TABLE_TRANSACTION_HISTORY` | `transaction_history` | Verify table transaction_history exists in SQLite | Table exists | Table exists (144,000 rows) | **PASS** |
| `SQL_TABLE_NPA_HISTORY` | `NPA_History` | Verify table NPA_History exists in SQLite | Table exists | Table exists (115,512 rows) | **PASS** |
| `SQL_TABLE_CUSTOMER_COMPANY_DETAILS` | `customer_company_details` | Verify table customer_company_details exists in SQLite | Table exists | Table exists (12,000 rows) | **PASS** |
| `SQL_TABLE_FUTURE_REPAYMENT_SIMULATION` | `future_repayment_simulation` | Verify table future_repayment_simulation exists in SQLite | Table exists | Table exists (60,000 rows) | **PASS** |
| `SQL_TABLE_FUTURE_OUTCOME` | `future_outcome` | Verify table future_outcome exists in SQLite | Table exists | Table exists (10,000 rows) | **PASS** |
| `SQL_TABLE_NPA_CUSTOMER_SPLIT` | `NPA_CUSTOMER_SPLIT` | Verify table NPA_CUSTOMER_SPLIT exists in SQLite | Table exists | Table exists (12,000 rows) | **PASS** |
| `SQL_TABLE_NPA_HISTORY_CUSTOMER_SUMMARY` | `npa_history_customer_summary` | Verify table npa_history_customer_summary exists in SQLite | Table exists | Table exists (12,000 rows) | **PASS** |
| `SCHEMA_CUSTOMER_MASTER` | `customer_master` | Verify column names and order for customer_master | Exact 8 columns in order | Matched 8 columns | **PASS** |
| `SCHEMA_LOAN_ACCOUNT` | `loan_account` | Verify column names and order for loan_account | Exact 11 columns in order | Matched 11 columns | **PASS** |
| `SCHEMA_EMI_HISTORY` | `emi_history` | Verify column names and order for emi_history | Exact 6 columns in order | Matched 6 columns | **PASS** |
| `SCHEMA_PAYMENT_HISTORY` | `payment_history` | Verify column names and order for payment_history | Exact 6 columns in order | Matched 6 columns | **PASS** |
| `SCHEMA_CREDIT_BUREAU` | `credit_bureau` | Verify column names and order for credit_bureau | Exact 9 columns in order | Matched 9 columns | **PASS** |
| `SCHEMA_TRANSACTION_HISTORY` | `transaction_history` | Verify column names and order for transaction_history | Exact 6 columns in order | Matched 6 columns | **PASS** |
| `SCHEMA_NPA_HISTORY` | `NPA_History` | Verify column names and order for NPA_History | Exact 30 columns in order | Matched 30 columns | **PASS** |
| `SCHEMA_CUSTOMER_COMPANY_DETAILS` | `customer_company_details` | Verify column names and order for customer_company_details | Exact 30 columns in order | Matched 30 columns | **PASS** |
| `SCHEMA_FUTURE_REPAYMENT_SIMULATION` | `future_repayment_simulation` | Verify column names and order for future_repayment_simulation | Exact 9 columns in order | Matched 9 columns | **PASS** |
| `SCHEMA_FUTURE_OUTCOME` | `future_outcome` | Verify column names and order for future_outcome | Exact 2 columns in order | Matched 2 columns | **PASS** |
| `SCHEMA_NPA_CUSTOMER_SPLIT` | `NPA_CUSTOMER_SPLIT` | Verify column names and order for NPA_CUSTOMER_SPLIT | Exact 4 columns in order | Matched 4 columns | **PASS** |
| `POP_CUSTOMER_COUNT` | `customer_master` | Total customer count equals 12,000 unique records | 12,000 unique customers | 12,000 unique customers | **PASS** |
| `POP_LOAN_ACCOUNT` | `loan_account` | 12,000 unique loans, exactly one per customer | 12,000 unique loans matching customer master | 12,000 loans, 12,000 unique customers | **PASS** |
| `POP_SPLIT_DISJOINT` | `NPA_CUSTOMER_SPLIT` | Populations are disjoint: 7,000 Train, 3,000 Test, 2,000 Scoring | 7,000 Train, 3,000 Test, 2,000 Scoring (12,000 total) | Train=7,000, Test=3,000, Scoring=2,000 | **PASS** |
| `POP_SCORING_TARGET_ISOLATION` | `future_outcome` | Scoring population (2,000) completely excluded from future outcome | 0 scoring customers in future outcome | 0 scoring customers found (10,000 labelled dev customers) | **PASS** |
| `CURRENT_EMI_STRICT_CLEAN` | `emi_history` | Exactly 12 monthly EMI records per customer; 100% paid, DPD=0, npa_indicator=0 | 144,000 rows, emi_paid==emi_due, DPD==0, npa_indicator==0 | 144,000 rows, 0 unpaid, 0 non-zero DPD, 0 NPA indicators | **PASS** |
| `CURRENT_PAYMENT_STRICT_CLEAN` | `payment_history` | Exactly 12 payment records per customer; payment_delay=0, bounce_flag=0, late_payment_flag=0 | 144,000 rows, payment_delay==0, bounce_flag==0, late_payment_flag==0 | 144,000 rows, 0 delays, 0 bounces, 0 late payment flags | **PASS** |
| `CURRENT_BUREAU_STRICT_CLEAN` | `credit_bureau` | Current credit bureau snapshot clean: overdue_accounts=0, bureau_dpd=0, writeoff_accounts=0 | overdue=0, bureau_dpd=0, writeoff=0 | 0 overdue accounts, 0 bureau DPD, 0 writeoffs | **PASS** |
| `CURRENT_LOAN_AGE_AND_AMORTIZATION` | `loan_account` | Loan age >= 12 months for 12-month observation window; positive amortizing balances | loan_age >= 12, 0 < outstanding < sanctioned | Min loan age=12, all 12,000 balances valid | **PASS** |
| `TRANSACTION_INTEGRITY` | `transaction_history` | 144,000 transaction rows; no negative values; cash_withdrawal <= debit_transaction | 144,000 rows, non-negative, cash_withdrawal <= debit | 144,000 rows, 0 negative values, 0 cash exceeds debit | **PASS** |
| `PRIOR_HISTORY_PATTERNS_AND_CHRONOLOGY` | `NPA_History` | Prior loan ends before current loan starts; 24 months per customer; all 7 patterns represented; NPA event requires DPD >= 90 | Chronology valid, 24 months, 7 patterns, DPD>=90 for NPA | 115,512 rows across 4,813 customers, 7/7 patterns, 0 chronological inversions | **PASS** |
| `COMPANY_DETAILS_RELATIONSHIP_AND_INTEGRITY` | `customer_company_details` | 12,000 company records; valid occupation mapping; NO string truncation (0 PROFESSIONAL_P); clearly marked synthetic | 12,000 rows, valid mapping, no truncation, synthetic=1 | 12,000 rows, relationships={'PROFESSIONAL_PRACTICE', 'EMPLOYER', 'CUSTOMER_OWNED'}, 0 truncated strings | **PASS** |
| `FUTURE_SIMULATION_AND_TARGET_RECONCILIATION` | `future_repayment_simulation / future_outcome` | 60,000 simulation rows (6 per dev customer); 0 scoring customers; npa_flag reconciles 100% with DPD>=90; target rate 8-15% | 60,000 rows, 10,000 targets, 100% reconciliation, 8-15% positive rate | 60,000 rows, 10,000 targets, 0 mismatches, Positive rate=12.16% (1,216 events) | **PASS** |
| `STRATIFIED_SPLIT_BALANCE` | `NPA_CUSTOMER_SPLIT` | 70:30 stratified split balances positive target rate between Train and Test | Balanced target distribution (diff < 0.5%) | Train rate=12.16% (851 events), Test rate=12.17% (365 events), Diff=0.010% | **PASS** |
| `SQL_CSV_MATCH_CUSTOMER_MASTER` | `customer_master` | Reconcile row count between customer_master.csv and SQLite table customer_master | Exact match (12,000 rows) | Matched (12,000 rows) | **PASS** |
| `SQL_CSV_MATCH_LOAN_ACCOUNT` | `loan_account` | Reconcile row count between loan_account.csv and SQLite table loan_account | Exact match (12,000 rows) | Matched (12,000 rows) | **PASS** |
| `SQL_CSV_MATCH_EMI_HISTORY` | `emi_history` | Reconcile row count between emi_history.csv and SQLite table emi_history | Exact match (144,000 rows) | Matched (144,000 rows) | **PASS** |
| `SQL_CSV_MATCH_PAYMENT_HISTORY` | `payment_history` | Reconcile row count between payment_history.csv and SQLite table payment_history | Exact match (144,000 rows) | Matched (144,000 rows) | **PASS** |
| `SQL_CSV_MATCH_CREDIT_BUREAU` | `credit_bureau` | Reconcile row count between credit_bureau.csv and SQLite table credit_bureau | Exact match (12,000 rows) | Matched (12,000 rows) | **PASS** |
| `SQL_CSV_MATCH_TRANSACTION_HISTORY` | `transaction_history` | Reconcile row count between transaction_history.csv and SQLite table transaction_history | Exact match (144,000 rows) | Matched (144,000 rows) | **PASS** |
| `SQL_CSV_MATCH_NPA_HISTORY` | `NPA_History` | Reconcile row count between NPA_History.csv and SQLite table NPA_History | Exact match (115,512 rows) | Matched (115,512 rows) | **PASS** |
| `SQL_CSV_MATCH_CUSTOMER_COMPANY_DETAILS` | `customer_company_details` | Reconcile row count between customer_company_details.csv and SQLite table customer_company_details | Exact match (12,000 rows) | Matched (12,000 rows) | **PASS** |
| `SQL_CSV_MATCH_FUTURE_REPAYMENT_SIMULATION` | `future_repayment_simulation` | Reconcile row count between future_repayment_simulation.csv and SQLite table future_repayment_simulation | Exact match (60,000 rows) | Matched (60,000 rows) | **PASS** |
| `SQL_CSV_MATCH_FUTURE_OUTCOME` | `future_outcome` | Reconcile row count between future_outcome.csv and SQLite table future_outcome | Exact match (10,000 rows) | Matched (10,000 rows) | **PASS** |
| `SQL_CSV_MATCH_NPA_CUSTOMER_SPLIT` | `NPA_CUSTOMER_SPLIT` | Reconcile row count between NPA_CUSTOMER_SPLIT.csv and SQLite table NPA_CUSTOMER_SPLIT | Exact match (12,000 rows) | Matched (12,000 rows) | **PASS** |
| `SQL_CSV_MATCH_NPA_HISTORY_CUSTOMER_SUMMARY` | `npa_history_customer_summary` | Reconcile row count between npa_history_customer_summary.csv and SQLite table npa_history_customer_summary | Exact match (12,000 rows) | Matched (12,000 rows) | **PASS** |

---

## 9. Conclusion and Next Steps

All mandatory data engineering, business rule, population isolation, and mathematical reconciliation checks have **PASSED**. The package is fully prepared and ready for upload into SAS Viya for Learners.
