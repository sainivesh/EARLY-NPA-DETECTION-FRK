# NPA Early Detection - End-to-End Data Lineage & Architecture

This document details the data provenance, transformation logic, and architectural flow of the synthetic data generation, SAS Viya analytical processing, Model Studio machine learning, and downstream webpage consumption.

---

## 1. End-to-End Architecture & Data Flow

```mermaid
flowchart TD
    subgraph S1["1. Local Python Generation Engine"]
        GEN["generate_npa_data.py<br/>(Seed: 20260814)"]
        CM["customer_master.csv<br/>(12,000 rows)"]
        LA["loan_account.csv<br/>(12,000 rows)"]
        EH["emi_history.csv<br/>(144,000 rows - 12m clean)"]
        PH["payment_history.csv<br/>(144,000 rows - 12m clean)"]
        CB["credit_bureau.csv<br/>(12,000 rows - clean)"]
        TH["transaction_history.csv<br/>(144,000 rows - non-EMI debits)"]
        NH["NPA_History.csv<br/>(115,512 rows - 24m prior loan)"]
        CCD["customer_company_details.csv<br/>(12,000 rows - 30 cols)"]
        NHS["npa_history_customer_summary.csv<br/>(12,000 rows - summary)"]
        
        GEN --> CM & LA & EH & PH & CB & TH & NH & CCD & NHS
    end

    subgraph S2["2. Local Storage & Validation Layer"]
        SQL[("npa_project.sqlite<br/>(Unified Local DB)")]
        VAL["08_VALIDATION/npa_validate_data.py"]
        REP["NPA_VALIDATION_REPORT.md<br/>& Results CSV (61/61 PASS)"]
        
        CM & LA & EH & PH & CB & TH & NH & CCD & NHS --> SQL
        SQL --> VAL --> REP
    end

    subgraph S3["3. Future Repayment Simulation & Target"]
        FRS["future_repayment_simulation.csv<br/>(60,000 rows - 6m simulation<br/>10,000 labelled dev only)"]
        FO["future_outcome.csv<br/>(10,000 rows: npa_flag=1 if DPD>=90)"]
        SPLIT["NPA_CUSTOMER_SPLIT.csv<br/>(Train: 7,000 | Test: 3,000 | Scoring: 2,000)"]
        
        GEN --> FRS --> FO
        GEN --> SPLIT
        FRS & FO & SPLIT --> SQL
    end

    subgraph S4["4. SAS Viya Analytical Pipeline"]
        SAS1["05_SAS_PROGRAMS/npa_import_and_qa.sas<br/>(CSV Import & Rigorous DQ)"]
        SAS2["05_SAS_PROGRAMS/npa_feature_engineering_and_flags.sas<br/>(Ratios + 11 Internal Risk Flags)"]
        SAS3["05_SAS_PROGRAMS/npa_prepare_model_datasets.sas<br/>(Train, Test, Scoring Partitioning)"]
        
        CM & LA & CB & TH & CCD & NHS & SPLIT --> SAS1
        FO -.->|Target Attachment Only| SAS1
        SAS1 --> SAS2 --> SAS3
    end

    subgraph S5["5. Model Studio Datasets"]
        TRAIN["NPA_MODEL_TRAIN.csv<br/>(7,000 dev rows + npa_flag)"]
        TEST["NPA_MODEL_TEST.csv<br/>(3,000 dev rows + npa_flag)"]
        SCORING_IN["NPA_SCORING_INPUT.csv<br/>(2,000 scoring rows - NO target)"]
        
        SAS3 --> TRAIN & TEST & SCORING_IN
    end

    subgraph S6["6. Model Studio & Champion Scoring"]
        MS["SAS Model Studio<br/>(Logistic, Tree, Forest, Gradient Boosting)"]
        CHAMP["Champion Model Score Code"]
        SAS4["05_SAS_PROGRAMS/npa_postprocess_scores.sas"]
        
        TRAIN --> MS --> CHAMP
        CHAMP & TEST --> SAS4
        CHAMP & SCORING_IN --> SAS4
    end

    subgraph S7["7. Final Scored Deliverables & Webpage Contract"]
        SCR["07_SCORED_OUTPUT/NPA_SCORING_RESULTS.csv<br/>(2,000 live scored customers for Webpage)"]
        TST_SCR["07_SCORED_OUTPUT/NPA_MODEL_TEST_SCORED.csv<br/>(3,000 independent evaluation rows)"]
        METRICS["07_SCORED_OUTPUT/NPA_MODEL_METRICS.csv<br/>(Test AUC, KS, Confusion Matrix, F1)"]
        WEB["Existing NPA Webpage Dashboard<br/>(Human Review & Explanation)"]
        
        SAS4 --> SCR & TST_SCR & METRICS
        SCR -.->|Handoff via Contract| WEB
    end
```

---

## 2. Source-to-Target Feature Transformation Mapping

The analytical base table is built by combining current loan, bureau, transaction, prior history, and company metrics:

| Engineered Feature / Flag | Formula / Transformation Source | Business Rationale & Guardrail |
|---|---|---|
| `emi_income_ratio` | `emi_amount / max(1, monthly_income)` | Installment burden relative to regular income. |
| `outstanding_ratio` | `outstanding_amount / max(1, sanctioned_amount)` | Proportion of principal remaining unpaid. |
| `credit_utilization` | `total_credit_balance / max(1, total_credit_limit)` | Utilization of revolving credit facilities across bureau. |
| `loan_to_value` | `sanctioned_amount / max(1, collateral_value)` | Exposure security coverage ratio. |
| `debt_to_income` | `(emi_amount + (total_debit_transaction / 12)) / max(1, monthly_income)` | Total monthly debt and lifestyle outflow burden. Excludes loan EMI from debit to prevent double-counting. |
| `cash_withdrawal_ratio` | `total_cash_withdrawal / max(1, total_debit_transaction)` | Cash extraction intensity from bank accounts. |
| `credit_to_income_ratio` | `(total_credit_transaction / 12) / max(1, monthly_income)` | Turnover cash-flow velocity relative to declared income. |
| `flag_high_emi_burden` | `emi_income_ratio > 0.40` | Binary trigger for elevated installment commitments. |
| `flag_high_credit_utilization` | `credit_utilization > 0.75` | Binary trigger for near-limit revolving credit usage. |
| `flag_low_credit_score` | `credit_score < 650` | External bureau risk score below prime benchmark. |
| `flag_high_outstanding_ratio` | `outstanding_ratio > 0.85` | Unamortized or seasoned loan with high principal exposure. |
| `flag_previous_npa` | `previous_npa_flag = 1` | Verified default event in historical loan cycle. |
| `flag_prior_missed_streak` | `max_consecutive_missed_months >= 3` | Chronic delinquency streak in previous borrowing history. |
| `flag_company_financial_stress` | `financial_stress_flag_synthetic = 1` | Associated employer/business under synthetic financial strain. |
| `flag_negative_turnover_growth` | `turnover_growth_pct < -5.0` | Revenue contraction in customer's commercial ecosystem. |
| `flag_low_current_ratio` | `current_ratio < 1.0` (for business/practice) | Operating liquidity deficit in customer-owned entity. |
| `flag_unstable_transaction_cashflow` | `total_debit_transaction > total_credit_transaction * 0.90` | Account outflows approaching or exceeding total inflows. |
| `flag_history_unavailable` | `history_available = 0` | Customer lacks previous borrowing history; flagged explicitly without inferring clean repayment. |
| `internal_risk_flag_count` | Sum of 11 internal binary flags | Transparent, unweighted rule risk composite (0 to 11). |
| `internal_rule_risk_grade` | Mapped from flag count: 0-1 (LOW), 2-3 (MEDIUM), 4-5 (HIGH), 6+ (CRITICAL) | Rule-based triage grade, strictly decoupled from ML model probability. |

---

## 3. Data Leakage Elimination & Integrity Safeguards

1. **Strict Current-Loan Non-Delinquency**:
   - Current loans reflect performing status across all 12 observed months (`days_past_due = 0`, `npa_indicator = 0`, `payment_delay = 0`, `bounce_flag = 0`, `late_payment_flag = 0`).
   - Credit bureau reports 0 overdue accounts, 0 bureau DPD, and 0 write-offs at the observation date.
   - Prevents trivial shortcut learning where models rely on current delinquency to predict future delinquency.

2. **Chronological Separation of Prior History**:
   - `NPA_History.csv` covers a past borrowing cycle that concluded and matured/resolved before the current loan disbursal date (`prior_loan_end_date < current_loan_start_date`).
   - Customers without historical records have no synthetic rows generated; their status is represented as `history_available = 0`.

3. **Future Repayment Simulation vs. Supervised Target**:
   - The future 6-month repayment schedule is generated solely for the 10,000 development customers.
   - `future_outcome.csv` derives `npa_flag = 1` if cumulative simulated DPD reaches 90 days.
   - The monthly simulation records (`future_repayment_simulation.csv`) are strictly quarantined and never fed into SAS feature engineering or model training.
   - No target probability generator scores (`npa_probability_actual`) are included in model training files.

4. **Absolute Partition Isolation**:
   - Training (`NPA_MODEL_TRAIN`, 7,000 customers) and Independent Testing (`NPA_MODEL_TEST`, 3,000 customers) are mutually exclusive.
   - The Scoring population (`NPA_SCORING_INPUT`, 2,000 customers) has zero overlap with development, possesses no future simulation rows, and contains no target flag.

