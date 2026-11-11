# 07_SCORED_OUTPUT - Webpage Scored Output Handoff Contract

## 1. Directory Purpose & Handoff Policy

This directory is the official designated landing folder for validated SAS Viya scoring outputs:

- **Exact Directory Path**: `NPA_DATA_PIPELINE/07_SCORED_OUTPUT/`
- **Handoff Mechanism**: After executing the champion model score code in SAS Viya and running `npa_postprocess_scores.sas`, download the resulting scored CSV files and place them into this folder.
- **Consumption Principle**: Any future customer-level risk summaries, display cards, and explanation views on the NPA dashboard must be sourced **strictly and exclusively** from `NPA_SCORING_RESULTS.csv`.
- **Anti-Contamination Rule**:
  - Never generate customer risk summaries from raw source datasets, training data, test data, future repayment simulations, future outcome tables, or target-generation metadata.
  - Never mix `NPA_MODEL_TEST_SCORED.csv` into the live customer scoring population. `NPA_MODEL_TEST_SCORED.csv` is reserved solely for independent out-of-sample model evaluation.

---

## 2. File Contract Specifications

### A. Primary Customer Scoring Output: `NPA_SCORING_RESULTS.csv`

- **Purpose**: Primary customer-level input for live customer risk displays and explainability.
- **Population**: Exactly 2,000 separate scoring customers (IDs 10,001 to 12,000).
- **Unique Key**: `customer_id` (Integer, Primary Key, Unique, Non-null).
- **Expected Probability Range**: `model_event_probability` must be a float bounded in `[0.0000, 1.0000]`.
- **Expected Risk Grades**: Exactly one of `['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']`.
- **Required Columns & Data Types**:

| Column Name | Inferred Type | Constraint / Valid Range | Description |
|---|---|---|---|
| `customer_id` | `int64` | `10001` to `12000` (Unique) | Unique customer identifier. |
| `scoring_run_id` | `str` | Non-empty string (e.g. `RUN_YYYYMMDD_XX`) | Identifier for the scoring execution batch. |
| `scoring_timestamp` | `str` | ISO 8601 (`YYYY-MM-DDTHH:MM:SS`) | Timestamp when score code executed. |
| `age` | `int64` | `21` to `70` | Customer age in years. |
| `gender` | `str` | `'M'`, `'F'` | Customer gender. |
| `marital_status` | `str` | `'MARRIED'`, `'SINGLE'` | Marital status. |
| `occupation` | `str` | `'SALARIED'`, `'BUSINESS'`, `'SELF_EMPLOYED'`, `'PROFESSIONAL'` | Primary occupation. |
| `monthly_income` | `int64` | `25,000` to `350,000` | Net verified monthly income in INR. |
| `employment_years` | `float64` | `>= 0` | Career experience in years. |
| `city_type` | `str` | `'METRO'`, `'URBAN'`, `'SEMI_URBAN'`, `'RURAL'` | Residence city classification. |
| `loan_id` | `int64` | Unique integer | Current active loan identifier. |
| `loan_type` | `str` | `'HOME'`, `'PERSONAL'`, `'AUTO'`, `'BUSINESS'` | Loan product category. |
| `sanctioned_amount` | `float64` | `100,000` to `5,000,000` | Original sanctioned loan principal. |
| `outstanding_amount` | `float64` | `0 < outstanding < sanctioned` | Current outstanding loan balance. |
| `emi_amount` | `float64` | Positive float | Contractual monthly installment. |
| `interest_rate` | `float64` | `7.0` to `17.0` | Annual interest rate percentage. |
| `collateral_value` | `float64` | Positive float | Assessed collateral value. |
| `loan_age_months` | `int64` | `>= 12` | Elapsed tenure in months. |
| `remaining_tenure` | `int64` | `>= 6` | Remaining contractual tenure. |
| `credit_score` | `int64` | `300` to `900` | Bureau credit score. |
| `total_credit_limit` | `float64` | Positive float | Total bureau credit limit. |
| `total_credit_balance`| `float64` | `<= total_credit_limit` | Total bureau outstanding balance. |
| `flag_high_emi_burden` | `int64` | `0`, `1` | Rule flag: EMI / Income > 40%. |
| `flag_high_credit_utilization` | `int64` | `0`, `1` | Rule flag: Bureau balance / Limit > 75%. |
| `flag_low_credit_score` | `int64` | `0`, `1` | Rule flag: Credit score < 650. |
| `flag_high_outstanding_ratio` | `int64` | `0`, `1` | Rule flag: Outstanding / Sanctioned > 85%. |
| `flag_previous_npa` | `int64` | `0`, `1` | Rule flag: Verified prior NPA event. |
| `flag_prior_missed_streak` | `int64` | `0`, `1` | Rule flag: Prior missed streak >= 3 months. |
| `flag_company_financial_stress` | `int64` | `0`, `1` | Rule flag: Employer/business stress trigger. |
| `flag_negative_turnover_growth` | `int64` | `0`, `1` | Rule flag: Turnover growth < -5%. |
| `flag_low_current_ratio` | `int64` | `0`, `1` | Rule flag: Business current ratio < 1.0. |
| `flag_unstable_transaction_cashflow` | `int64` | `0`, `1` | Rule flag: Outflows > 90% of inflows. |
| `flag_history_unavailable` | `int64` | `0`, `1` | Rule flag: Prior history unavailable. |
| `internal_risk_flag_count` | `int64` | `0` to `11` | Sum of internal rule flags. |
| `internal_rule_risk_grade` | `str` | `'LOW'`, `'MEDIUM'`, `'HIGH'`, `'CRITICAL'` | Rule-based triage grade. |
| `risk_reason_1` | `str` | Non-empty explanation | Primary ordered explanation factor. |
| `risk_reason_2` | `str` | Non-empty explanation | Secondary ordered explanation factor. |
| `risk_reason_3` | `str` | Non-empty explanation | Tertiary / additional explanation factor. |
| `model_event_probability` | `float64` | `0.0000` to `1.0000` | Scored model predicted NPA probability. |
| `model_predicted_class` | `int64` | `0`, `1` | Model classification at decision cutoff. |
| `model_risk_grade` | `str` | `'LOW'`, `'MEDIUM'`, `'HIGH'`, `'CRITICAL'` | Model risk band mapped from probability. |
| `recommended_action` | `str` | Standard operational labels | Recommended portfolio action. |

---

### B. Independent Test Evaluation Output: `NPA_MODEL_TEST_SCORED.csv`

- **Purpose**: Independent verification of model performance on unseen development customers.
- **Population**: Exactly 3,000 independent test customers.
- **Required Columns**:
  - `customer_id` (`int64`, Unique)
  - `npa_flag` (`int64`: `0`, `1` - actual simulated ground truth)
  - `model_event_probability` (`float64`: `0.0000` to `1.0000`)
  - `model_predicted_class` (`int64`: `0`, `1`)
  - `model_risk_grade` (`str`: `'LOW'`, `'MEDIUM'`, `'HIGH'`, `'CRITICAL'`)

---

### C. Champion Model Metrics Summary: `NPA_MODEL_METRICS.csv`

- **Purpose**: Official audit summary of out-of-sample model evaluation metrics.
- **Required Columns**:
  - `metric_name` (`str`)
  - `metric_value` (`str` / `float64`)
  - `metric_description` (`str`)
- **Key Metrics Included**:
  - `test_population_size` (3,000)
  - `test_positive_events` (Actual default count in test set)
  - `test_negative_events` (Actual performing count in test set)
  - `event_rate_pct` (Observed test set default rate)
  - `classification_threshold` (Cutoff used for binary classification)
  - `true_positives` (TP)
  - `false_positives` (FP)
  - `true_negatives` (TN)
  - `false_negatives` (FN)
  - `accuracy_pct`
  - `sensitivity_recall_pct`
  - `specificity_pct`
  - `precision_pct`
  - `f1_score`

---

## 3. Validation Rules Before Accepting Scored Output

Before the webpage or downstream API ingests `NPA_SCORING_RESULTS.csv`, the ingestion service must verify:

1. **File Existence & Non-Emptiness**: File size > 0 bytes; UTF-8 encoded.
2. **Row Count Match**: Exactly 2,000 rows (excluding header).
3. **Primary Key Integrity**: Zero nulls in `customer_id`; all 2,000 IDs are distinct and belong to the scoring population (IDs 10,001 to 12,000).
4. **Probability Bounds**: Every `model_event_probability` satisfies `0.0 <= p <= 1.0`.
5. **Risk Band Reconciliation**:
   - `model_event_probability < 0.10` $\implies$ `model_risk_grade == 'LOW'` and `recommended_action == 'NORMAL MONITORING'`
   - `0.10 <= model_event_probability < 0.30` $\implies$ `model_risk_grade == 'MEDIUM'` and `recommended_action == 'REMINDER'`
   - `0.30 <= model_event_probability < 0.60` $\implies$ `model_risk_grade == 'HIGH'` and `recommended_action == 'COLLECTION CALL'`
   - `model_event_probability >= 0.60` $\implies$ `model_risk_grade == 'CRITICAL'` and `recommended_action == 'RECOVERY TEAM'`
6. **Zero Target Leakage**: Confirm that `npa_flag`, `future_month`, and `outstanding_arrears` are **not present** in the file.

---

## 4. Webpage Integration Status & Future Path

- **Current State**: The existing prototype webpage (`web_app.py`) reads directly from `bank_data.db` (`NPA_MASTER_10K`).
- **Preservation Policy**: Per project instructions, `web_app.py`, `bank_data.db`, and frontend code were **not modified** during this task.
- **Future Integration Path**: Once authorized, a lightweight adapter or ingestion script can load `NPA_SCORING_RESULTS.csv` into a dedicated table (e.g. `NPA_SCORED_CUSTOMERS`) or update the SQLite database so the frontend displays live scored customers from SAS Viya.

