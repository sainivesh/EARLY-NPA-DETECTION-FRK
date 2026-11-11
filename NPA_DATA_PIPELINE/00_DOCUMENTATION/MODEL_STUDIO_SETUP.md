# SAS Model Studio - Project Setup & Machine Learning Guide

This document provides instructions for configuring and training machine learning models in **SAS Model Studio** (Visual Data Mining and Machine Learning) using the prepared NPA datasets.

---

## 1. Project Creation & Data Ingestion

1. In SAS Viya, open the application switcher icon (top left) and choose **Build Models (Model Studio)**.
2. Click **New Project** and configure:
   - **Name**: `NPA_Early_Detection`
   - **Type**: `Data Mining and Machine Learning`
   - **Data**: Select table `NPA_MODEL_TRAIN` (promoted in CAS or imported from `06_SAS_OUTPUTS/NPA_MODEL_TRAIN.csv`).
3. Click **Save**.

---

## 2. Variable Metadata Assignment


---

## 3. Pipeline Construction & Model Comparison

1. Navigate to the **Pipelines** tab.
2. Construct a pipeline with the following competing supervised learning nodes:
   - **Logistic Regression**: Linear baseline with stepwise selection.
   - **Decision Tree**: Explainable tree rules.
   - **Forest**: Bagging ensemble for variance reduction.
   - **Gradient Boosting**: Tuned boosting ensemble with early stopping.
3. Right-click the **Pipeline** and click **Run**.
4. Open the **Model Comparison** node:
   - Compare models on **Validation KS (Youden's Index)**, **ROC Area (AUC)**, and **Misclassification Rate**.
   - Note which model is designated as the **Champion**.

---

## 4. Score Code Export & Independent Evaluation

1. Right-click the Champion model node and select **Download Score Code**.
2. Save the generated `dmcas_scorecode.sas` or Python scoring package.
3. In SAS Studio, score the independent test population:
   - Run the score code against `work.NPA_MODEL_TEST` (3,000 customers).
   - This produces predicted probabilities (`P_npa_flag1` or `EM_EVENTPROBABILITY`).
4. Score the live scoring population:
   - Run the score code against `work.NPA_SCORING_INPUT` (2,000 customers).
   - This produces event probabilities for unlabelled customers without any target leakage.

---

## 5. Applying Post-Processing & Output Generation

Execute `05_SAS_PROGRAMS/npa_postprocess_scores.sas`:
1. It automatically maps the model probability column to `model_event_probability`.
2. It assigns the four prototype risk bands:
   - **LOW**: `< 0.10`
   - **MEDIUM**: `0.10` to `< 0.30`
   - **HIGH**: `0.30` to `< 0.60`
   - **CRITICAL**: `>= 0.60`
3. It maps the operational recommended actions:
   - LOW: `NORMAL MONITORING`
   - MEDIUM: `REMINDER`
   - HIGH: `COLLECTION CALL`
   - CRITICAL: `RECOVERY TEAM`
4. It outputs `NPA_SCORING_RESULTS.csv` (2,000 rows), `NPA_MODEL_TEST_SCORED.csv` (3,000 rows), and `NPA_MODEL_METRICS.csv` into `07_SCORED_OUTPUT/`.

