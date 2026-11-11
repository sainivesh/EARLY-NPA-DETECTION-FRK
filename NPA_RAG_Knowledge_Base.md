## Document scope

This document contains policy and rule content for a prototype NPA risk-explanation system. It is intended to be indexed as factual knowledge in a RAG system.

The numerical thresholds identified as **SAS prototype rules** come from the supplied SAS NPA program. Additional operational guidance is labelled **Proposed bank policy**. The proposed guidance has not been supplied as an approved policy of a specific bank and must be reviewed by the bank's Credit Risk, Compliance and Legal teams before operational use.

The supplied SAS program uses synthetic data and a synthetic NPA target. Its model thresholds must not be represented as proof of a customer's actual regulatory NPA classification.

---

# Policy 1 (POL-NPA-001): Repayment Performance and Days Past Due (DPD)

## 1.1 Policy objective

Monitor repayment performance using instalment due dates, amounts due, amounts paid and days past due. Identify sustained or severe repayment delays for further account review.

## 1.2 DPD monitoring bands

The following are **proposed operational monitoring bands** for this prototype:

| DPD | Monitoring treatment |
|---|---|
| 0 days | Regular repayment monitoring. |
| 1–30 days | Send an early reminder and verify payment status. |
| 31–60 days | Increase monitoring and initiate customer contact through approved channels. |
| 61–90 days | Escalate for collections review and repayment-capacity assessment. |
| Above 90 days | Escalate for urgent account-status review by authorised bank personnel, applying the bank's approved policy and applicable regulatory requirements. |

These bands are operational review guidance. They do not independently establish the regulatory asset classification of an account.

## 1.3 DPD measures

The following measures are calculated from the customer's monthly EMI history:

- **Average DPD (`avg_dpd`):** Mean days past due across the available monthly EMI observations.
- **Maximum DPD (`max_dpd`):** Highest days-past-due value across those observations.
- **30+ DPD count (`dpd_30_count`):** Number of monthly observations where DPD is greater than 30.
- **60+ DPD count (`dpd_60_count`):** Number of monthly observations where DPD is greater than 60.
- **90+ DPD count (`dpd_90_count`):** Number of monthly observations where DPD is greater than 90.

In the supplied synthetic dataset, the EMI history contains 12 monthly observations per customer.

## 1.4 SAS prototype explanation rules

The supplied SAS/Python explainability logic applies these ordered conditions:

| Logic ID | Rule priority | Condition | Explanation |
|---|---|---|---|
| LOG-NPA-007 | Primary reason 1 | `avg_dpd > 60` | High average Days Past Due. |
| LOG-NPA-008 | Secondary reason 1 | `max_dpd > 90` | Customer has severe historical delinquency. |

The primary-reason condition is evaluated before the other primary-reason conditions in Policy 2 and Policy 3. The secondary-reason condition is evaluated before the other secondary-reason conditions in Policy 3.

## 1.5 Proposed bank policy

- Maintain an auditable repayment history for each loan.
- Record due date, amount due, amount received, payment date and calculated DPD.
- Review repeated or increasing DPD rather than relying only on a single observation.
- Verify payment posting delays, disputes or data errors before escalating an account.
- Record customer communications, contact attempts and agreed follow-up actions.
- Refer account classification to authorised bank personnel using the bank's approved classification process.

---

# Policy 2 (POL-NPA-002): Payment Behaviour, Bounces and Repayment Capacity

## 2.1 Policy objective

Assess repayment discipline and the customer's apparent capacity to meet loan obligations. Payment delays and bounced payments are risk indicators that may require review; they do not, by themselves, prove intentional non-payment or regulatory NPA status.

## 2.2 Payment behaviour measures

- **Bounce count (`bounce_count`):** Number of payment-history observations with `bounce_flag = 1`.
- **Late-payment count (`late_payment_count`):** Number of observations where payment delay is greater than 30 days.
- **Average payment delay (`avg_payment_delay`):** Average delay across payment-history observations.
- **Maximum payment delay (`max_payment_delay`):** Maximum delay across payment-history observations.
- **Payment trend (`payment_trend`):** Calculated as:

  `payment_trend = late_payment_count + (bounce_count * 2)`

The prototype gives a bounced payment twice the weight of a late-payment observation in this feature.

## 2.3 Repayment-capacity measures

**EMI-to-income ratio**

`emi_income_ratio = emi_amount / max(1, monthly_income)`

This compares the monthly EMI with monthly income.

**Debt-to-income ratio**

`debt_to_income = (emi_amount + total_debit_transaction / 12) / max(1, monthly_income)`

The annual debit-transaction total is divided by 12 to approximate a monthly amount. This is the formula used by the supplied prototype; it is not necessarily the bank's standard affordability calculation.

## 2.4 SAS prototype explanation rules

| Logic ID | Rule priority | Condition | Explanation |
|---|---|---|---|
| LOG-NPA-017 | Primary reason 1, after the average-DPD test | `bounce_count >= 3` | Multiple payment bounces. |
| LOG-NPA-016 | Primary reason 2, after earlier primary tests | `debt_to_income > 0.50` | High debt-to-income ratio. |
| LOG-NPA-018 | Tertiary reason 1 | `payment_trend > 5` | Negative payment trend observed. |

The reason fields use ordered conditions. A condition may be true but not appear in the stored reason field when an earlier condition in that same reason group is also true.

## 2.5 Proposed bank policy

- Record each payment bounce with its date, amount and available return or failure reason.
- Review repeated bounces and late payments for possible cash-flow, mandate, processing or account-related issues.
- Verify income and existing repayment obligations when repayment-capacity indicators are elevated.
- Treat `debt_to_income > 0.50` as a prototype review trigger, not as a universal banking affordability limit.
- Contact customers through approved channels and communicate overdue amounts and resolution options clearly.
- Do not infer deliberate default from a bounce or delay without supporting evidence.

---

# Policy 3 (POL-NPA-003): Credit Exposure, Credit Bureau History and Collateral

## 3.1 Policy objective

Review the customer's wider credit exposure, bureau repayment history and available collateral as supporting indicators of credit risk.

## 3.2 Credit exposure measures

**Credit utilization**

`credit_utilization = total_credit_balance / max(1, total_credit_limit)`

This measures the proportion of the reported total credit limit currently used.

**Outstanding ratio**

`outstanding_ratio = outstanding_amount / max(1, sanctioned_amount)`

This measures the outstanding loan amount relative to the sanctioned amount.

**Loan-to-value ratio (LTV)**

`loan_to_value = sanctioned_amount / max(1, collateral_value)`

This compares the sanctioned loan amount with the recorded collateral value.

## 3.3 SAS prototype explanation rules

| Logic ID | Rule group and priority | Condition | Explanation |
|---|---|---|---|
| LOG-NPA-026 | Primary reason, after average DPD | `credit_utilization > 0.80` | High credit utilization. |
| LOG-NPA-027 | Primary reason, after earlier primary tests | `credit_score < 650` | Low credit bureau score. |
| LOG-NPA-030 | Tertiary reason, after payment-trend test | `outstanding_ratio > 0.80` | High outstanding loan ratio. |

## 3.4 Credit bureau indicators

The supplied program includes these bureau fields:

- `credit_score`
- `total_credit_limit`
- `total_credit_balance`
- `active_credit_accounts`
- `overdue_accounts`
- `bureau_dpd`
- `recent_enquiries`
- `writeoff_accounts`

The explainability rules use the following ordered secondary-reason conditions:

| Logic ID | Rule priority | Condition | Explanation |
|---|---|---|---|
| LOG-NPA-008 | Secondary reason 1 | `max_dpd > 90` | Customer has severe historical delinquency. |
| LOG-NPA-028 | Secondary reason 2 | `overdue_accounts >= 3` | Multiple overdue credit accounts. |
| LOG-NPA-029 | Secondary reason 3 | `recent_enquiries >= 6` | High recent credit enquiries. |

The credit risk behaviour score also uses credit score, credit utilization, debt-to-income, average DPD, bounce count, overdue accounts, recent enquiries, write-off accounts and outstanding ratio. It is a prototype composite feature, bounded between 0 and 1.

## 3.5 LTV bands described in the SAS comments

The supplied SAS comments describe these illustrative LTV categories:

| LTV | Commented category |
|---|---|
| `loan_to_value <= 0.60` | LOW |
| `0.60 < loan_to_value <= 0.80` | MEDIUM |
| `0.80 < loan_to_value <= 1.00` | HIGH |
| `loan_to_value > 1.00` | VERY HIGH |

The supplied feature-engineering code calculates `loan_to_value`, but the shown code does not implement the `ltv_risk` category assignment. These bands should therefore be treated as documented illustrative bands, not as a confirmed active decision rule.

## 3.6 Proposed bank policy

- Review credit-bureau information using its source, reporting date and account status.
- Verify disputed, stale or inconsistent bureau entries before relying on them for customer decisions.
- Treat high credit utilization as a reason to review the customer's overall indebtedness and repayment capacity.
- Review multiple overdue accounts and write-off history as adverse credit indicators, while confirming their current status.
- Compare sanctioned exposure with current, verified collateral value under the bank's approved valuation process.
- Do not treat high utilization, a low bureau score or high LTV alone as proof that a particular loan is an NPA.

---

# Policy 4 (POL-NPA-004): Risk Grading, Collection Escalation and Customer Protection

## 4.1 Policy objective

Use model outputs as risk-monitoring and prioritisation information while retaining authorised human review for account classification and consequential collection or recovery decisions.

## 4.2 SAS prototype risk-grade mapping

The supplied SAS scoring code assigns `EM_EVENTPROBABILITY` from `pd_logistic` and applies these bands:

| Scored event probability | Risk grade | Prototype recommended action |
|---|---|---|
| Below 0.10 | LOW | NORMAL MONITORING |
| 0.10 to below 0.30 | MEDIUM | REMINDER |
| 0.30 to below 0.60 | HIGH | COLLECTION CALL |
| 0.60 or above | CRITICAL | RECOVERY TEAM |

These are the probability bands and action labels implemented in the supplied scoring excerpt. They are prototype mappings and must not be represented as an approved bank's collection policy without formal approval.

## 4.3 Distinction between model outputs

The following outputs have different meanings:

- **Synthetic NPA flag (`npa_flag`):** In the supplied SAS feature code, set to 1 when `npa_probability_actual >= 0.50`; otherwise set to 0.
- **Synthetic target probability (`npa_probability_actual`):** Calculated from the prototype risk formula and bounded between 0.01 and 0.95.
- **Scored event probability (`EM_EVENTPROBABILITY`):** Assigned from `pd_logistic` in the supplied scoring excerpt.
- **Risk grade:** Assigned from `EM_EVENTPROBABILITY` using the bands in Section 4.2.
- **Risk reasons:** Generated from ordered threshold conditions described in Policies 1–3.
- **Recommended action:** The action label mapped from the scored event-probability band.

A synthetic target flag, model probability, risk grade or explanatory indicator is not, by itself, confirmation of a customer's regulatory NPA classification.

## 4.4 Proposed bank policy for review and escalation

- Use risk grades to prioritise account monitoring and review, not as an automatic substitute for the bank's approved NPA classification process.
- Require authorised personnel to verify account-level repayment records and applicable classification requirements before confirming NPA status or initiating consequential recovery action.
- Preserve the source data, scoring date, model version, applicable rule version, risk reasons and human review outcome for audit.
- Provide customers with accurate information about overdue amounts and the bank's approved resolution or grievance process.
- Use respectful, non-misleading communication and follow the bank's approved customer-contact procedures.
- Provide a process for customers to dispute incorrect payment records or credit-bureau information.
- Do not recommend seizure, legal action, rejection of restructuring or other enforcement solely on the basis of an AI-generated explanation or model probability.
- Escalate missing, inconsistent or unverified account information for correction before relying on it for consequential decisions.

## 4.5 Model and data governance

- Validate model performance and probability calibration on appropriately labelled, representative data.
- Monitor false positives and false negatives and review material changes in model behaviour.
- Validate thresholds before production use and document approved changes.
- Review data quality, missing values, inconsistent histories and the date of source information.
- Assess whether model inputs and outcomes create unintended or unfair effects.
- Keep synthetic demonstration data separate from real customer records.

---

## Source classification

The rules and values in this document have the following origins:

- **SAS prototype rule:** A threshold, calculation, reason condition or probability band appearing in the supplied SAS program.
- **Proposed bank policy:** Operational guidance added for this prototype. It is not an approved policy of a named bank and is not asserted to be an official regulatory requirement.

## End of policy knowledge base