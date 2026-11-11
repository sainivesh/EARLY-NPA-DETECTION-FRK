# SAS Viya for Learners - Manual Upload & CAS Ingestion Guide

This guide describes how to upload the generated synthetic CSV datasets and SAS programs into **SAS Viya for Learners** (or standard SAS Studio) and execute the analytical pipeline.

---

## 1. Architectural Architecture Notice

> [!IMPORTANT]
> **No Direct SQLite-to-SAS Viya Connection**:
> SAS Viya for Learners operates in a secure cloud container. It does not provide direct ODBC or network sockets to your local SQLite database file (`npa_project.sqlite`).
> 
> Therefore, data handoff occurs strictly through **CSV file uploads** via SAS Studio. Local SQLite serves as the permanent local storage, query, and audit repository, while CSV files act as the transport mechanism to SAS Viya.

---

## 2. Directory Preparation in SAS Studio

1. Open **SAS Viya for Learners** in your web browser and launch **SAS Studio**.
2. In the navigation pane on the left, click **Explorer** (the folder icon).
3. Under **Files (Home)**, create a project folder named:
   ```text
   NPA_DATA_PIPELINE
   ```
4. Within `NPA_DATA_PIPELINE`, create the following subdirectories:
   ```text
   01_RAW_DATASETS
   02_FUTURE_SIMULATION_AND_TARGET
   03_POPULATION_AND_SAS_INPUTS
   05_SAS_PROGRAMS
   06_SAS_OUTPUTS
   07_SCORED_OUTPUT
   ```

---

## 3. Uploading Files to SAS Studio

You can upload files using the SAS Studio UI:

1. Right-click on `01_RAW_DATASETS` in SAS Studio Explorer, select **Upload Files...**, and upload:
   - `customer_master.csv`
   - `loan_account.csv`
   - `emi_history.csv`
   - `payment_history.csv`
   - `credit_bureau.csv`
   - `transaction_history.csv`
   - `NPA_History.csv`
   - `customer_company_details.csv`
   - `npa_history_customer_summary.csv`
2. Right-click on `02_FUTURE_SIMULATION_AND_TARGET`, select **Upload Files...**, and upload:
   - `future_outcome.csv`
   - `future_repayment_simulation.csv`
3. Right-click on `03_POPULATION_AND_SAS_INPUTS`, select **Upload Files...**, and upload:
   - `NPA_CUSTOMER_SPLIT.csv`
4. Right-click on `05_SAS_PROGRAMS`, select **Upload Files...**, and upload:
   - `npa_import_and_qa.sas`
   - `npa_feature_engineering_and_flags.sas`
   - `npa_prepare_model_datasets.sas`
   - `npa_postprocess_scores.sas`
   - `SAS_RUN_INSTRUCTIONS.md`

*(Alternatively, if your browser supports folder drag-and-drop, you can drag the folders directly into your SAS Studio Files area.)*

---

## 4. Configuring Path Macro Variables

In SAS Viya on Linux containers, your home path is typically:
```sas
/home/<your_viya_username>/NPA_DATA_PIPELINE
```
To verify your exact home path:
1. Open a new SAS program tab in SAS Studio.
2. Run:
   ```sas
   %put User Home Directory = %sysget(HOME);
   ```
3. Check the SAS Log to see your exact Linux home directory path.
4. In each of the 4 SAS programs, update the `%let data_dir` statement at the top:
   ```sas
   %let data_dir = /home/<your_viya_username>/NPA_DATA_PIPELINE;
   ```

---

## 5. Working with SAS WORK vs. Cloud Analytic Services (CAS)

The SAS programs are designed to run in two modes:

### Mode A: Standard SAS WORK Library (Default, Recommended for Simplicity)
- Leave `%let use_cas = 0;` at the top of the SAS programs.
- All intermediate datasets (`work.customer_master`, `work.npa_features_with_flags`, `work.NPA_MODEL_TRAIN`, etc.) are processed in high-speed SAS WORK memory.
- Output datasets are exported directly to CSV in `06_SAS_OUTPUTS/` and `07_SCORED_OUTPUT/`.

### Mode B: In-Memory CAS Tables (For Model Studio Integration)
- Set `%let use_cas = 1;` and `%let caslib = casuser;`.
- The programs will establish a CAS session (`cas mycas;`), load the prepared tables into CAS memory, and promote them:
  ```sas
  proc casutil;
      load data=work.NPA_MODEL_TRAIN outcaslib="casuser" casout="NPA_MODEL_TRAIN" promote;
      load data=work.NPA_MODEL_TEST outcaslib="casuser" casout="NPA_MODEL_TEST" promote;
      load data=work.NPA_SCORING_INPUT outcaslib="casuser" casout="NPA_SCORING_INPUT" promote;
  quit;
  ```
- These promoted CAS tables become immediately visible and selectable inside **SAS Model Studio** data selection menus.

---

## 6. Execution Verification Checklist

After running the programs in SAS Studio, check the SAS Log for the following milestones:

- [ ] `npa_import_and_qa.sas`:
  - 12,000 customers in `customer_master`
  - 144,000 records in `emi_history` (all DPD = 0, npa_indicator = 0)
  - 144,000 records in `payment_history` (all delay = 0, bounce = 0)
  - 12,000 records in `credit_bureau` (overdue = 0, bureau DPD = 0)
  - 0 scoring customers leaked into `future_outcome`
- [ ] `npa_feature_engineering_and_flags.sas`:
  - 11 internal risk flags evaluated with zero missing values
  - Freq distribution of `internal_rule_risk_grade` displayed
- [ ] `npa_prepare_model_datasets.sas`:
  - `NPA_MODEL_TRAIN.csv`: 7,000 rows
  - `NPA_MODEL_TEST.csv`: 3,000 rows
  - `NPA_SCORING_INPUT.csv`: 2,000 rows (no target column)
- [ ] `npa_postprocess_scores.sas`:
  - `NPA_SCORING_RESULTS.csv` created in `07_SCORED_OUTPUT/`
  - `NPA_MODEL_TEST_SCORED.csv` created in `07_SCORED_OUTPUT/`
  - `NPA_MODEL_METRICS.csv` created in `07_SCORED_OUTPUT/`

