/*==========================================================================
  PROJECT : NPA Early Detection - SAS Viya Pipeline
  PROGRAM : npa_feature_engineering_and_flags.sas
  PURPOSE : Engineer behavioral and financial features, construct explainable
            internal rule-based risk flags, and assign prototype rule risk grades.
  ENVIRONMENT : SAS Viya for Learners / SAS Studio
==========================================================================*/

/*--------------------------------------------------------------------------
  1. AGGREGATE CURRENT TRANSACTION BEHAVIOR
--------------------------------------------------------------------------*/
proc sql;
    create table work.transaction_summary as
    select customer_id,
           sum(credit_transaction) as total_credit_transaction,
           sum(debit_transaction) as total_debit_transaction,
           mean(transaction_count) as avg_transaction_count,
           sum(cash_withdrawal) as total_cash_withdrawal
    from work.transaction_history
    group by customer_id;
quit;

/*--------------------------------------------------------------------------
  2. JOIN OBSERVABLE ATTRIBUTES ACROSS SOURCE DOMAINS
--------------------------------------------------------------------------*/
proc sql;
    create table work.customer_consolidated as
    select c.customer_id,
           c.age,
           c.gender,
           c.marital_status,
           c.occupation,
           c.monthly_income,
           c.employment_years,
           c.city_type,
           l.loan_id,
           l.loan_type,
           l.sanctioned_amount,
           l.outstanding_amount,
           l.emi_amount,
           l.interest_rate,
           l.collateral_value,
           l.loan_age_months,
           l.remaining_tenure,
           b.credit_score,
           b.total_credit_limit,
           b.total_credit_balance,
           b.active_credit_accounts,
           b.recent_enquiries,
           t.total_credit_transaction,
           t.total_debit_transaction,
           t.avg_transaction_count,
           t.total_cash_withdrawal,
           h.history_available,
           h.previous_npa_flag,
           h.prior_missed_payment_count,
           h.prior_avg_dpd,
           h.prior_max_dpd,
           h.max_consecutive_missed_months,
           h.prior_npa_event_count,
           h.repayment_pattern as prior_repayment_pattern,
           h.resolution_status as prior_resolution_status,
           h.prior_recovery_amount,
           comp.company_id,
           comp.company_relationship,
           comp.industry,
           comp.sub_industry,
           comp.company_size,
           comp.company_age_years,
           comp.customer_company_tenure_years,
           comp.employee_count,
           comp.annual_turnover,
           comp.turnover_growth_pct,
           comp.profit_margin_pct,
           comp.debt_to_equity,
           comp.current_ratio,
           comp.credit_rating as company_credit_rating,
           comp.business_status,
           comp.sector_outlook_synthetic,
           comp.financial_stress_flag_synthetic,
           s.population_role,
           s.split_set
    from work.customer_master as c
    left join work.loan_account as l
        on c.customer_id = l.customer_id
    left join work.credit_bureau as b
        on c.customer_id = b.customer_id
    left join work.transaction_summary as t
        on c.customer_id = t.customer_id
    left join work.npa_history_customer_summary as h
        on c.customer_id = h.customer_id
    left join work.customer_company_details as comp
        on c.customer_id = comp.customer_id
    left join work.NPA_CUSTOMER_SPLIT as s
        on c.customer_id = s.customer_id;
quit;

/*--------------------------------------------------------------------------
  3. COMPUTE ANALYTICAL RATIOS AND INTERNAL RULE-BASED FLAGS
--------------------------------------------------------------------------*/
data work.npa_features_with_flags;
    set work.customer_consolidated;

    /* Financial & Behavioral Ratios */
    emi_income_ratio = emi_amount / max(1, monthly_income);
    outstanding_ratio = outstanding_amount / max(1, sanctioned_amount);
    credit_utilization = total_credit_balance / max(1, total_credit_limit);
    loan_to_value = sanctioned_amount / max(1, collateral_value);

    /* Debt-to-income: adds monthly EMI once to non-EMI average monthly debits */
    debt_to_income = (emi_amount + (total_debit_transaction / 12)) / max(1, monthly_income);

    cash_withdrawal_ratio = total_cash_withdrawal / max(1, total_debit_transaction);
    credit_to_income_ratio = (total_credit_transaction / 12) / max(1, monthly_income);

    /*----------------------------------------------------------------------
      PROVISIONAL PROTOTYPE INTERNAL RISK FLAGS
      Transparent, rule-based business criteria derived strictly from
      documented source attributes.
    ----------------------------------------------------------------------*/
    flag_high_emi_burden = (emi_income_ratio > 0.40);
    flag_high_credit_utilization = (credit_utilization > 0.75);
    flag_low_credit_score = (credit_score < 650);
    flag_high_outstanding_ratio = (outstanding_ratio > 0.85);
    flag_previous_npa = (previous_npa_flag = 1);
    flag_prior_missed_streak = (max_consecutive_missed_months >= 3);
    flag_company_financial_stress = (financial_stress_flag_synthetic = 1);
    flag_negative_turnover_growth = (turnover_growth_pct < -5.0);

    /* Low current ratio applies only to business / practice profiles where working capital applies */
    if company_relationship in ('CUSTOMER_OWNED', 'PROFESSIONAL_PRACTICE') then
        flag_low_current_ratio = (current_ratio < 1.0);
    else
        flag_low_current_ratio = 0;

    flag_unstable_transaction_cashflow = (total_debit_transaction > total_credit_transaction * 0.90);
    flag_history_unavailable = (history_available = 0);

    /* Composite internal rule flag count */
    internal_risk_flag_count = sum(
        flag_high_emi_burden,
        flag_high_credit_utilization,
        flag_low_credit_score,
        flag_high_outstanding_ratio,
        flag_previous_npa,
        flag_prior_missed_streak,
        flag_company_financial_stress,
        flag_negative_turnover_growth,
        flag_low_current_ratio,
        flag_unstable_transaction_cashflow,
        flag_history_unavailable
    );

    /* Prototype rule-based risk grade (distinct from predictive model probability) */
    length internal_rule_risk_grade $10;
    if internal_risk_flag_count <= 1 then internal_rule_risk_grade = 'LOW';
    else if internal_risk_flag_count <= 3 then internal_rule_risk_grade = 'MEDIUM';
    else if internal_risk_flag_count <= 5 then internal_rule_risk_grade = 'HIGH';
    else internal_rule_risk_grade = 'CRITICAL';

    /* Ordered Explainability Reason Condition Strings */
    length risk_reason_1 risk_reason_2 risk_reason_3 $200;

    /* Primary Reason Slot (Priority 1) */
    if flag_high_emi_burden = 1 then
        risk_reason_1 = 'High EMI burden relative to monthly income (EMI ratio > 40%).';
    else if flag_high_credit_utilization = 1 then
        risk_reason_1 = 'Elevated revolving credit utilization (utilization > 75%).';
    else if flag_previous_npa = 1 then
        risk_reason_1 = 'Adverse historical loan record with prior NPA event.';
    else if flag_company_financial_stress = 1 then
        risk_reason_1 = 'Associated employer or business exhibiting synthetic financial stress.';
    else
        risk_reason_1 = 'No major primary rule risk indicator observed.';

    /* Secondary Reason Slot (Priority 2) */
    if flag_low_credit_score = 1 then
        risk_reason_2 = 'Below-benchmark credit bureau score (score < 650).';
    else if flag_prior_missed_streak = 1 then
        risk_reason_2 = 'Prior loan history shows 3 or more consecutive missed monthly installments.';
    else if flag_negative_turnover_growth = 1 then
        risk_reason_2 = 'Employer or business turnover contracting year-over-year.';
    else if flag_low_current_ratio = 1 then
        risk_reason_2 = 'Constrained operating liquidity (business current ratio < 1.0).';
    else
        risk_reason_2 = 'Secondary indicators within normal operating thresholds.';

    /* Tertiary / Additional Reason Slot (Priority 3) */
    if flag_high_outstanding_ratio = 1 then
        risk_reason_3 = 'Elevated outstanding loan principal relative to sanctioned amount.';
    else if flag_unstable_transaction_cashflow = 1 then
        risk_reason_3 = 'Monthly account debits consume over 90% of aggregate monthly credits.';
    else if flag_history_unavailable = 1 then
        risk_reason_3 = 'Prior loan repayment history unavailable in bureau/portfolio records.';
    else
        risk_reason_3 = 'Account transaction and repayment patterns are stable.';
run;

proc freq data=work.npa_features_with_flags;
    tables internal_rule_risk_grade internal_risk_flag_count;
run;

%put NOTE: npa_feature_engineering_and_flags.sas completed successfully.;

