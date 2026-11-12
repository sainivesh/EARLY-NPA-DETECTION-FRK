# NPA Early Detection – AI Assessment Quality, Explainability & Early-Warning Enhancement

## PROJECT OBJECTIVE

Improve the quality, consistency, depth and presentation of AI-generated customer risk assessments in the existing NPA Early Detection application.

The current assessments are too brief and generic. They state the model's risk grade and mention a few indicators, but they do not adequately explain the customer's financial position, historical repayment behaviour, potential vulnerabilities or the reasons for recommending further review.

The goal is to create informative, evidence-based and professional banking-credit assessments that help reviewers understand:

1. What the SAS model predicts.
2. Why the customer may require additional attention.
3. What the customer's current financial position indicates.
4. What previous repayment history reveals.
5. Which indicators are favourable and which require attention.
6. What the credit-risk team should investigate or do next.

The central business objective is:

**Identify potential financial vulnerability before it develops into repayment delinquency.**

This is an early-warning and risk-prioritisation system, not an automatic NPA declaration or collections system.

Do not replace the existing application or introduce unrelated functionality.

---

# PHASE 1 – INSPECT THE EXISTING ASSESSMENT ENGINE

Before implementing changes, inspect:

- `web_app.py`
- `npa_assessment.py`
- `templates/index.html`
- Existing assessment-generation prompt.
- Existing LLM response JSON structure.
- `retrieve_knowledge()`
- `generate_assessment()`
- Actual `NPA_SCORING_RESULTS.csv` schema.
- Existing banking policy knowledge base and citation structure.

Understand how customer records are passed into the RAG retrieval system, how customer-specific information is supplied to the LLM and how the assessment response reaches the frontend.

Identify why the current summaries are too short, generic or incomplete.

Verify whether the LLM receives all relevant customer attributes, financial indicators, previous repayment summaries, risk flags and risk reasons.

## Preservation requirements

- Preserve the existing Python backend.
- Preserve the existing `ThreadingHTTPServer`.
- Preserve the existing SQLite database.
- Preserve the existing ChromaDB knowledge collection.
- Preserve the existing RAG retrieval functionality.
- Preserve the existing LLM provider integration.
- Preserve existing customer selection and API functionality.
- Preserve the existing webpage architecture and styling unless a small presentation adjustment is necessary.
- Do not introduce Node.js or a new frontend framework.
- Do not alter the SAS model or its scoring outputs.
- Do not modify unrelated files.
- Do not delete existing data, logs, databases or backups.
- Do not commit changes.

---

# PHASE 2 – CORE BUSINESS LOGIC: PREDICTIVE VS. REACTIVE

This distinction must be reflected throughout the assessment-generation instructions and webpage terminology.

## 1. Current customer status

The live scoring population consists of customers who are performing at the current observation date.

The current-loan monitoring design requires:

- Current DPD = 0.
- Current EMIs fully paid.
- No current payment delays.
- No current bounced payments.
- No current late-payment indicators.
- No current bureau overdue accounts or DPD.

A customer receiving a HIGH or CRITICAL model grade has not automatically become an NPA.

The model estimates whether the customer may experience an NPA event within the **next six months**, based on the six-month prediction target.

Use terminology such as:

- Early NPA Risk.
- Predicted Future NPA Risk.
- Model-Estimated NPA Probability.
- Early-Warning Risk Grade.
- Performing Customer Under Risk Review.

Never describe a predicted future event as an existing default or current NPA.

## 2. Why a currently performing customer may require attention

The assessment should explain that repayment history and future repayment capacity are different aspects of credit risk.

A customer may continue paying EMIs on time even while their financial position becomes increasingly vulnerable.

Potential early-warning indicators include:

- High EMI commitments relative to income.
- High total debt obligations relative to income, where valid debt-obligation data is available.
- Increasing credit utilisation.
- Declining income or business turnover.
- Increasing outstanding exposure.
- Poor liquidity.
- Previous NPA or severe repayment distress.
- Increasing credit enquiries or borrowing activity.
- Deteriorating cash-flow patterns.

Explain the indicators using the actual customer's observed values.

Do not assume that an elevated ratio proves financial deterioration. Where historical comparisons are unavailable, describe it as an observed financial condition rather than a worsening trend.

## 3. Appropriate risk-review actions

The purpose of an early-warning score is to prioritise internal attention and determine whether intervention is appropriate.

A high score alone must not automatically result in a collections or recovery call to a customer who is currently performing.

Use the following recommended review framework:

| Model Risk Grade | Recommended Review Action | Purpose |
|---|---|---|
| LOW | Routine Portfolio Monitoring | Continue normal monitoring of the performing account |
| MEDIUM | Periodic Risk Review | Monitor financial indicators and identify changes in repayment capacity |
| HIGH | Priority Credit Review | Verify significant financial warning indicators and assess repayment capacity |
| CRITICAL | Urgent Credit Risk Assessment | Prioritise human review and evaluate suitable preventive measures |

The action descriptions should be displayed consistently in the webpage.

Customer-facing contact must not be automatic based solely on the model probability.

A relationship manager or authorised credit-risk professional should first review and verify the supporting information.

Where customer communication is appropriate, it should be proportionate and supportive.

For example, a relationship manager may conduct a routine financial-wellbeing or repayment-capacity discussion when verified financial changes justify it.

Do not tell customers that the model predicts they will default.

Do not automatically recommend recovery procedures for a performing account.

## 4. Keep all risk classifications separate

There are two distinct grading systems.

**SAS Model Risk Grade**

- LOW
- MEDIUM
- HIGH
- CRITICAL

This is derived from the SAS champion model's event probability.

**Internal Rule-Based Risk Grade**

- Generated using the internal business-rule risk flags.
- Represents a separate rule-based assessment.

Never combine the two grades or present them as equivalent.

If the SAS model assigns LOW but an internal financial indicator is elevated, explain the distinction clearly.

Example:

"The SAS model assigns a LOW risk grade. Separately, the customer's debt-to-income indicator is elevated and warrants periodic review. This financial indicator does not override the model's assigned grade."

---

# PHASE 3 – ESTABLISH ONE STANDARD ASSESSMENT FORMAT

Every customer must receive the same logical assessment structure regardless of whether the model risk grade is LOW, MEDIUM, HIGH or CRITICAL.

Generate the assessment using the following six sections in this exact order.

## SECTION 1 – MODEL RISK SUMMARY

This section contains authoritative SAS Model Studio information.

Display:

- Model Risk Grade.
- Model Event Probability.
- Predicted Future NPA Outcome.
- Prediction Horizon.
- Recommended Review Action.
- Scoring Run ID, where available.

Example:

**Model Risk: HIGH**

**Model-Estimated NPA Probability: 33.36%**

**Predicted Future NPA Risk: YES**

**Prediction Horizon: Six months**

**Recommended Review Action: PRIORITY CREDIT REVIEW**

All probability, predicted-class and model-grade values must come directly from the SAS scoring record.

Do not allow the LLM to generate, recalculate, modify or independently round these values.

Use the model probability bands already defined in SAS:

- Below 10%: LOW
- 10% to below 30%: MEDIUM
- 30% to below 60%: HIGH
- 60% and above: CRITICAL

The displayed recommended review action should follow the review framework defined in Phase 2.

## SECTION 2 – EXECUTIVE ASSESSMENT

Generate an informative, customer-specific narrative of approximately 120–180 words.

The narrative must explain:

1. What the model predicts.
2. The customer's most relevant financial indicators.
3. The severity of any previous repayment problems.
4. Any favourable or mitigating indicators.
5. Why additional monitoring or review may be appropriate.
6. Why the proposed review action is suitable.

Use professional but simple banking language.

Avoid generic statements such as:

- The customer is high risk due to financial problems.
- The customer has poor repayment behaviour.
- The customer requires monitoring.

Instead, explain the actual evidence.

Example:

"The customer has a previous NPA event recorded in the prior loan history, with an average DPD of 150 days and a maximum DPD of 450 days. This indicates prolonged repayment difficulty during the previous lending cycle. The current debt-to-income indicator is 0.88, suggesting substantial financial outflow relative to reported income. At the same time, the current loan records show that scheduled EMIs are being paid on time. The SAS champion model assigns a CRITICAL risk grade with a model-estimated event probability of 96%. Given the combination of historical distress and current financial indicators, the account warrants urgent internal credit-risk assessment to verify the customer's repayment capacity and identify whether preventive support is appropriate."

Do not copy this exact text for every customer.

Generate the narrative using the selected customer's actual records.

Always acknowledge favourable current performance where supported by the data.

## SECTION 3 – KEY RISK INDICATORS

Create a structured list or table of the most relevant evidence.

Use:

| Risk Indicator | Observed Value | Prototype Threshold / Reference | Interpretation |
|---|---|---|---|

Include relevant available indicators from:

### Financial indicators

- EMI-to-income ratio.
- Debt-to-income ratio, using its actual documented calculation.
- Outstanding ratio.
- Credit utilisation.
- Loan-to-value ratio.
- Credit score.
- Current ratio.
- Turnover growth.
- Company financial stress.

### Historical repayment indicators

- Previous NPA flag.
- Previous average DPD.
- Previous maximum DPD.
- Prior missed-payment count.
- Maximum consecutive missed months.
- Previous NPA event count.
- Resolution status.

### Current financial context

- Monthly income.
- Current EMI.
- Outstanding loan balance.
- Remaining loan tenure.
- Credit balance and available credit limit.

For every relevant indicator:

1. Show the actual observed value.
2. Show a threshold only when it exists in the documented business-rule configuration.
3. Explain what the value indicates.
4. Identify whether it is a direct model input, an internal rule flag or an additional contextual indicator.

Do not invent thresholds.

Do not present every available variable just to make the assessment longer.

Prioritise the strongest and most relevant indicators for the individual customer.

Also identify favourable indicators, such as:

- Current DPD = 0.
- Full and timely current EMI payments.
- No current bounce or late-payment records.
- Healthy credit score, where supported.
- Reasonable credit utilisation.
- Stable income or company financial indicators, where supported.

Do not assume an indicator is favourable when its value is unavailable.

## SECTION 4 – PREVIOUS REPAYMENT HISTORY

This section must explain historical repayment behaviour separately from current-loan performance.

Include, when available:

- History availability.
- Previous loan repayment pattern.
- Previous NPA occurrence.
- Average DPD.
- Maximum DPD.
- Consecutive missed months.
- Missed-payment count.
- Previous NPA event count.
- Previous NPA resolution status.

Explain the severity of the historical pattern using actual figures.

Example:

"Previous loan records show an average DPD of 288.75 days and a maximum DPD of 630 days. The customer also experienced 21 consecutive months of missed payments. The historical record indicates prolonged repayment distress during the previous loan cycle. The recorded NPA resolution status should be considered when evaluating the customer's previous credit history."

Where the previous NPA status is written off, resolved or unresolved, use the actual recorded status.

Do not confuse historical DPD with current-loan DPD.

Do not describe a historical NPA event as a current NPA event.

If history is unavailable, explicitly state:

"No previous loan history is available in the supplied records. This should not be interpreted as a confirmed clean repayment history."

## SECTION 5 – RECOMMENDED NEXT STEPS

Use the recommended review action defined by the model risk grade.

Explain why the action is relevant to the available evidence.

Additionally, provide two or three practical reviewer checks where supported by the records.

Examples:

- Verify previous NPA resolution documentation.
- Review the current EMI burden against reported income.
- Confirm recent income consistency.
- Review current credit utilisation.
- Compare current outstanding exposure with sanctioned amount.
- Examine historical business turnover and liquidity indicators.
- Consider an appropriate relationship-manager review if verified financial changes warrant customer engagement.

Clearly distinguish between:

- The system's recommended internal review action.
- Additional AI-suggested verification steps.
- Any customer communication that requires human approval.

Do not invent collection procedures, legal requirements or bank-mandated actions.

Do not recommend automatic customer contact solely because a model probability is high.

## SECTION 6 – EVIDENCE AND QUALIFICATIONS

Show relevant banking-policy references retrieved through the existing RAG knowledge base.

For every reference:

- Display policy ID.
- Display policy title.
- Provide a concise explanation of the relevant provision.
- Preserve the actual citation.
- Avoid duplicate references.
- Connect each reference to the relevant risk or review consideration.

Do not invent policy IDs, policy statements or citations.

Policy recommendations must reflect the actual retrieved documentation.

---

# PHASE 4 – CRITICAL MODEL EXPLAINABILITY RULES

This is one of the most important requirements.

The current champion is Logistic Regression. Its exported scoring equation uses the following predictors:

- `credit_score`
- `credit_utilization`
- `emi_income_ratio`
- `financial_stress_flag_synthetic`
- `flag_negative_turnover_growth`
- `flag_previous_npa`

The generated assessment must distinguish these model inputs from other contextual financial indicators and historical variables.

## Rule 1 – Never fabricate model explanations

Do not claim that a variable caused or drove the model probability unless the model's actual explainability output supports that attribution.

In particular:

- `debt_to_income` is contextual financial evidence, not a direct input in the supplied champion scoring equation.
- `outstanding_ratio` is contextual financial evidence, not a direct input in that equation.
- Detailed prior DPD measures must not be claimed as direct model predictors unless the actual champion scoring code includes them.
- `flag_previous_npa` is one of the actual champion inputs.

The AI may explain how these contextual indicators relate to repayment capacity, but must not misrepresent them as direct causes of the model probability.

If reliable feature-contribution information is unavailable, use wording such as:

"The following indicators provide additional context for reviewing the customer's financial and repayment position. They are not individually attributed as causes of the model probability."

## Rule 2 – Keep model and rule-based grades separate

Never combine the SAS Model Risk Grade and Internal Rule-Based Risk Grade.

If the model assigns LOW but a financial ratio is elevated, explain the distinction.

If the model assigns CRITICAL but the current loan is performing, explain both facts.

Do not let internal rules override the SAS model probability.

## Rule 3 – Distinguish prediction from existing NPA status

All live-scoring customers belong to the currently performing scoring population.

The model predicts potential future NPA risk.

Never call a predicted Class 1 customer an existing NPA account.

Use:
- Predicted future NPA risk.
- Model-estimated event probability.
- Previous NPA history.
- Current performing-loan status.

Never confuse previous NPA history with the future prediction.

## Rule 4 – Never invent missing values

When information is unavailable:

- Display "Not available in the supplied record."
- Do not substitute zero.
- Do not interpret missing history as clean history.
- Do not fabricate payment dates, DPD values, company financial figures or policy references.

## Rule 5 – Explain both risk and resilience

Do not create one-sided summaries that mention only negative indicators.

Where supported, explain the customer's positive current performance alongside areas requiring attention.

A customer may have a previous NPA history but currently maintain regular repayments.

A customer may have a LOW model grade but have one elevated financial indicator that warrants observation.

Preserve these distinctions in the narrative.

---

# PHASE 5 – MAKE ALL RISK-GRADE SUMMARIES EQUALLY INFORMATIVE

Do not generate detailed explanations only for CRITICAL customers.

All model grades must receive the same six-section structure.

### LOW

Explain why the model assigns low risk.

Mention favourable indicators where verified.

If separate internal financial indicators are elevated, mention them as monitoring considerations without overstating the model risk.

Recommended review action: Routine Portfolio Monitoring.

### MEDIUM

Explain the indicators creating moderate concern, their observed values and what needs monitoring.

Identify whether historical repayment evidence is available.

Recommended review action: Periodic Risk Review.

### HIGH

Explain significant financial indicators, historical repayment behaviour and any concerns that need closer review.

Recommended review action: Priority Credit Review.

### CRITICAL

Explain severe supporting evidence, relevant previous NPA history, financial pressure and why urgent internal assessment is appropriate.

Recommended review action: Urgent Credit Risk Assessment.

Do not exaggerate the severity beyond the actual customer data.

Avoid generic text repeated across different customers.

Every assessment must be generated using that individual customer's values.

---

# PHASE 6 – STRUCTURED OUTPUT AND FRONTEND PRESENTATION

Inspect the existing assessment JSON structure before modifying it.

Retain backward compatibility with the existing `/api/summary` endpoint wherever possible.

The preferred logical response structure is:

```json
{
  "overview": {},
  "executive_assessment": "",
  "key_risk_indicators": [],
  "previous_repayment_history": {},
  "mitigating_factors": [],
  "recommended_next_steps": [],
  "applicable_policies": [],
  "citations": [],
  "qualifications": ""
}
```

Use the actual existing API response schema as the compatibility reference.

This is a proposed logical structure, not permission to break existing frontend consumers.

Keep authoritative SAS fields separate from generated narrative content.

## Frontend presentation

Create a clear, consistent visual hierarchy:

1. Model Risk Summary.
2. Executive Assessment.
3. Key Risk Indicators.
4. Previous Repayment History.
5. Recommended Next Steps.
6. Applicable Policies and Citations.

Use:

- Clear section headings.
- Bold emphasis for important financial values.
- Compact evidence tables.
- Consistent spacing.
- Subtle risk-grade colours.
- Readable paragraphs.
- Expandable details where useful.

Do not display one large unformatted LLM paragraph.

Do not duplicate the same risk explanation in multiple panels.

Keep the summary readable within the existing dashboard layout. Use tabs or collapsible sections rather than making the entire page excessively long.

The primary customer assessment must remain visually prominent.

---

# PHASE 7 – TEST USING THE THREE PROVIDED CUSTOMER EXAMPLES

Use the three previously supplied customer examples as regression scenarios. Do not hardcode these examples into the application.

## Example A – LOW model risk with elevated financial indicators

Known context:

- Home-loan customer.
- LOW model risk.
- NORMAL MONITORING action in the existing output.
- Elevated debt-to-income ratio.
- High outstanding loan ratio.
- No confirmed previous missed payments.
- Credit utilisation and bureau score are unremarkable.
- Current loan repayments are performing.

Expected assessment:

- Clearly explain why the SAS model grade is LOW.
- Explain elevated financial indicators separately.
- Mention favourable credit and repayment indicators.
- Do not present the customer as HIGH or CRITICAL.
- Explain that the financial indicators may warrant monitoring despite the LOW model grade.
- Do not invent unavailable numerical values.

## Example B – CRITICAL model risk

Known context:

- Personal loan.
- Model event probability approximately 0.96.
- CRITICAL model risk.
- Existing output recommends RECOVERY TEAM.
- Debt-to-income ratio 0.88.
- Previous average DPD 150 days.
- Previous maximum DPD 450 days.
- Previous NPA event recorded as written off.

Expected assessment:

- Explain the severe previous repayment history.
- Explain the high financial burden.
- Distinguish the written-off previous NPA from the currently performing loan.
- Show the 96% model estimate.
- Explain that the result warrants urgent internal credit-risk assessment.
- Do not automatically recommend an external recovery or collections call.
- Distinguish actual champion inputs from contextual financial indicators.

## Example C – HIGH model risk

Known context:

- Home loan.
- Model probability 0.3336.
- HIGH model grade.
- Existing output recommends COLLECTION CALL.
- Previous NPA event.
- Previous average DPD 288.75 days.
- Previous maximum DPD 630 days.
- 21 consecutive missed-payment months.
- Debt-to-income ratio 0.696.

Expected assessment:

- Explain the prolonged historical repayment distress.
- Display the DPD values clearly.
- Explain the financial-burden indicator.
- Explain why the model probability falls into the HIGH band.
- Recommend priority internal credit review.
- Do not declare the customer currently NPA.
- Do not recommend automatic collections contact.

## Regression acceptance requirements

For all three customers:

- Same section ordering.
- Same overall assessment format.
- Customer-specific figures.
- No invented values.
- No conflicting risk grades.
- No unsupported model-causation claims.
- Clear distinction between previous NPA history and future NPA prediction.
- Appropriate risk-review action.
- Clear favourable and adverse indicators where available.

---

# PHASE 8 – QUALITY AND VERIFICATION

After modifying the assessment engine, run actual tests.

## Backend tests

- Verify that the customer record is retrieved from the correct scoring CSV row.
- Verify that model probability is unchanged.
- Verify that predicted class is unchanged.
- Verify that model grade is unchanged.
- Verify that the SAS source data remains authoritative.
- Verify that the selected customer's actual attributes are passed to the LLM.
- Verify that policy retrieval uses the existing ChromaDB collection.
- Verify that citations are preserved.
- Verify that missing values are handled explicitly.
- Verify that assessment-generation errors are handled correctly.

## Narrative quality tests

For all three supplied example scenarios, verify:

1. All six assessment sections are present.
2. Important available numerical indicators are included.
3. Historical and current loan information are separated.
4. Model predictors are distinguished from contextual indicators.
5. Model grades and review actions are consistent with the defined framework.
6. No claim is unsupported by the customer record or retrieved policy.
7. The assessment is specific to the selected customer.
8. Wording is understandable to a banking reviewer.
9. Recommendations are practical and proportionate.
10. The explanation is informative without unnecessary repetition.
11. Positive current repayment performance is acknowledged.
12. No customer is automatically directed to recovery or collections solely because of a high model score.

## Frontend tests

- All sections render correctly.
- Missing information displays cleanly.
- Long explanations do not break the layout.
- Customer switching updates the assessment.
- Loading and error states work.
- Citations remain accessible.
- Existing dashboard navigation remains functional.
- The primary summary remains visually prominent.

## Final deliverables

Provide:

1. Existing summary problems identified.
2. Revised assessment structure.
3. Updated LLM instructions/system prompt.
4. Exact files modified.
5. Example assessments for all three scenarios.
6. Backend and frontend test results.
7. Remaining limitations.

Do not claim tests passed unless they were actually executed.

Do not change unrelated project functionality or commit changes.

---

# FINAL QUALITY EXPECTATION

A banking reviewer should be able to read any customer assessment and understand:

- What the SAS model predicts.
- How significant the predicted risk is.
- Why a currently performing customer may warrant additional attention.
- Which actual customer facts are relevant.
- What the previous loan history reveals.
- Which financial indicators require review.
- Which indicators demonstrate favourable current performance.
- What internal review action is appropriate.
- Which policy evidence supports the assessment.

The system must prioritise early identification and appropriate preventive review rather than treating a high-risk customer as an existing defaulter.

**The assessment should explain the customer's financial situation and the reason for internal risk attention, not simply repeat the customer's risk grade and three risk reasons.**