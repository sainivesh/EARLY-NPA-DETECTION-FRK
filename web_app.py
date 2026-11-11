import csv
import json
import os
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import chromadb
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from npa_assessment import (
    build_knowledge_collection,
    generate_assessment,
    retrieve_knowledge,
)


ROOT = Path(__file__).resolve().parent
DATABASE_PATH = ROOT / "bank_data.db"
PAGE_PATH = ROOT / "templates" / "index.html"
KNOWLEDGE_BASE_PATH = ROOT / "NPA_RAG_Knowledge_Base.md"
SCORING_RESULTS_PATH = ROOT / "NPA_DATA_PIPELINE" / "07_SCORED_OUTPUT" / "NPA_SCORING_RESULTS.csv"
RULE_COLLECTION: Any = None
SCORED_CUSTOMERS: dict[int, dict[str, Any]] = {}


def _connect_database() -> sqlite3.Connection:
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _load_scoring_customers() -> None:
    global SCORED_CUSTOMERS
    if not SCORING_RESULTS_PATH.is_file():
        raise FileNotFoundError(f"Scored results file not found: {SCORING_RESULTS_PATH}")
    customers: dict[int, dict[str, Any]] = {}
    with open(SCORING_RESULTS_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = int(row["customer_id"])
            customers[cid] = row
    SCORED_CUSTOMERS = customers
    print(f"Loaded {len(SCORED_CUSTOMERS)} scored customers from {SCORING_RESULTS_PATH.name}", flush=True)


def _json_response(handler: BaseHTTPRequestHandler, status: int, data: dict) -> None:
    payload = json.dumps(data).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(payload)


def _build_customer_profile(record: dict[str, Any]) -> dict[str, Any]:
    customer_id = int(record["customer_id"])
    prob_val = float(record.get("model_event_probability", 0.0))
    pred_cls = int(record.get("model_predicted_class", 0))
    risk_grd = str(record.get("model_risk_grade", "LOW"))
    rec_act = str(record.get("recommended_action", "NORMAL MONITORING"))

    monthly_income = float(record.get("monthly_income", 0))
    emi_amount = float(record.get("emi_amount", 0))
    sanctioned_amount = float(record.get("sanctioned_amount", 0))
    outstanding_amount = float(record.get("outstanding_amount", 0))
    credit_score = int(float(record.get("credit_score", 0)))
    total_credit_limit = float(record.get("total_credit_limit", 0))
    total_credit_balance = float(record.get("total_credit_balance", 0))
    total_credit_tx = float(record.get("total_credit_transaction", 0))
    total_debit_tx = float(record.get("total_debit_transaction", 0))
    total_cash_wd = float(record.get("total_cash_withdrawal", 0))
    collateral_value = float(record.get("collateral_value", 0))

    emi_income_ratio = float(record.get("emi_income_ratio", emi_amount / max(1.0, monthly_income)))
    credit_utilization = float(record.get("credit_utilization", total_credit_balance / max(1.0, total_credit_limit)))
    outstanding_ratio = float(record.get("outstanding_ratio", outstanding_amount / max(1.0, sanctioned_amount)))
    debt_to_income = float(record.get("debt_to_income", (emi_amount + (total_debit_tx / 12.0)) / max(1.0, monthly_income)))
    loan_to_value = float(record.get("loan_to_value", sanctioned_amount / max(1.0, collateral_value)))
    turnover_growth = float(record.get("turnover_growth_pct", 0))
    current_ratio = float(record.get("current_ratio", 0))
    max_missed = int(float(record.get("max_consecutive_missed_months", 0)))
    co_stress = int(float(record.get("financial_stress_flag_synthetic", 0)))
    prev_npa = int(float(record.get("previous_npa_flag", 0)))
    unstable_cf = int(float(record.get("unstable_cash_flow", 0)))
    hist_avail = int(float(record.get("history_available", 1)))
    co_rel = str(record.get("company_relationship", "EMPLOYER"))
    is_biz = co_rel in ("CUSTOMER_OWNED", "PROFESSIONAL_PRACTICE")

    # Master list of all 11 prototype risk indicators with observed vs threshold
    all_indicators = [
        {
            "id": "flag_high_emi_burden",
            "name": "High EMI Burden",
            "is_active": emi_income_ratio > 0.40,
            "observed": f"{emi_income_ratio * 100:.1f}%",
            "threshold": "> 40.0%",
            "explanation": "Contractual monthly EMI consumes over 40% of net monthly income.",
            "evidence": f"EMI: ₹{emi_amount:,.0f} / Income: ₹{monthly_income:,.0f}",
            "category": "Affordability / Debt Service"
        },
        {
            "id": "flag_high_credit_utilization",
            "name": "High Credit Card Utilization",
            "is_active": credit_utilization > 0.75,
            "observed": f"{credit_utilization * 100:.1f}%",
            "threshold": "> 75.0%",
            "explanation": "Outstanding revolving credit balance exceeds 75% of total sanctioned limit.",
            "evidence": f"Balance: ₹{total_credit_balance:,.0f} / Limit: ₹{total_credit_limit:,.0f}",
            "category": "Revolving Debt Exposure"
        },
        {
            "id": "flag_low_credit_score",
            "name": "Low Credit Bureau Score",
            "is_active": credit_score < 650,
            "observed": str(credit_score),
            "threshold": "< 650",
            "explanation": "External bureau credit score falls below prime lending risk benchmark.",
            "evidence": f"Bureau Score: {credit_score} (Scale: 300–900)",
            "category": "Bureau Profile"
        },
        {
            "id": "flag_high_outstanding_ratio",
            "name": "High Outstanding Principal Ratio",
            "is_active": outstanding_ratio > 0.85,
            "observed": f"{outstanding_ratio * 100:.1f}%",
            "threshold": "> 85.0%",
            "explanation": "Unamortized outstanding balance exceeds 85% of original sanctioned loan.",
            "evidence": f"Outstanding: ₹{outstanding_amount:,.0f} / Sanctioned: ₹{sanctioned_amount:,.0f}",
            "category": "Principal Amortization"
        },
        {
            "id": "flag_previous_npa",
            "name": "Historical NPA Event",
            "is_active": prev_npa == 1,
            "observed": "Yes (Default)" if prev_npa == 1 else "No (Clean)",
            "threshold": "Flag == 1",
            "explanation": "Borrower has a recorded default / NPA event on a past closed loan facility.",
            "evidence": f"Historical NPA Events: {record.get('prior_npa_event_count', 0)}",
            "category": "Repayment Track Record"
        },
        {
            "id": "flag_prior_missed_streak",
            "name": "Historical Missed Installment Streak",
            "is_active": max_missed >= 3,
            "observed": f"{max_missed} mos",
            "threshold": ">= 3 consecutive months",
            "explanation": "Prior loan history shows 3 or more consecutive missed monthly installments.",
            "evidence": f"Max Consecutive Missed: {max_missed} installments",
            "category": "Delinquency Severity"
        },
        {
            "id": "flag_company_financial_stress",
            "name": "Employer Financial Stress",
            "is_active": co_stress == 1,
            "observed": "Active Stress" if co_stress == 1 else "Normal",
            "threshold": "Flag == 1",
            "explanation": "Associated employer or business is exhibiting corporate financial distress.",
            "evidence": f"Rating: {record.get('company_credit_rating', 'N/A')}, Status: {record.get('business_status', 'N/A')}",
            "category": "Corporate Balance Sheet"
        },
        {
            "id": "flag_negative_turnover_growth",
            "name": "Employer Revenue Contraction",
            "is_active": turnover_growth < -5.0,
            "observed": f"{turnover_growth:.1f}%",
            "threshold": "< -5.0% YoY",
            "explanation": "Associated employer or business annual turnover contracting over 5% year-over-year.",
            "evidence": f"YoY Turnover Growth: {turnover_growth:.1f}%",
            "category": "Corporate Health"
        },
        {
            "id": "flag_low_current_ratio",
            "name": "Constrained Operating Liquidity",
            "is_active": is_biz and current_ratio < 1.0,
            "observed": f"{current_ratio:.2f}" if is_biz else "N/A (Salaried)",
            "threshold": "< 1.00",
            "explanation": "Business current assets are insufficient to cover short-term operating liabilities.",
            "evidence": f"Current Ratio: {current_ratio:.2f} (Relationship: {co_rel})",
            "category": "Working Capital"
        },
        {
            "id": "unstable_cash_flow",
            "name": "Unstable Transaction Cash Flow",
            "is_active": unstable_cf == 1,
            "observed": "Unstable (Debits > 90%)" if unstable_cf == 1 else "Stable",
            "threshold": "Debits > 90% Credits",
            "explanation": "Monthly account debits consume over 90% of aggregate monthly incoming credits.",
            "evidence": f"Debits: ₹{total_debit_tx:,.0f} / Credits: ₹{total_credit_tx:,.0f}",
            "category": "Account Cash Flow"
        },
        {
            "id": "flag_history_unavailable",
            "name": "Prior Credit History Unavailable",
            "is_active": hist_avail == 0,
            "observed": "Thin File" if hist_avail == 0 else "Established",
            "threshold": "Flag == 0",
            "explanation": "Prior loan repayment history unavailable in bureau/portfolio records.",
            "evidence": "New-to-credit bureau classification",
            "category": "Information Asymmetry"
        }
    ]

    active_flags = [
        {"flag": ind["id"], "label": ind["name"], "observed": ind["observed"]}
        for ind in all_indicators
        if ind["is_active"]
    ]

    return {
        "customer_id": customer_id,
        "demographics": {
            "age": record.get("age"),
            "gender": record.get("gender"),
            "marital_status": record.get("marital_status"),
            "occupation": record.get("occupation"),
            "monthly_income": f"₹{monthly_income:,.2f}" if monthly_income else "N/A",
            "monthly_income_raw": monthly_income,
            "employment_years": record.get("employment_years"),
            "city_type": record.get("city_type"),
        },
        "loan_details": {
            "loan_id": record.get("loan_id"),
            "loan_type": record.get("loan_type"),
            "sanctioned_amount": f"₹{sanctioned_amount:,.2f}" if sanctioned_amount else "N/A",
            "sanctioned_amount_raw": sanctioned_amount,
            "outstanding_amount": f"₹{outstanding_amount:,.2f}" if outstanding_amount else "N/A",
            "outstanding_amount_raw": outstanding_amount,
            "emi_amount": f"₹{emi_amount:,.2f}" if emi_amount else "N/A",
            "emi_amount_raw": emi_amount,
            "interest_rate": f"{float(record.get('interest_rate', 0)):.2f}%" if record.get("interest_rate") else "N/A",
            "collateral_value": f"₹{collateral_value:,.2f}" if collateral_value else "N/A",
            "loan_age_months": record.get("loan_age_months"),
            "remaining_tenure": record.get("remaining_tenure"),
            "current_loan_status": "Active & Performing (DPD = 0)"
        },
        "bureau_and_transactions": {
            "credit_score": credit_score,
            "total_credit_limit": f"₹{total_credit_limit:,.2f}" if total_credit_limit else "N/A",
            "total_credit_balance": f"₹{total_credit_balance:,.2f}" if total_credit_balance else "N/A",
            "active_credit_accounts": record.get("active_credit_accounts"),
            "recent_enquiries": record.get("recent_enquiries"),
            "total_credit_transaction": f"₹{total_credit_tx:,.2f}" if total_credit_tx else "N/A",
            "total_debit_transaction": f"₹{total_debit_tx:,.2f}" if total_debit_tx else "N/A",
            "avg_transaction_count": record.get("avg_transaction_count"),
            "total_cash_withdrawal": f"₹{total_cash_wd:,.2f}" if total_cash_wd else "N/A",
        },
        "financial_ratios": {
            "emi_income_ratio": f"{emi_income_ratio * 100:.1f}%",
            "credit_utilization": f"{credit_utilization * 100:.1f}%",
            "outstanding_ratio": f"{outstanding_ratio * 100:.1f}%",
            "debt_to_income": f"{debt_to_income * 100:.1f}%",
            "loan_to_value": f"{loan_to_value * 100:.1f}%",
        },
        "internal_risk_flags": {
            "flag_count": int(record.get("internal_risk_flag_count", len(active_flags))),
            "rule_grade": record.get("internal_rule_risk_grade", "LOW"),
            "active_flags": active_flags,
        },
        "all_risk_indicators": all_indicators,
        "previous_loan_history": {
            "history_available": "Available" if hist_avail == 1 else "Unavailable (Thin File)",
            "previous_npa_flag": "Defaulted (Prior NPA)" if prev_npa == 1 else "No Prior NPA Default",
            "prior_missed_payment_count": int(float(record.get("prior_missed_payment_count", 0))),
            "prior_avg_dpd": f"{float(record.get('prior_avg_dpd', 0)):.1f} days",
            "prior_max_dpd": f"{float(record.get('prior_max_dpd', 0)):.0f} days",
            "max_consecutive_missed_months": f"{max_missed} months",
            "prior_repayment_pattern": record.get("prior_repayment_pattern", "N/A"),
            "prior_resolution_status": record.get("prior_resolution_status", "N/A"),
            "prior_recovery_amount": f"₹{float(record.get('prior_recovery_amount', 0)):,.2f}" if record.get("prior_recovery_amount") else "N/A",
            "note": "Historical metrics describe previous closed credit facilities. The borrower's active current loan has 0 DPD."
        },
        "company_details": {
            "company_id": record.get("company_id", "N/A"),
            "company_relationship": co_rel,
            "industry": record.get("industry", "N/A"),
            "sub_industry": record.get("sub_industry", "N/A"),
            "company_size": record.get("company_size", "N/A"),
            "company_age_years": record.get("company_age_years", "N/A"),
            "annual_turnover": f"₹{float(record.get('annual_turnover', 0)):,.2f}" if record.get("annual_turnover") else "N/A",
            "turnover_growth_pct": f"{turnover_growth:.1f}%",
            "profit_margin_pct": f"{float(record.get('profit_margin_pct', 0)):.1f}%" if record.get("profit_margin_pct") else "N/A",
            "debt_to_equity": record.get("debt_to_equity", "N/A"),
            "current_ratio": f"{current_ratio:.2f}" if current_ratio else "N/A",
            "company_credit_rating": record.get("company_credit_rating", "N/A"),
            "business_status": record.get("business_status", "OPERATIONAL"),
            "financial_stress_flag_synthetic": "Active Stress" if co_stress == 1 else "Normal Operations",
        },
        "risk_reasons": {
            "risk_reason_1": record.get("risk_reason_1"),
            "risk_reason_2": record.get("risk_reason_2"),
            "risk_reason_3": record.get("risk_reason_3"),
        },
        "sas_model_results": {
            "model_event_probability": f"{prob_val * 100:.2f}%",
            "model_event_probability_raw": prob_val,
            "model_predicted_class": "Yes (Predicted NPA Class 1)" if pred_cls == 1 else "No (Performing Class 0)",
            "model_predicted_class_raw": pred_cls,
            "model_risk_grade": risk_grd,
            "recommended_action": rec_act,
            "scoring_run_id": record.get("scoring_run_id", "RUN_20261111_01"),
            "scoring_timestamp": record.get("scoring_timestamp", "2026-11-11T15:06:30"),
        },
    }


class NPARequestHandler(BaseHTTPRequestHandler):
    server_version = "NPADashboard/1.0"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._serve_page()
        elif path == "/api/customers":
            self._serve_customers()
        elif path == "/api/customer":
            self._serve_single_customer()
        else:
            _json_response(self, 404, {"error": "Not found."})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/summary":
            _json_response(self, 404, {"error": "Not found."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            _json_response(self, 400, {"error": "Invalid request length."})
            return
        if content_length <= 0 or content_length > 4096:
            _json_response(self, 400, {"error": "Invalid request size."})
            return

        try:
            body = json.loads(self.rfile.read(content_length))
            customer_id = int(body["customer_id"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            _json_response(self, 400, {"error": "Provide a valid customer_id."})
            return

        record = SCORED_CUSTOMERS.get(customer_id)
        if record is None:
            _json_response(
                self,
                404,
                {"error": f"Customer {customer_id} not found among the scored customers."},
            )
            return

        api_key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            _json_response(
                self,
                503,
                {"error": "Set API_KEY or OPENAI_API_KEY in .env to generate summaries."},
            )
            return
        if RULE_COLLECTION is None:
            _json_response(
                self,
                503,
                {"error": "The policy knowledge index is not ready."},
            )
            return

        try:
            sources = retrieve_knowledge(RULE_COLLECTION, record)
        except (ValueError, KeyError) as error:
            _json_response(self, 500, {"error": f"Could not retrieve policy context: {error}"})
            return

        try:
            client = OpenAI(
                api_key=api_key,
                base_url=os.getenv("BASE_URL") or None,
                timeout=60,
                max_retries=1,
            )
            assessment = generate_assessment(
                client,
                os.getenv("OPENAI_MODEL", "deepseek-v4.1-flash"),
                record,
                sources,
            )
        except (OpenAIError, ValueError, RuntimeError) as error:
            _json_response(self, 502, {"error": f"Summary generation failed: {error}"})
            return

        # Enforce SAS Model Authority: The SAS output must remain authoritative.
        prob_val = float(record.get("model_event_probability", 0.0))
        pred_cls = int(record.get("model_predicted_class", 0))
        risk_grd = str(record.get("model_risk_grade", "LOW"))
        rec_act = str(record.get("recommended_action", "NORMAL MONITORING"))

        if not isinstance(assessment.get("overview"), dict):
            assessment["overview"] = {}

        assessment["overview"]["npa_flag"] = "Yes (Class 1)" if pred_cls == 1 else "No (Class 0)"
        assessment["overview"]["predicted_npa"] = "Yes" if pred_cls == 1 else "No"
        assessment["overview"]["synthetic_target_probability"] = "Not applicable (Unlabelled live customer)"
        assessment["overview"]["scored_model_probability"] = f"{prob_val * 100:.2f}%"
        assessment["overview"]["model_event_probability"] = f"{prob_val * 100:.2f}%"
        assessment["overview"]["risk_grade"] = risk_grd
        assessment["overview"]["model_risk_grade"] = risk_grd
        assessment["overview"]["recommended_action"] = rec_act
        assessment["overview"]["probability_note"] = (
            "Model event probability generated by SAS Model Studio champion model. "
            "Predictions represent future 12-month NPA risk, not existing delinquency."
        )

        customer_profile = _build_customer_profile(record)

        _json_response(
            self,
            200,
            {
                "assessment": assessment,
                "citations": sources,
                "customer_profile": customer_profile,
            },
        )

    def _serve_page(self) -> None:
        try:
            page = PAGE_PATH.read_bytes()
        except OSError as error:
            _json_response(self, 500, {"error": f"Could not load frontend: {error}"})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def _serve_customers(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        grade_filter = params.get("risk_grade", [None])[0]
        if grade_filter:
            grade_filter = grade_filter.strip().upper()

        class_filter = params.get("predicted_class", [None])[0]
        if class_filter is not None:
            class_filter = class_filter.strip()

        customers = []
        for cid, row in SCORED_CUSTOMERS.items():
            grade = str(row.get("model_risk_grade", "")).strip().upper()
            pred_class = str(row.get("model_predicted_class", "")).strip()

            if grade_filter and grade != grade_filter:
                continue
            if class_filter is not None and pred_class != class_filter:
                continue

            prob = float(row.get("model_event_probability", 0.0))
            customers.append({
                "customer_id": cid,
                "loan_id": row.get("loan_id", ""),
                "npa_id": row.get("model_risk_grade", "LOW"),
                "model_risk_grade": row.get("model_risk_grade", "LOW"),
                "model_predicted_class": int(row.get("model_predicted_class", 0)),
                "model_event_probability": f"{prob * 100:.2f}%",
                "model_event_probability_raw": prob,
                "recommended_action": row.get("recommended_action", "NORMAL MONITORING"),
            })

        _json_response(
            self,
            200,
            {
                "customers": customers,
                "total_count": len(SCORED_CUSTOMERS),
                "scoring_run_id": "RUN_20261111_01",
                "scoring_timestamp": "2026-11-11T15:06:30"
            }
        )

    def _serve_single_customer(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        cid_list = params.get("id", params.get("customer_id", []))
        if not cid_list:
            _json_response(self, 400, {"error": "Missing customer ID parameter (?id=... or ?customer_id=...)." })
            return
        try:
            cid = int(cid_list[0])
        except ValueError:
            _json_response(self, 400, {"error": "Invalid customer ID format."})
            return

        record = SCORED_CUSTOMERS.get(cid)
        if record is None:
            _json_response(self, 404, {"error": f"Customer {cid} not found among scored accounts."})
            return

        profile = _build_customer_profile(record)
        _json_response(self, 200, {"customer": profile})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    global RULE_COLLECTION
    load_dotenv(ROOT / ".env")
    _load_scoring_customers()
    if not KNOWLEDGE_BASE_PATH.is_file():
        raise FileNotFoundError(f"Knowledge base not found: {KNOWLEDGE_BASE_PATH}")

    with closing(_connect_database()) as conn:
        required_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "NPA_MASTER_10K" not in required_tables:
            raise RuntimeError(
                "NPA_MASTER_10K is missing. Build the cleaned sample first."
            )
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(NPA_MASTER_10K)")
        }
        if "NPA_ID" not in columns:
            raise RuntimeError(
                "NPA_ID is missing. Rebuild the sample with clean_data.py."
            )
        invalid_ids = conn.execute(
            """
            SELECT COUNT(*)
            FROM NPA_MASTER_10K
            WHERE (npa_flag = 1 AND NPA_ID IS NULL)
               OR (npa_flag != 1 AND NPA_ID IS NOT NULL)
            """
        ).fetchone()[0]
        if invalid_ids:
            raise RuntimeError(
                "NPA_ID values do not match npa_flag. Rebuild the sample "
                "with clean_data.py."
            )

    markdown = KNOWLEDGE_BASE_PATH.read_text(encoding="utf-8")
    RULE_COLLECTION = build_knowledge_collection(chromadb.Client(), markdown)
    address = ("127.0.0.1", int(os.getenv("PORT", "8000")))
    server = ThreadingHTTPServer(address, NPARequestHandler)
    print(f"\n========================================================", flush=True)
    print(f" NPA Early Detection Dashboard is LIVE and READY", flush=True)
    print(f" URL: http://{address[0]}:{address[1]} or http://localhost:{address[1]}", flush=True)
    print(f" Press Ctrl+C in this terminal to stop the server", flush=True)
    print(f"========================================================\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping NPA dashboard.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
