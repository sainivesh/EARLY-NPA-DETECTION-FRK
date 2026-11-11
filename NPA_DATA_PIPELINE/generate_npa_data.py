#!/usr/bin/env python3
"""
NPA Early Detection - Synthetic Data Generator
Generates realistic, internally consistent synthetic datasets for the NPA Early Detection project.
Target population:
  - 10,000 Labelled development customers (7,000 Train, 3,000 Test)
  - 2,000 Separate unlabelled scoring customers
  - Total: 12,000 customers.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


RANDOM_SEED = 20260814
TOTAL_CUSTOMERS = 12_000
DEV_CUSTOMERS = 10_000
SCORING_CUSTOMERS = 2_000
HISTORY_SAMPLE_RATE = 0.40  # 40% of customers have prior loan history
CURRENT_HISTORY_MONTHS = 12
PRIOR_HISTORY_MONTHS = 24
FUTURE_SIMULATION_MONTHS = 6
AS_OF_DATE = "2026-10-31"


def round_to(values: np.ndarray, base: int) -> np.ndarray:
    return (np.round(values / base) * base).astype(np.int64)


def generate_customer_master(n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Generate customer master dataset."""
    customer_ids = np.arange(1, n + 1, dtype=np.int64)
    age = rng.integers(21, 71, size=n)
    gender = rng.choice(["M", "F"], size=n, p=[0.53, 0.47])

    # Marital status correlated with age
    married_prob = np.clip((age - 21) / 35.0 * 0.70 + 0.12, 0.12, 0.82)
    marital_status = np.where(rng.random(n) < married_prob, "MARRIED", "SINGLE")

    # Occupation
    occupation = rng.choice(
        ["SALARIED", "BUSINESS", "SELF_EMPLOYED", "PROFESSIONAL"],
        size=n,
        p=[0.45, 0.22, 0.18, 0.15],
    )

    # Monthly income based on occupation
    income_factor = np.select(
        [
            occupation == "SALARIED",
            occupation == "BUSINESS",
            occupation == "SELF_EMPLOYED",
            occupation == "PROFESSIONAL",
        ],
        [1.00, 1.25, 0.95, 1.30],
        default=1.0,
    )
    base_income = np.exp(rng.normal(np.log(62_000), 0.48, size=n)) * income_factor
    monthly_income = np.clip(round_to(base_income, 100), 25_000, 350_000)

    # Employment years (strictly <= age - 18)
    max_exp = np.minimum(age - 18, 35)
    employment_years = np.round(rng.uniform(0.5, 0.95, size=n) * max_exp, 1)

    # City type
    city_type = rng.choice(
        ["METRO", "URBAN", "SEMI_URBAN", "RURAL"],
        size=n,
        p=[0.35, 0.35, 0.20, 0.10],
    )

    return pd.DataFrame({
        "customer_id": customer_ids,
        "age": age.astype(np.int64),
        "gender": gender,
        "marital_status": marital_status,
        "occupation": occupation,
        "monthly_income": monthly_income.astype(np.int64),
        "employment_years": employment_years,
        "city_type": city_type,
    })


def generate_loan_account(
    customers: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Generate active, performing current loan account dataset."""
    n = len(customers)
    customer_ids = customers["customer_id"].to_numpy()
    income = customers["monthly_income"].to_numpy(dtype=float)

    loan_ids = 5_000_000 + customer_ids

    loan_types = rng.choice(
        ["HOME", "PERSONAL", "AUTO", "BUSINESS"],
        size=n,
        p=[0.32, 0.30, 0.22, 0.16],
    )

    # Contractual tenure and interest rate by loan type
    term = np.empty(n, dtype=np.int64)
    rate = np.empty(n, dtype=float)

    for ltype, low_term, high_term, low_rate, high_rate in [
        ("HOME", 48, 120, 7.5, 10.5),
        ("PERSONAL", 24, 60, 10.5, 16.5),
        ("AUTO", 36, 84, 8.5, 13.0),
        ("BUSINESS", 24, 84, 9.5, 15.5),
    ]:
        mask = loan_types == ltype
        cnt = int(mask.sum())
        if cnt > 0:
            term[mask] = rng.integers(low_term, high_term + 1, size=cnt)
            rate[mask] = np.round(rng.uniform(low_rate, high_rate, size=cnt), 2)

    # Loan age: MUST be at least 12 months to support 12-month current loan history!
    # Remaining tenure must be positive
    loan_age_months = np.empty(n, dtype=np.int64)
    for i in range(n):
        # loan_age between 12 and term - 6
        max_age = max(12, term[i] - 6)
        loan_age_months[i] = rng.integers(12, max_age + 1)

    remaining_tenure = term - loan_age_months
    assert (loan_age_months >= 12).all(), "loan_age_months must be >= 12"
    assert (remaining_tenure >= 6).all(), "remaining_tenure must be >= 6"

    # EMI target between 15% and 38% of income
    emi_ratio = rng.uniform(0.15, 0.38, size=n)
    emi_target = income * emi_ratio

    monthly_rate = rate / 1200.0
    # Present value annuity factor
    annuity_factor = (1.0 - np.power(1.0 + monthly_rate, -term)) / monthly_rate
    sanctioned_raw = emi_target * annuity_factor
    sanctioned_amount = np.clip(round_to(sanctioned_raw, 5_000), 100_000, 5_000_000).astype(float)

    # Exact EMI from rounded sanctioned amount
    exact_emi = sanctioned_amount * monthly_rate / (1.0 - np.power(1.0 + monthly_rate, -term))
    emi_amount = np.round(exact_emi, 2)

    # Outstanding principal after loan_age_months payments
    # Outstanding = P*(1+r)^k - EMI*((1+r)^k - 1)/r
    compound_k = np.power(1.0 + monthly_rate, loan_age_months)
    outstanding_raw = sanctioned_amount * compound_k - emi_amount * (compound_k - 1.0) / monthly_rate
    outstanding_amount = np.round(np.clip(outstanding_raw, 1_000, sanctioned_amount - 1_000), 2)

    # Collateral value
    collateral_mult = np.select(
        [
            loan_types == "HOME",
            loan_types == "PERSONAL",
            loan_types == "AUTO",
            loan_types == "BUSINESS",
        ],
        [
            rng.uniform(1.20, 1.65, size=n),
            rng.uniform(0.85, 1.15, size=n),
            rng.uniform(1.00, 1.30, size=n),
            rng.uniform(1.15, 1.75, size=n),
        ],
        default=1.0,
    )
    collateral_value = np.round(sanctioned_amount * collateral_mult, 2)

    return pd.DataFrame({
        "customer_id": customer_ids,
        "loan_id": loan_ids,
        "loan_type": loan_types,
        "sanctioned_amount": sanctioned_amount,
        "outstanding_amount": outstanding_amount,
        "emi_amount": emi_amount,
        "interest_rate": rate,
        "collateral_value": collateral_value,
        "loan_age_months": loan_age_months,
        "remaining_tenure": remaining_tenure,
        "loan_status": "ACTIVE",
    })


def generate_current_histories(
    customers: pd.DataFrame, loans: pd.DataFrame, rng: np.random.Generator
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generate emi_history, payment_history, credit_bureau, transaction_history.
    Strictly clean current performance as mandated:
      - 12 EMI records: emi_paid == emi_due, DPD == 0, npa_indicator == 0
      - 12 Payment records: payment_delay == 0, bounce_flag == 0, late_payment_flag == 0
      - Bureau: overdue_accounts == 0, bureau_dpd == 0, writeoff_accounts == 0
      - Transactions: 12 months, non-EMI debits, cash_withdrawal <= debit_transaction
    """
    n = len(customers)
    customer_ids = customers["customer_id"].to_numpy()
    income = customers["monthly_income"].to_numpy(dtype=float)
    emi = loans["emi_amount"].to_numpy(dtype=float)
    occupations = customers["occupation"].to_numpy()

    # Repeat IDs for 12 months
    repeated_ids = np.repeat(customer_ids, CURRENT_HISTORY_MONTHS)
    month_no = np.tile(np.arange(1, CURRENT_HISTORY_MONTHS + 1, dtype=np.int64), n)
    repeated_emi = np.repeat(emi, CURRENT_HISTORY_MONTHS)

    # 1. emi_history.csv
    emi_history = pd.DataFrame({
        "customer_id": repeated_ids,
        "month_no": month_no,
        "emi_due": np.round(repeated_emi, 2),
        "emi_paid": np.round(repeated_emi, 2),
        "days_past_due": np.zeros(n * CURRENT_HISTORY_MONTHS, dtype=np.int64),
        "npa_indicator": np.zeros(n * CURRENT_HISTORY_MONTHS, dtype=np.int64),
    })

    # 2. payment_history.csv
    payment_history = pd.DataFrame({
        "customer_id": repeated_ids,
        "payment_month": month_no,
        "payment_amount": np.round(repeated_emi, 2),
        "payment_delay": np.zeros(n * CURRENT_HISTORY_MONTHS, dtype=np.int64),
        "bounce_flag": np.zeros(n * CURRENT_HISTORY_MONTHS, dtype=np.int64),
        "late_payment_flag": np.zeros(n * CURRENT_HISTORY_MONTHS, dtype=np.int64),
    })

    # 3. credit_bureau.csv
    # Credit score ~ normal(725, 45), bounded [580, 840]
    credit_score = np.clip(np.rint(rng.normal(725, 45, size=n)), 580, 840).astype(np.int64)

    # Credit limit based on income (e.g. 2.5x to 8x monthly income)
    total_credit_limit = np.clip(
        round_to(income * rng.uniform(2.5, 8.0, size=n), 1_000), 50_000, 2_000_000
    ).astype(float)

    # Utilization between 10% and 80%
    utilization = rng.beta(2.2, 4.0, size=n)
    total_credit_balance = np.round(np.minimum(total_credit_limit * utilization, total_credit_limit), 2)

    active_credit_accounts = rng.integers(1, 9, size=n)
    recent_enquiries = rng.integers(0, 6, size=n)

    credit_bureau = pd.DataFrame({
        "customer_id": customer_ids,
        "credit_score": credit_score,
        "total_credit_limit": total_credit_limit,
        "total_credit_balance": total_credit_balance,
        "active_credit_accounts": active_credit_accounts.astype(np.int64),
        "overdue_accounts": np.zeros(n, dtype=np.int64),
        "bureau_dpd": np.zeros(n, dtype=np.int64),
        "recent_enquiries": recent_enquiries.astype(np.int64),
        "writeoff_accounts": np.zeros(n, dtype=np.int64),
    })

    # 4. transaction_history.csv
    # Salaried: recurring credits ~ monthly income. Business: higher variance
    repeated_income = np.repeat(income, CURRENT_HISTORY_MONTHS)
    repeated_occ = np.repeat(occupations, CURRENT_HISTORY_MONTHS)

    credit_mult = np.where(
        repeated_occ == "SALARIED",
        rng.uniform(0.96, 1.15, size=n * CURRENT_HISTORY_MONTHS),
        rng.uniform(0.85, 1.45, size=n * CURRENT_HISTORY_MONTHS),
    )
    credit_txn = np.round(repeated_income * credit_mult, 2)

    # Debits exclude subject loan EMI (approx 30% to 65% of income)
    debit_mult = rng.uniform(0.30, 0.65, size=n * CURRENT_HISTORY_MONTHS)
    debit_txn = np.round(repeated_income * debit_mult, 2)

    # Cash withdrawal is a subset of debit transactions (5% to 35%)
    cash_withdrawal = np.round(debit_txn * rng.uniform(0.05, 0.35, size=n * CURRENT_HISTORY_MONTHS), 2)
    transaction_count = rng.integers(12, 110, size=n * CURRENT_HISTORY_MONTHS)

    transaction_history = pd.DataFrame({
        "customer_id": repeated_ids,
        "transaction_month": month_no,
        "credit_transaction": credit_txn,
        "debit_transaction": debit_txn,
        "transaction_count": transaction_count.astype(np.int64),
        "cash_withdrawal": cash_withdrawal,
    })

    return emi_history, payment_history, credit_bureau, transaction_history


def generate_company_details(
    customers: pd.DataFrame, rng: np.random.Generator, as_of_date: str
) -> pd.DataFrame:
    """Generate 30-column customer_company_details dataset without string truncation."""
    n = len(customers)
    customer_ids = customers["customer_id"].to_numpy()
    occupations = customers["occupation"].to_numpy()
    employment_years = customers["employment_years"].to_numpy(dtype=float)

    company_ids = 90_000_000 + customer_ids

    # Consistent occupation to relationship mapping
    # SALARIED -> EMPLOYER
    # BUSINESS / SELF_EMPLOYED -> CUSTOMER_OWNED
    # PROFESSIONAL -> PROFESSIONAL_PRACTICE (40%) or EMPLOYER (60%)
    company_relationship = []
    for occ in occupations:
        if occ == "SALARIED":
            company_relationship.append("EMPLOYER")
        elif occ in ("BUSINESS", "SELF_EMPLOYED"):
            company_relationship.append("CUSTOMER_OWNED")
        elif occ == "PROFESSIONAL":
            if rng.random() < 0.40:
                company_relationship.append("PROFESSIONAL_PRACTICE")
            else:
                company_relationship.append("EMPLOYER")
        else:
            company_relationship.append("EMPLOYER")

    industries = [
        "Manufacturing",
        "Information Technology",
        "Healthcare and Life Sciences",
        "Retail and Consumer",
        "Financial Services",
        "Construction and Real Estate",
        "Transportation and Logistics",
        "Agriculture and Food Processing",
        "Telecommunications",
        "Education and Professional Services",
    ]
    subindustry_map = {
        "Manufacturing": ["Auto Components", "Industrial Machinery", "Consumer Goods"],
        "Information Technology": ["Software Services", "IT Consulting", "Cloud Services"],
        "Healthcare and Life Sciences": ["Hospitals", "Diagnostics", "Pharmaceuticals"],
        "Retail and Consumer": ["Retail Trade", "Consumer Products", "E-commerce"],
        "Financial Services": ["Banking Services", "Insurance", "Fintech"],
        "Construction and Real Estate": ["Construction", "Residential Property", "Infrastructure"],
        "Transportation and Logistics": ["Road Transport", "Warehousing", "Passenger Mobility"],
        "Agriculture and Food Processing": ["Food Processing", "Agribusiness", "Dairy"],
        "Telecommunications": ["Network Infrastructure", "Telecom Services", "Digital Connectivity"],
        "Education and Professional Services": ["Education", "Legal Services", "Consulting"],
    }
    state_cities = {
        "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik"],
        "Karnataka": ["Bengaluru", "Mysuru", "Mangaluru", "Hubballi"],
        "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli"],
        "Delhi": ["New Delhi", "Delhi"],
        "Telangana": ["Hyderabad", "Warangal", "Karimnagar"],
        "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot"],
        "Uttar Pradesh": ["Lucknow", "Kanpur", "Noida", "Varanasi"],
        "West Bengal": ["Kolkata", "Siliguri", "Durgapur"],
        "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur"],
        "Kerala": ["Kochi", "Thiruvananthapuram", "Kozhikode"],
    }

    selected_industries = rng.choice(industries, size=n)
    selected_subindustries = [
        rng.choice(subindustry_map[ind]) for ind in selected_industries
    ]

    states = list(state_cities.keys())
    selected_states = rng.choice(states, size=n)
    selected_cities = [
        rng.choice(state_cities[st]) for st in selected_states
    ]

    # Company age and tenure
    company_age_years = rng.integers(3, 45, size=n)
    customer_company_tenure_years = np.round(
        np.minimum(employment_years, company_age_years.astype(float)), 1
    )

    # Employee count and size
    employee_count = []
    company_size = []
    for rel in company_relationship:
        if rel in ("CUSTOMER_OWNED", "PROFESSIONAL_PRACTICE"):
            ec = int(rng.integers(2, 60))
        else:
            ec = int(np.clip(rng.lognormal(4.8, 1.1), 8, 15_000))
        employee_count.append(ec)
        if ec <= 10:
            company_size.append("MICRO")
        elif ec <= 50:
            company_size.append("SMALL")
        elif ec <= 250:
            company_size.append("MEDIUM")
        else:
            company_size.append("LARGE")

    employee_count = np.array(employee_count, dtype=np.int64)

    # Financial metrics
    per_emp_turnover = rng.uniform(1_500_000, 4_200_000, size=n)
    annual_turnover = np.round(employee_count * per_emp_turnover, 2)
    turnover_growth_pct = np.round(rng.normal(5.5, 11.0, size=n).clip(-35, 45), 2)
    profit_margin_pct = np.round(rng.normal(10.5, 4.5, size=n).clip(-8, 30), 2)
    debt_to_equity = np.round(rng.lognormal(-0.10, 0.65, size=n).clip(0.1, 7.5), 2)
    current_ratio = np.round(rng.lognormal(0.30, 0.45, size=n).clip(0.4, 5.0), 2)

    financial_stress = (
        (turnover_growth_pct < -6.0)
        | (profit_margin_pct < 2.5)
        | (debt_to_equity > 3.2)
        | (current_ratio < 0.9)
    )
    financial_stress_flag_synthetic = financial_stress.astype(np.int64)

    credit_rating = []
    business_status = []
    for i in range(n):
        if financial_stress[i]:
            if current_ratio[i] < 0.7 or debt_to_equity[i] > 4.5:
                credit_rating.append("CCC")
                business_status.append("DISTRESSED")
            else:
                credit_rating.append(rng.choice(["B", "BB"]))
                business_status.append("UNDER_PRESSURE")
        else:
            if profit_margin_pct[i] > 12.0 and debt_to_equity[i] < 1.2:
                credit_rating.append(rng.choice(["AA", "A"]))
                business_status.append("EXPANDING")
            else:
                credit_rating.append(rng.choice(["BBB", "A"]))
                business_status.append("STABLE")

    sector_outlook_opts = ["POSITIVE", "STABLE", "CAUTIOUS", "NEGATIVE"]
    market_risk_opts = ["LOW", "MEDIUM", "HIGH"]
    scenario_events = [
        "STEADY_DEMAND",
        "RAW_MATERIAL_INFLATION",
        "ORDER_BOOK_EXPANSION",
        "SUPPLY_CHAIN_BOTTLENECK",
        "REGULATORY_COMPLIANCE_SHIFT",
        "EXPORT_MARKET_GROWTH",
    ]

    sector_outlook_synthetic = rng.choice(sector_outlook_opts, size=n, p=[0.35, 0.40, 0.18, 0.07])
    market_risk_level_synthetic = rng.choice(market_risk_opts, size=n, p=[0.40, 0.42, 0.18])
    synthetic_scenario_event = rng.choice(scenario_events, size=n)

    company_names = [
        f"SYNTHCO-{selected_states[i][:5].upper()}-{selected_industries[i][:8].upper()}-{company_ids[i]}"
        for i in range(n)
    ]
    market_lookup_key = [
        f"India | {selected_states[i]} | {selected_industries[i]}"
        for i in range(n)
    ]

    return pd.DataFrame({
        "customer_id": customer_ids,
        "company_id": company_ids,
        "company_name": company_names,
        "company_relationship": company_relationship,
        "occupation": occupations,
        "industry": selected_industries,
        "sub_industry": selected_subindustries,
        "company_city": selected_cities,
        "company_state": selected_states,
        "company_country": ["India"] * n,
        "company_age_years": company_age_years.astype(np.int64),
        "customer_company_tenure_years": customer_company_tenure_years,
        "employee_count": employee_count,
        "company_size": company_size,
        "annual_turnover": annual_turnover,
        "turnover_growth_pct": turnover_growth_pct,
        "profit_margin_pct": profit_margin_pct,
        "debt_to_equity": debt_to_equity,
        "current_ratio": current_ratio,
        "credit_rating": credit_rating,
        "business_status": business_status,
        "sector_outlook_synthetic": sector_outlook_synthetic,
        "market_risk_level_synthetic": market_risk_level_synthetic,
        "financial_stress_flag_synthetic": financial_stress_flag_synthetic,
        "synthetic_scenario_event": synthetic_scenario_event,
        "market_lookup_key": market_lookup_key,
        "market_research_scope": ["INDUSTRY_AND_REGION_ONLY"] * n,
        "company_data_source": ["SYNTHETIC_SCENARIO_DATA"] * n,
        "company_data_is_synthetic": np.ones(n, dtype=np.int64),
        "company_profile_as_of_date": [as_of_date] * n,
    })


def generate_prior_history(
    customers: pd.DataFrame,
    loans: pd.DataFrame,
    rng: np.random.Generator,
    sample_rate: float,
    as_of_date: str,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate NPA_History (24 months for sampled customers) and npa_history_customer_summary.
    Implements all 7 historical repayment patterns:
      1. ALL_PAID_ON_TIME
      2. PAID_3_MONTHS_THEN_STOPPED
      3. PAID_6_MONTHS_THEN_STOPPED
      4. INTERMITTENT_MISSED_REPAID
      5. OCCASIONAL_LATE_BUT_CURED
      6. PRIOR_NPA_UNRESOLVED
      7. PRIOR_NPA_RESOLVED_RECOVERED
    """
    n_all = len(customers)
    customer_ids_all = customers["customer_id"].to_numpy()
    loan_ages = loans["loan_age_months"].to_numpy()
    sanctioned = loans["sanctioned_amount"].to_numpy()

    # Sample customers for prior history
    sample_mask = rng.random(n_all) < sample_rate
    sampled_indices = np.flatnonzero(sample_mask)
    n_sampled = len(sampled_indices)

    sampled_cids = customer_ids_all[sampled_indices]
    sampled_loan_ages = loan_ages[sampled_indices]
    sampled_sanctioned = sanctioned[sampled_indices]

    # Pattern assignment
    # 1: ALL_PAID_ON_TIME (45%)
    # 2: OCCASIONAL_LATE_BUT_CURED (22%)
    # 3: INTERMITTENT_MISSED_REPAID (10%)
    # 4: PAID_3_MONTHS_THEN_STOPPED (9%) -> NPA
    # 5: PAID_6_MONTHS_THEN_STOPPED (6%) -> NPA
    # 6: PRIOR_NPA_UNRESOLVED (4%) -> NPA
    # 7: PRIOR_NPA_RESOLVED_RECOVERED (4%) -> NPA
    pattern_choices = [
        "ALL_PAID_ON_TIME",
        "OCCASIONAL_LATE_BUT_CURED",
        "INTERMITTENT_MISSED_REPAID",
        "PAID_3_MONTHS_THEN_STOPPED",
        "PAID_6_MONTHS_THEN_STOPPED",
        "PRIOR_NPA_UNRESOLVED",
        "PRIOR_NPA_RESOLVED_RECOVERED",
    ]
    pattern_probs = [0.45, 0.22, 0.10, 0.09, 0.06, 0.04, 0.04]
    assigned_patterns = rng.choice(pattern_choices, size=n_sampled, p=pattern_probs)

    # Dates calculation:
    # Current loan started: as_of_date - loan_age months
    # Prior loan ended: 1 month before current loan start date
    # Prior loan started: 24 months before current loan start date
    as_of_period = pd.Period(as_of_date, freq="M")
    current_start_periods = [as_of_period - int(age) for age in sampled_loan_ages]
    prior_end_periods = [p - 1 for p in current_start_periods]
    prior_start_periods = [p - 24 for p in current_start_periods]

    prior_loan_types = rng.choice(["PERSONAL", "AUTO", "HOME", "BUSINESS"], size=n_sampled, p=[0.38, 0.28, 0.20, 0.14])
    prior_sanctioned_arr = np.round(sampled_sanctioned * rng.uniform(0.40, 0.85, size=n_sampled), 2)
    prior_rates = np.round(rng.uniform(8.5, 16.5, size=n_sampled), 2)
    monthly_rates = prior_rates / 1200.0
    prior_emis = np.round(
        prior_sanctioned_arr * monthly_rates / (1.0 - np.power(1.0 + monthly_rates, -24)), 2
    )

    rows = []
    summary_dict = {}

    for i in range(n_sampled):
        cid = int(sampled_cids[i])
        pattern = assigned_patterns[i]
        p_loan_id = 70_000_000 + cid
        p_type = prior_loan_types[i]
        p_sanctioned = float(prior_sanctioned_arr[i])
        p_rate = float(prior_rates[i])
        p_emi = float(prior_emis[i])

        c_start_str = current_start_periods[i].strftime("%Y-%m-%d")
        p_end_str = prior_end_periods[i].strftime("%Y-%m-%d")
        p_start_str = prior_start_periods[i].strftime("%Y-%m-%d")

        is_npa_loan = pattern in (
            "PAID_3_MONTHS_THEN_STOPPED",
            "PAID_6_MONTHS_THEN_STOPPED",
            "PRIOR_NPA_UNRESOLVED",
            "PRIOR_NPA_RESOLVED_RECOVERED",
        )
        prev_npa_flag = 1 if is_npa_loan else 0

        # Month by month simulation for 24 months
        npa_event_month = None
        consecutive_missed = 0
        max_consecutive_missed = 0
        missed_payment_count = 0
        total_recovery = 0.0
        dpd_list = []

        # Determine default month if NPA
        if pattern == "PAID_3_MONTHS_THEN_STOPPED":
            default_start_month = 4  # stops at month 4, DPD reaches 90 at month 6
        elif pattern == "PAID_6_MONTHS_THEN_STOPPED":
            default_start_month = 7  # stops at month 7, DPD reaches 90 at month 9
        elif pattern == "PRIOR_NPA_UNRESOLVED":
            default_start_month = 10  # DPD reaches 90 at month 12
        elif pattern == "PRIOR_NPA_RESOLVED_RECOVERED":
            default_start_month = 8   # DPD reaches 90 at month 10, resolved at month 24
        else:
            default_start_month = 999

        for m in range(1, 25):
            m_period = prior_start_periods[i] + (m - 1)
            m_date_str = m_period.strftime("%Y-%m-%d")

            # Determine payment status
            if pattern == "ALL_PAID_ON_TIME":
                emi_due = p_emi
                emi_paid = p_emi
                dpd = 0
                delay = 0
                paid_flag = 1
                missed_flag = 0
                payment_status = "PAID_ON_TIME"
                bounce_flag = 0
                consecutive_missed = 0

            elif pattern == "OCCASIONAL_LATE_BUT_CURED":
                emi_due = p_emi
                emi_paid = p_emi
                # Delays in month 5, 12, 18
                if m in (5, 12, 18):
                    dpd = int(rng.integers(15, 55))
                    delay = dpd
                    payment_status = "PAID_LATE"
                    bounce_flag = 1 if rng.random() < 0.3 else 0
                else:
                    dpd = 0
                    delay = 0
                    payment_status = "PAID_ON_TIME"
                    bounce_flag = 0
                paid_flag = 1
                missed_flag = 0
                consecutive_missed = 0

            elif pattern == "INTERMITTENT_MISSED_REPAID":
                # Misses month 6 (DPD=30), pays double in month 7 (DPD=0)
                if m == 6:
                    emi_due = p_emi
                    emi_paid = 0.0
                    dpd = 30
                    delay = 30
                    paid_flag = 0
                    missed_flag = 1
                    payment_status = "MISSED"
                    bounce_flag = 1
                    consecutive_missed += 1
                    missed_payment_count += 1
                elif m == 7:
                    emi_due = p_emi
                    emi_paid = p_emi * 2.0
                    dpd = 0
                    delay = 0
                    paid_flag = 1
                    missed_flag = 0
                    payment_status = "CURED"
                    bounce_flag = 0
                    consecutive_missed = 0
                else:
                    emi_due = p_emi
                    emi_paid = p_emi
                    dpd = 0
                    delay = 0
                    paid_flag = 1
                    missed_flag = 0
                    payment_status = "PAID_ON_TIME"
                    bounce_flag = 0
                    consecutive_missed = 0

            else:  # NPA patterns
                if m < default_start_month:
                    emi_due = p_emi
                    emi_paid = p_emi
                    dpd = 0
                    delay = 0
                    paid_flag = 1
                    missed_flag = 0
                    payment_status = "PAID_ON_TIME"
                    bounce_flag = 0
                    consecutive_missed = 0
                else:
                    # After default, customer stops regular EMI payments
                    emi_due = p_emi
                    emi_paid = 0.0
                    months_unpaid = m - default_start_month + 1
                    dpd = min(months_unpaid * 30, 90 + (months_unpaid - 3) * 30)
                    delay = dpd
                    paid_flag = 0
                    missed_flag = 1
                    payment_status = "MISSED"
                    bounce_flag = 1 if months_unpaid <= 2 else 0
                    consecutive_missed += 1
                    missed_payment_count += 1

            dpd_list.append(dpd)
            max_consecutive_missed = max(max_consecutive_missed, consecutive_missed)

            # NPA event flag: exactly on the first month DPD reaches 90
            npa_event_flag = 0
            if is_npa_loan and dpd >= 90 and npa_event_month is None:
                npa_event_flag = 1
                npa_event_month = m

            npa_status_flag = 1 if (npa_event_month is not None and m >= npa_event_month and m < 24) else 0

            # Resolution details at month 24
            recovery_amount = 0.0
            if m == 24 and is_npa_loan:
                if pattern in ("PAID_3_MONTHS_THEN_STOPPED", "PAID_6_MONTHS_THEN_STOPPED"):
                    recovery_amount = round(p_sanctioned * rng.uniform(0.35, 0.65), 2)
                    total_recovery = recovery_amount
                elif pattern == "PRIOR_NPA_RESOLVED_RECOVERED":
                    recovery_amount = round(p_sanctioned * rng.uniform(0.65, 0.90), 2)
                    total_recovery = recovery_amount
                else:  # PRIOR_NPA_UNRESOLVED
                    recovery_amount = 0.0
                    total_recovery = 0.0

            rows.append({
                "customer_id": cid,
                "prior_loan_id": p_loan_id,
                "prior_loan_type": p_type,
                "prior_loan_start_date": p_start_str,
                "prior_loan_end_date": p_end_str,
                "current_loan_start_date": c_start_str,
                "prior_loan_tenure_months": 24,
                "prior_loan_sanctioned_amount": p_sanctioned,
                "prior_loan_interest_rate": p_rate,
                "prior_loan_emi_amount": p_emi,
                "history_month_no": m,
                "history_month_date": m_date_str,
                "emi_due": emi_due,
                "emi_paid": emi_paid,
                "days_past_due": dpd,
                "payment_delay_days": delay,
                "paid_flag": paid_flag,
                "missed_payment_flag": missed_flag,
                "payment_status": payment_status,
                "bounce_flag": bounce_flag,
                "consecutive_missed_months": consecutive_missed,
                "repayment_pattern": pattern,
                "previous_npa_flag": prev_npa_flag,
                "npa_event_flag": npa_event_flag,
                "npa_status_flag": npa_status_flag,
                "previous_npa_date": (
                    (prior_start_periods[i] + (npa_event_month - 1)).strftime("%Y-%m-%d")
                    if npa_event_month is not None else ""
                ),
                "prior_loan_status": (
                    "CLOSED_REGULAR" if not is_npa_loan
                    else ("CLOSED_NPA_WRITTEN_OFF" if pattern == "PRIOR_NPA_UNRESOLVED" else "CLOSED_NPA_RESOLVED")
                ),
                "resolution_status": (
                    "CLOSED_AS_SCHEDULED" if not is_npa_loan
                    else ("WRITTEN_OFF" if pattern == "PRIOR_NPA_UNRESOLVED"
                          else ("RECOVERED" if pattern == "PRIOR_NPA_RESOLVED_RECOVERED" else "SETTLED"))
                ),
                "resolution_date": p_end_str if is_npa_loan else "",
                "recovery_amount": recovery_amount,
            })

        summary_dict[cid] = {
            "customer_id": cid,
            "history_available": 1,
            "previous_npa_flag": prev_npa_flag,
            "prior_missed_payment_count": missed_payment_count,
            "prior_avg_dpd": round(float(np.mean(dpd_list)), 2),
            "prior_max_dpd": int(np.max(dpd_list)),
            "max_consecutive_missed_months": int(max_consecutive_missed),
            "prior_npa_event_count": 1 if prev_npa_flag == 1 else 0,
            "repayment_pattern": pattern,
            "resolution_status": (
                "CLOSED_AS_SCHEDULED" if not is_npa_loan
                else ("WRITTEN_OFF" if pattern == "PRIOR_NPA_UNRESOLVED"
                      else ("RECOVERED" if pattern == "PRIOR_NPA_RESOLVED_RECOVERED" else "SETTLED"))
            ),
            "prior_recovery_amount": total_recovery,
        }

    npa_history_df = pd.DataFrame(rows)

    # Build full customer summary (including unsampled customers who have history_available=0)
    summary_rows = []
    for cid in customer_ids_all:
        cid_int = int(cid)
        if cid_int in summary_dict:
            summary_rows.append(summary_dict[cid_int])
        else:
            summary_rows.append({
                "customer_id": cid_int,
                "history_available": 0,
                "previous_npa_flag": 0,
                "prior_missed_payment_count": 0,
                "prior_avg_dpd": 0.0,
                "prior_max_dpd": 0,
                "max_consecutive_missed_months": 0,
                "prior_npa_event_count": 0,
                "repayment_pattern": "HISTORY_UNAVAILABLE",
                "resolution_status": "NOT_APPLICABLE",
                "prior_recovery_amount": 0.0,
            })

    history_summary_df = pd.DataFrame(summary_rows)

    return npa_history_df, history_summary_df


def generate_future_simulation_and_target(
    customers: pd.DataFrame,
    loans: pd.DataFrame,
    credit_bureau: pd.DataFrame,
    history_summary: pd.DataFrame,
    company_details: pd.DataFrame,
    rng: np.random.Generator,
    dev_count: int = DEV_CUSTOMERS,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Simulate 6 future monthly repayments for the labelled development population (10,000 customers).
    NO future records or outcome rows for scoring customers.
    Simulates true repayment behavior:
      - Arrears carry forward
      - DPD calculated from oldest unpaid installment
      - NPA occurs when DPD reaches 90 days
      - Once NPA occurs, event is preserved
      - Calibrated to produce ~8-15% positive NPA rate naturally.
    """
    dev_customers = customers.iloc[:dev_count].copy()
    dev_loans = loans.iloc[:dev_count].copy()
    dev_bureau = credit_bureau.iloc[:dev_count].copy()
    dev_history = history_summary.iloc[:dev_count].copy()
    dev_company = company_details.iloc[:dev_count].copy()

    cids = dev_customers["customer_id"].to_numpy()
    incomes = dev_customers["monthly_income"].to_numpy(dtype=float)
    emis = dev_loans["emi_amount"].to_numpy(dtype=float)
    scores = dev_bureau["credit_score"].to_numpy(dtype=float)
    limits = dev_bureau["total_credit_limit"].to_numpy(dtype=float)
    balances = dev_bureau["total_credit_balance"].to_numpy(dtype=float)

    prior_npa = dev_history["previous_npa_flag"].to_numpy()
    prior_streak = dev_history["max_consecutive_missed_months"].to_numpy()
    comp_stress = dev_company["financial_stress_flag_synthetic"].to_numpy()
    comp_growth = dev_company["turnover_growth_pct"].to_numpy()

    # Latent risk formula
    emi_ratio = emis / np.maximum(1.0, incomes)
    utilization = balances / np.maximum(1.0, limits)

    # Risk score composite (0 to 1) based on observable financial burden and stress
    risk_score = (
        0.28 * np.clip((emi_ratio - 0.18) / 0.22, 0, 1.2)
        + 0.22 * utilization
        + 0.20 * np.clip((740.0 - scores) / 140.0, 0, 1.0)
        + 0.18 * prior_npa
        + 0.12 * comp_stress
        + 0.08 * (prior_streak >= 3)
        + 0.06 * (comp_growth < -6.0)
    )

    # Latent financial stress includes customer risk score plus idiosyncratic shock
    latent_stress = risk_score + rng.normal(0, 0.07, size=dev_count)

    # Threshold 0.49 produces ~10.8% NPA rate (cleanly in 8-15% target range)
    # Temporary stress occurs for customers just below default threshold (0.38 - 0.49)
    simulation_rows = []
    npa_flag_dict = {}

    future_months = [
        "2026-11-01",
        "2026-12-01",
        "2027-01-01",
        "2027-02-01",
        "2027-03-01",
        "2027-04-01",
    ]

    for i in range(dev_count):
        cid = int(cids[i])
        emi = float(emis[i])
        stress = latent_stress[i]

        becomes_npa = stress > 0.49
        temp_stress = (not becomes_npa) and (stress > 0.38) and (rng.random() < 0.40)

        outstanding_arrears = 0.0
        oldest_unpaid_month = None
        has_reached_npa = False
        dpd = 0

        # Scenario assignment
        if becomes_npa:
            # 70% stop at Month 1 (reach 90 DPD at Month 3)
            # 30% stop at Month 2 or 3 (reach 90 DPD at Month 4 or 5)
            if rng.random() < 0.70:
                stop_month = 1
            else:
                stop_month = rng.integers(2, 4)
        elif temp_stress:
            # Misses in month 1 or 2, cures in month 3
            stop_month = rng.integers(1, 3)
            cure_month = stop_month + rng.integers(1, 3)
        else:
            stop_month = 999
            cure_month = 999

        for m_idx, as_of_m in enumerate(future_months, start=1):
            emi_due = emi

            if not has_reached_npa:
                if becomes_npa:
                    if m_idx < stop_month:
                        emi_paid = emi_due
                        payment_status = "PAID_ON_TIME"
                    else:
                        emi_paid = 0.0
                        payment_status = "MISSED"
                        if oldest_unpaid_month is None:
                            oldest_unpaid_month = m_idx
                        outstanding_arrears += emi_due
                        # DPD from oldest unpaid installment
                        dpd = (m_idx - oldest_unpaid_month + 1) * 30
                        if dpd >= 90:
                            has_reached_npa = True

                elif temp_stress:
                    if m_idx == stop_month:
                        emi_paid = 0.0
                        payment_status = "MISSED"
                        if oldest_unpaid_month is None:
                            oldest_unpaid_month = m_idx
                        outstanding_arrears += emi_due
                        dpd = 30
                    elif m_idx == cure_month:
                        # Double payment cures arrears
                        emi_paid = emi_due + outstanding_arrears
                        outstanding_arrears = 0.0
                        oldest_unpaid_month = None
                        dpd = 0
                        payment_status = "CURED"
                    elif m_idx > stop_month and m_idx < cure_month:
                        emi_paid = 0.0
                        outstanding_arrears += emi_due
                        dpd = (m_idx - oldest_unpaid_month + 1) * 30
                        payment_status = "MISSED"
                    else:
                        emi_paid = emi_due
                        dpd = 0
                        payment_status = "PAID_ON_TIME"

                else:  # Performing
                    emi_paid = emi_due
                    dpd = 0
                    outstanding_arrears = 0.0
                    payment_status = "PAID_ON_TIME"
            else:
                # Once NPA occurs, preserve NPA event and status, no regular EMI paid
                emi_paid = 0.0
                outstanding_arrears += emi_due
                dpd = (m_idx - oldest_unpaid_month + 1) * 30
                payment_status = "NPA_DEFAULT"

            npa_indicator = 1 if has_reached_npa else 0

            simulation_rows.append({
                "customer_id": cid,
                "future_month": m_idx,
                "emi_due": np.round(emi_due, 2),
                "emi_paid": np.round(emi_paid, 2),
                "days_past_due": dpd,
                "npa_indicator": npa_indicator,
                "payment_status": payment_status,
                "outstanding_arrears": np.round(outstanding_arrears, 2),
                "as_of_date": as_of_m,
            })

        npa_flag_dict[cid] = 1 if has_reached_npa else 0

    future_sim_df = pd.DataFrame(simulation_rows)

    outcome_rows = [
        {"customer_id": cid, "npa_flag": npa_flag_dict[cid]}
        for cid in cids
    ]
    future_outcome_df = pd.DataFrame(outcome_rows)

    return future_sim_df, future_outcome_df


def generate_customer_split(
    future_outcome: pd.DataFrame,
    total_customers: int = TOTAL_CUSTOMERS,
    dev_count: int = DEV_CUSTOMERS,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """
    Generate stratified train/test split for development customers (7,000 / 3,000)
    and assign separate scoring population (2,000).
    """
    rng = np.random.Generator(np.random.PCG64(seed))

    dev_cids = future_outcome["customer_id"].to_numpy()
    dev_flags = future_outcome["npa_flag"].to_numpy()

    # Stratified 70:30 split
    pos_indices = np.flatnonzero(dev_flags == 1)
    neg_indices = np.flatnonzero(dev_flags == 0)

    rng.shuffle(pos_indices)
    rng.shuffle(neg_indices)

    pos_train_count = int(round(len(pos_indices) * 0.70))
    neg_train_count = 7_000 - pos_train_count

    train_indices = np.concatenate([pos_indices[:pos_train_count], neg_indices[:neg_train_count]])
    test_indices = np.concatenate([pos_indices[pos_train_count:], neg_indices[neg_train_count:]])

    split_set_map = {}
    for idx in train_indices:
        split_set_map[dev_cids[idx]] = ("DEVELOPMENT", "TRAIN")
    for idx in test_indices:
        split_set_map[dev_cids[idx]] = ("DEVELOPMENT", "TEST")

    # Scoring customers (IDs dev_count + 1 to total_customers)
    scoring_rows = []
    for cid in range(1, total_customers + 1):
        if cid in split_set_map:
            role, sset = split_set_map[cid]
        else:
            role, sset = ("SCORING", "SCORING")
        scoring_rows.append({
            "customer_id": cid,
            "population_role": role,
            "split_set": sset,
            "random_seed": seed,
        })

    return pd.DataFrame(scoring_rows)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic NPA data package.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Root folder for NPA_DATA_PIPELINE",
    )
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Random seed")
    parser.add_argument("--total-customers", type=int, default=TOTAL_CUSTOMERS, help="Total customers (12,000)")
    parser.add_argument("--dev-customers", type=int, default=DEV_CUSTOMERS, help="Development customers (10,000)")
    args = parser.parse_args()

    root_dir = args.output_dir
    raw_dir = root_dir / "01_RAW_DATASETS"
    future_dir = root_dir / "02_FUTURE_SIMULATION_AND_TARGET"
    split_dir = root_dir / "03_POPULATION_AND_SAS_INPUTS"
    sql_dir = root_dir / "04_SQL_DATABASE"
    val_dir = root_dir / "08_VALIDATION"

    for d in [raw_dir, future_dir, split_dir, sql_dir, val_dir]:
        d.mkdir(parents=True, exist_ok=True)

    rng = np.random.Generator(np.random.PCG64(args.seed))

    print(f"Generating NPA synthetic data with seed {args.seed}...")
    print(f"Total customers: {args.total_customers} (Dev: {args.dev_customers}, Scoring: {args.total_customers - args.dev_customers})")

    # 1. Customer Master
    print("Generating customer_master...")
    customers = generate_customer_master(args.total_customers, rng)
    customers.to_csv(raw_dir / "customer_master.csv", index=False, encoding="utf-8")

    # 2. Loan Account
    print("Generating loan_account...")
    loans = generate_loan_account(customers, rng)
    loans.to_csv(raw_dir / "loan_account.csv", index=False, encoding="utf-8")

    # 3-6. Histories
    print("Generating current loan histories (EMI, Payment, Bureau, Transactions)...")
    emi_hist, pmt_hist, bureau, txn_hist = generate_current_histories(customers, loans, rng)
    emi_hist.to_csv(raw_dir / "emi_history.csv", index=False, encoding="utf-8")
    pmt_hist.to_csv(raw_dir / "payment_history.csv", index=False, encoding="utf-8")
    bureau.to_csv(raw_dir / "credit_bureau.csv", index=False, encoding="utf-8")
    txn_hist.to_csv(raw_dir / "transaction_history.csv", index=False, encoding="utf-8")

    # 7. Prior History
    print("Generating NPA_History (24 months for sample)...")
    npa_hist, hist_summary = generate_prior_history(
        customers, loans, rng, sample_rate=HISTORY_SAMPLE_RATE, as_of_date=AS_OF_DATE
    )
    npa_hist.to_csv(raw_dir / "NPA_History.csv", index=False, encoding="utf-8")
    hist_summary.to_csv(raw_dir / "npa_history_customer_summary.csv", index=False, encoding="utf-8")

    # 8. Customer Company Details
    print("Generating customer_company_details (30 columns)...")
    company_details = generate_company_details(customers, rng, as_of_date=AS_OF_DATE)
    company_details.to_csv(raw_dir / "customer_company_details.csv", index=False, encoding="utf-8")

    # 9-10. Future Simulation and Target
    print("Generating future_repayment_simulation and future_outcome for 10,000 dev customers...")
    future_sim, future_outcome = generate_future_simulation_and_target(
        customers, loans, bureau, hist_summary, company_details, rng, dev_count=args.dev_customers
    )
    future_sim.to_csv(future_dir / "future_repayment_simulation.csv", index=False, encoding="utf-8")
    future_outcome.to_csv(future_dir / "future_outcome.csv", index=False, encoding="utf-8")

    npa_rate = future_outcome["npa_flag"].mean() * 100.0
    npa_count = int(future_outcome["npa_flag"].sum())
    print(f"Future NPA Outcomes: {npa_count} positive events / {len(future_outcome)} ({npa_rate:.2f}%)")
    assert 8.0 <= npa_rate <= 15.0, f"NPA rate {npa_rate:.2f}% is outside the 8-15% target range!"

    # 11. Customer Split
    print("Generating NPA_CUSTOMER_SPLIT...")
    customer_split = generate_customer_split(
        future_outcome, total_customers=args.total_customers, dev_count=args.dev_customers, seed=args.seed
    )
    customer_split.to_csv(split_dir / "NPA_CUSTOMER_SPLIT.csv", index=False, encoding="utf-8")

    # 12. Populate SQLite Database
    db_path = sql_dir / "npa_project.sqlite"
    if db_path.exists():
        db_path.unlink()

    print(f"Populating SQLite database at {db_path}...")
    conn = sqlite3.connect(db_path)
    with conn:
        customers.to_sql("customer_master", conn, index=False)
        loans.to_sql("loan_account", conn, index=False)
        emi_hist.to_sql("emi_history", conn, index=False)
        pmt_hist.to_sql("payment_history", conn, index=False)
        bureau.to_sql("credit_bureau", conn, index=False)
        txn_hist.to_sql("transaction_history", conn, index=False)
        npa_hist.to_sql("NPA_History", conn, index=False)
        company_details.to_sql("customer_company_details", conn, index=False)
        future_sim.to_sql("future_repayment_simulation", conn, index=False)
        future_outcome.to_sql("future_outcome", conn, index=False)
        customer_split.to_sql("NPA_CUSTOMER_SPLIT", conn, index=False)
        hist_summary.to_sql("npa_history_customer_summary", conn, index=False)

        # Create helpful indexes
        conn.execute("CREATE UNIQUE INDEX idx_cm_cid ON customer_master(customer_id)")
        conn.execute("CREATE UNIQUE INDEX idx_la_cid ON loan_account(customer_id)")
        conn.execute("CREATE INDEX idx_eh_cid ON emi_history(customer_id, month_no)")
        conn.execute("CREATE INDEX idx_ph_cid ON payment_history(customer_id, payment_month)")
        conn.execute("CREATE UNIQUE INDEX idx_cb_cid ON credit_bureau(customer_id)")
        conn.execute("CREATE INDEX idx_th_cid ON transaction_history(customer_id, transaction_month)")
        conn.execute("CREATE INDEX idx_nh_cid ON NPA_History(customer_id, history_month_no)")
        conn.execute("CREATE UNIQUE INDEX idx_ccd_cid ON customer_company_details(customer_id)")
        conn.execute("CREATE INDEX idx_frs_cid ON future_repayment_simulation(customer_id, future_month)")
        conn.execute("CREATE UNIQUE INDEX idx_fo_cid ON future_outcome(customer_id)")
        conn.execute("CREATE UNIQUE INDEX idx_cs_cid ON NPA_CUSTOMER_SPLIT(customer_id)")

    conn.close()

    # Save Generation Metadata
    metadata = {
        "generation_timestamp": datetime.now().isoformat(),
        "random_seed": args.seed,
        "as_of_date": AS_OF_DATE,
        "total_customers": args.total_customers,
        "development_customers": args.dev_customers,
        "train_customers": 7_000,
        "test_customers": 3_000,
        "scoring_customers": args.total_customers - args.dev_customers,
        "npa_positive_count": npa_count,
        "npa_positive_rate_pct": round(npa_rate, 4),
        "tables": {
            "customer_master": len(customers),
            "loan_account": len(loans),
            "emi_history": len(emi_hist),
            "payment_history": len(pmt_hist),
            "credit_bureau": len(bureau),
            "transaction_history": len(txn_hist),
            "NPA_History": len(npa_hist),
            "customer_company_details": len(company_details),
            "future_repayment_simulation": len(future_sim),
            "future_outcome": len(future_outcome),
            "NPA_CUSTOMER_SPLIT": len(customer_split),
            "npa_history_customer_summary": len(hist_summary),
        },
    }
    with open(val_dir / "NPA_GENERATION_METADATA.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("Generation complete! All files generated and verified.")


if __name__ == "__main__":
    main()
