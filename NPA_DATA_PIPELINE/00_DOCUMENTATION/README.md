# NPA Early Detection - Complete Synthetic Data Package, SAS Pipeline & Validation

## 1. Project Overview

This repository package provides an end-to-end synthetic data generation, SAS Viya for Learners handoff, and quality validation pipeline for the **NPA Early Detection** project.

It has been constructed under **strict project-preservation rules**:
- All deliverables are maintained in this isolated `NPA_DATA_PIPELINE` directory.
- Existing project files (`bank_data.db`, `clean_data.py`, `export_data.py`, `main.py`, `npa_assessment.py`, `NPA_RAG_Knowledge_Base.md`, `templates/`, `web_app.py`) remain completely untouched.
- Git history and repository configuration are preserved without alteration.

---

## 2. Population Structure

The package generates **12,000 unique customers** across three strictly disjoint populations:

| Population Segment | Customer Count | Target Status | Purpose |
|---|---:|---|---|
| **Development - Train** | 7,000 | Labelled (`npa_flag` in 0, 1) | Model Studio model training |
| **Development - Test** | 3,000 | Labelled (`npa_flag` in 0, 1) | Completely independent champion evaluation |
| **Separate Scoring** | 2,000 | **Unlabelled** (No target/future data) | Live scoring & webpage handoff |
| **Total** | **12,000** | | |

- **Stratified Partitioning**: The 10,000 development customers are split 70:30 into Train and Test using fixed random seed `20260814`, stratified by `npa_flag`.
- **Target Rate Calibration**: Positive NPA outcomes occur naturally through simulated 6-month repayment delinquency (DPD >= 90 days), producing an observed **12.16%** positive event rate (1,216 positive events across the 10,000 development population), safely inside the **8%–15%** prototype design target.
- **Scoring Population Isolation**: The 2,000 scoring customers have zero future simulation rows, zero future outcome rows, and zero target leakage.

---

## 3. Directory Layout

```text
NPA_DATA_PIPELINE/
├── 00_DOCUMENTATION/
│   ├── README.md                          <- This master documentation file
│   ├── DATA_DICTIONARY.csv                <- Comprehensive 132-field data dictionary
│   ├── DATA_LINEAGE.md                    <- Mermaid architecture, data lineage & transformations
│   ├── SAS_VIYA_UPLOAD_GUIDE.md           <- Step-by-step CSV upload & CAS ingestion guide
│   └── MODEL_STUDIO_SETUP.md              <- Model Studio project configuration & ML guide
│
├── 01_RAW_DATASETS/
│   ├── customer_master.csv                <- 12,000 rows (customer demographics & income)
│   ├── loan_account.csv                   <- 12,000 rows (active performing current loans, age >= 12)
│   ├── emi_history.csv                    <- 144,000 rows (12 months clean, emi_paid=due, DPD=0)
│   ├── payment_history.csv                <- 144,000 rows (12 months clean, delay=0, bounce=0)
│   ├── credit_bureau.csv                  <- 12,000 rows (bureau snapshot, overdue=0, bureau DPD=0)
│   ├── transaction_history.csv            <- 144,000 rows (12 months cashflow, non-EMI debits)
│   ├── NPA_History.csv                    <- 115,512 rows (24-month prior loan cycle for sample)
│   ├── customer_company_details.csv       <- 12,000 rows (30-column enterprise context, no truncation)
│   └── npa_history_customer_summary.csv   <- 12,000 rows (customer-level prior history summary)
│
├── 02_FUTURE_SIMULATION_AND_TARGET/
│   ├── future_repayment_simulation.csv    <- 60,000 rows (6-month forward simulation for 10k dev only)
│   └── future_outcome.csv                 <- 10,000 rows (npa_flag=1 if simulated DPD >= 90)
│
├── 03_POPULATION_AND_SAS_INPUTS/
│   └── NPA_CUSTOMER_SPLIT.csv             <- 12,000 rows (Train: 7,000 | Test: 3,000 | Scoring: 2,000)
│
├── 04_SQL_DATABASE/
│   └── npa_project.sqlite                 <- Complete local SQLite database with all tables & indexes
│
├── 05_SAS_PROGRAMS/
│   ├── npa_import_and_qa.sas              <- Step 1: SAS CSV import & data quality checks
│   ├── npa_feature_engineering_and_flags.sas <- Step 2: Financial ratios & 11 internal risk flags
│   ├── npa_prepare_model_datasets.sas     <- Step 3: Train, Test, and Scoring partitioning
│   ├── npa_postprocess_scores.sas         <- Step 4: Champion post-processing & metrics calculation
│   └── SAS_RUN_INSTRUCTIONS.md            <- Detailed execution instructions in SAS Viya
│
├── 06_SAS_OUTPUTS/
│   └── README.md                          <- SAS staging and export documentation
│
├── 07_SCORED_OUTPUT/
│   └── README.md                          <- Webpage scored-output contract & validation rules
│
├── 08_VALIDATION/
│   ├── npa_validate_data.py               <- Independent Python validation script
│   ├── NPA_VALIDATION_REPORT.md           <- Executed audit report (61/61 rules PASS)
│   ├── NPA_VALIDATION_RESULTS.csv         <- Rule-by-rule audit results CSV
│   └── NPA_GENERATION_METADATA.json       <- Seed, timestamp, schema version & population counts
│
├── generate_npa_data.py                   <- Master Python data generator script
└── requirements.txt                       <- Python dependencies
```

---

## 4. Key Implementation Highlights & Corrections

1. **Strict Current-Loan Clean Performance**:
   - Unlike earlier prototypes that allowed current loans to exhibit DPD up to 89, every current loan observation is **100% performing and non-delinquent** (`days_past_due = 0`, `npa_indicator = 0`, `payment_delay = 0`, `bounce_flag = 0`, `late_payment_flag = 0`).
   - Current credit bureau records reflect zero overdue accounts, zero bureau DPD, and zero historical write-offs.

2. **Full Implementation of 7 Prior-Loan Repayment Patterns**:
   - `NPA_History.csv` covers a distinct earlier borrowing cycle that concluded before the current loan began.
   - All 7 patterns are fully implemented: `ALL_PAID_ON_TIME`, `OCCASIONAL_LATE_BUT_CURED`, `INTERMITTENT_MISSED_REPAID`, `PAID_3_MONTHS_THEN_STOPPED`, `PAID_6_MONTHS_THEN_STOPPED`, `PRIOR_NPA_UNRESOLVED`, and `PRIOR_NPA_RESOLVED_RECOVERED`.
   - Missing history is explicitly represented as `history_available = 0`, preventing unavailable records from being misconstrued as clean repayment.

3. **String Truncation Bug Eliminated**:
   - `customer_company_details.csv` strictly prevents NumPy fixed-width string truncation. Values such as `PROFESSIONAL_PRACTICE` are verified intact with **0 truncated strings**.

4. **True Multi-Month Repayment Simulation**:
   - Rather than drawing target flags from a static random Bernoulli distribution, `future_repayment_simulation.csv` models genuine month-by-month repayment schedules over 6 future months.
   - Overdue installments carry arrears forward, DPD is calculated from the oldest unpaid installment, and NPA occurs strictly when DPD reaches 90 days.
   - Target reconciliation between simulation and `future_outcome.csv` is **100% verified (0 mismatches)**.

---

## 5. Quick Start Execution

### Step 1: Generate or Inspect Synthetic Data
```bash
python NPA_DATA_PIPELINE/generate_npa_data.py --output-dir NPA_DATA_PIPELINE
```

### Step 2: Run Independent Validation
```bash
python NPA_DATA_PIPELINE/08_VALIDATION/npa_validate_data.py --root-dir NPA_DATA_PIPELINE
```

### Step 3: Handoff to SAS Viya for Learners
Follow the instructions in:
- `00_DOCUMENTATION/SAS_VIYA_UPLOAD_GUIDE.md`
- `05_SAS_PROGRAMS/SAS_RUN_INSTRUCTIONS.md`
- `00_DOCUMENTATION/MODEL_STUDIO_SETUP.md`

