# SAS Viya Execution & Run Instructions

This guide provides the complete operational sequence for running the NPA Early Detection SAS pipeline in **SAS Viya for Learners** or standard **SAS Studio**.

---

## 1. Prerequisites and Setup in SAS Viya for Learners

1. Log into your **SAS Viya for Learners** account and launch **SAS Studio**.
2. In the **Explorer** panel (left side), navigate to your home directory (`Files/home/<user_id>`).
3. Create a folder named `NPA_DATA_PIPELINE`.
4. Upload the following directories and files from this package into `NPA_DATA_PIPELINE`:
   - `01_RAW_DATASETS/` (contains all 9 raw CSVs)
   - `02_FUTURE_SIMULATION_AND_TARGET/` (contains `future_outcome.csv` and `future_repayment_simulation.csv`)
   - `03_POPULATION_AND_SAS_INPUTS/` (contains `NPA_CUSTOMER_SPLIT.csv`)
   - `05_SAS_PROGRAMS/` (contains the 4 SAS programs)
5. Create empty target folders in your SAS workspace:
   - `06_SAS_OUTPUTS/`
   - `07_SCORED_OUTPUT/`

> [!IMPORTANT]
> **No Direct SQLite Connection**: SAS Viya for Learners runs in a cloud container without direct ODBC/SQLite connectivity to your local machine. All data handoff is performed strictly via CSV file uploads and CAS table loads.

---

## 2. Program Execution Order

Run the programs in the strict numerical order below:

```text
Step 1: npa_import_and_qa.sas
   ↓
Step 2: npa_feature_engineering_and_flags.sas
   ↓
Step 3: npa_prepare_model_datasets.sas
   ↓
Step 4: [Model Studio Training & Scoring] (See Section 3)
   ↓
Step 5: npa_postprocess_scores.sas
```

---

### Step 1: `npa_import_and_qa.sas`

- **Purpose**: Imports all raw CSV files, the customer split, and the target into SAS `work` or `caslib`. Runs automated data quality checks.
- **Action**:
  1. Open `05_SAS_PROGRAMS/npa_import_and_qa.sas` in SAS Studio.
  2. Update the macro variable at the top with your SAS home path:
     ```sas
     %let data_dir = /home/&sysuserid/NPA_DATA_PIPELINE;
     %let use_cas  = 0; /* Set to 1 if using CAS library */
     %let caslib   = casuser;
     ```
  3. Submit the program (press `F3` or click Run).
  4. Inspect the SAS Log:
     - Verify that all row counts match:
       - `customer_master`: 12,000
       - `loan_account`: 12,000
       - `emi_history`: 144,000
       - `payment_history`: 144,000
       - `credit_bureau`: 12,000
       - `transaction_history`: 144,000
       - `NPA_History`: 115,512
       - `customer_company_details`: 12,000
       - `NPA_CUSTOMER_SPLIT`: 12,000
       - `future_outcome`: 10,000
     - Verify zero DQ errors reported.

---

### Step 2: `npa_feature_engineering_and_flags.sas`

- **Purpose**: Aggregates transaction data, calculates financial ratios (`emi_income_ratio`, `credit_utilization`, `debt_to_income`, `loan_to_value`), evaluates 11 internal business risk flags, and assigns prototype rule grades (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Action**:
  1. Open `05_SAS_PROGRAMS/npa_feature_engineering_and_flags.sas`.
  2. Submit the program.
  3. Inspect the frequency table of `internal_rule_risk_grade` and `internal_risk_flag_count` in the Results tab.

---

### Step 3: `npa_prepare_model_datasets.sas`

- **Purpose**: Creates the three final, standardized, non-leaking datasets:
  - `work.NPA_MODEL_TRAIN` (7,000 customers, labelled with `npa_flag`)
  - `work.NPA_MODEL_TEST` (3,000 customers, labelled with `npa_flag`, disjoint from Train)
  - `work.NPA_SCORING_INPUT` (2,000 customers, completely unlabelled, NO target)
- **Action**:
  1. Open `05_SAS_PROGRAMS/npa_prepare_model_datasets.sas`.
  2. Submit the program.
  3. Check the export logs to confirm CSV files were written to `06_SAS_OUTPUTS/`.

---

## 3. Training & Scoring in SAS Model Studio

1. In SAS Viya, open the Applications menu (top left) and select **Build Models (Model Studio)**.
2. Click **New Project**:
   - **Name**: `NPA_Early_Detection`
   - **Type**: `Data Mining and Machine Learning`
   - **Data**: Select `NPA_MODEL_TRAIN` (from your CAS library or upload `NPA_MODEL_TRAIN.csv`).
3. Set Metadata Roles:
   - `npa_flag`: **Target** (Binary/Nominal, Event level = `1`)
   - `customer_id`, `loan_id`: **Key / ID** (Excluded from inputs)
   - All engineered ratios, transaction aggregates, bureau metrics, company indicators, and internal flags: **Input**
   - Confirm that no future simulation or target probability fields exist in the dataset.
4. Run Pipeline:
   - Add **Logistic Regression**, **Decision Tree**, and **Gradient Boosting** nodes.
   - Run the pipeline and inspect champion model selection (based on Validation KS / Misclassification / ROC AUC).
5. Score Datasets:
   - Right-click the Champion model and select **Download Score Code**.
   - Apply score code to `NPA_MODEL_TEST` (to produce test predictions for evaluation).
   - Apply score code to `NPA_SCORING_INPUT` (to produce live customer predictions).

---

### Step 4: `npa_postprocess_scores.sas`

- **Purpose**: Enforces the webpage handoff contract, maps model event probabilities, maps risk grades and recommended actions, calculates independent test evaluation metrics, and exports CSVs.
- **Action**:
  1. Open `05_SAS_PROGRAMS/npa_postprocess_scores.sas`.
  2. Update the `%let data_dir` and `%let threshold` (default = 0.30).
  3. Submit the program.
  4. Verify that the following files are produced in `07_SCORED_OUTPUT/`:
     - `NPA_SCORING_RESULTS.csv` (2,000 rows)
     - `NPA_MODEL_TEST_SCORED.csv` (3,000 rows)
     - `NPA_MODEL_METRICS.csv` (Evaluation metrics: AUC, KS, Confusion Matrix, Recall, Precision, F1)
  5. Download `NPA_SCORING_RESULTS.csv` from SAS Studio to your local `NPA_DATA_PIPELINE/07_SCORED_OUTPUT/` folder.

