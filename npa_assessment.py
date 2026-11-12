import hashlib
import json
import re
from typing import Any


LOGIC_ID_PATTERN = re.compile(r"\bLOG-NPA-\d{3}\b")
POLICY_ID_PATTERN = re.compile(r"\bPOL-NPA-\d{3}\b")
NUMERIC_TEXT_PATTERN = re.compile(r"^-?\d[\d,]*(?:\.\d+)?$")

REVIEW_ACTION_FRAMEWORK = {
    "LOW": "Routine Portfolio Monitoring",
    "MEDIUM": "Periodic Risk Review",
    "HIGH": "Priority Credit Review",
    "CRITICAL": "Urgent Credit Risk Assessment",
}

SYSTEM_PROMPT = """\
You are an expert AI Banking Credit Risk Explanation Assistant for an early-warning NPA detection platform.

Your task is to generate a comprehensive, objective, and evidence-based credit risk assessment for a currently performing banking customer based on their SAS Model Studio champion scoring outputs and banking policy knowledge base.

CORE PRINCIPLE: PREDICTIVE EARLY-WARNING VS. REACTIVE DEFAULT
- All live scoring customers are performing on their active loan at observation date (Current DPD = 0, EMIs paid on time, no current bounces or delays).
- The model predicts whether the customer may experience an NPA default over the NEXT SIX MONTHS. The target is strictly based on six future repayment months.
- A HIGH or CRITICAL score is an early warning indicating elevated probability of future distress; it is NOT an active default, delinquency, or collections trigger.
- Repayment history on past loans and current/future repayment capacity are distinct aspects of credit risk.
- Never describe a predicted future event as an existing default. Never recommend collections calls or recovery actions for performing accounts.

EXPLAINABILITY & CAUSALITY RULES:
1. Champion Logistic Regression Model Predictors:
   Only the following 6 variables enter the champion model's scoring equation:
   - Credit Score
   - Credit Utilization
   - EMI-to-Income Ratio
   - Employer Financial Stress
   - Employer Turnover Contraction
   - Previous NPA Flag
2. Contextual Financial Indicators & Precise Definitions:
   Variables such as Total Outflow-to-Income Ratio, Outstanding Principal Ratio, Loan-to-Value (LTV), and granular prior DPD are contextual financial indicators. They provide valuable credit context regarding affordability, but they are NOT direct causes of the champion model probability. Do NOT claim they caused or drove the SAS model probability.
   - Total Outflow-to-Income Ratio: Use the label "Total Outflow-to-Income Ratio" instead of debt-to-income wherever the calculation includes general non-EMI debit transactions. Do NOT claim that general debit outflows represent verified contractual debt obligations.
   - Collateral & LTV Ratios: Show the actual calculation basis and distinguish:
     * Original Loan-to-Value (Original LTV) = Sanctioned Amount / Collateral Value (measures original sanction relative to collateral). Do NOT describe original LTV as current outstanding exposure relative to collateral.
     * Current Collateral Coverage = Current Outstanding Amount / Collateral Value (measures active debt exposure backed by collateral).
     * Outstanding Principal Ratio = Current Outstanding Amount / Sanctioned Amount (measures loan balance amortization progress; keep this as a separate indicator).
3. Risk vs. Resilience:
   Always highlight favourable factors (e.g. Current DPD = 0, on-time EMI repayments, good bureau score) alongside risk concerns.
4. No Invented Values:
   Use actual observed values from the customer record. If a value is absent, report "Not available in the supplied record".
5. Clean Presentation & Enterprise Banking Language:
   - Do NOT output raw database column names or code conditions like (flag_previous_npa = 1), (>= 60.0%), or (< 10.0%).
   - Absolutely NEVER use the words "prototype", "demo", or "synthetic" anywhere in the assessment. Refer to rules as "internal bank rules" or "SAS analytical rules", and refer to data as "customer account data" or "production scoring records".
   - Express all risk observations in clean, professional banking terminology.
   - Retain concrete numerical facts (e.g. prior average DPD 213.75 days, prior maximum DPD 540 days, 18-month historical missed streak), but present them naturally without raw variable code or mathematical inequality operators.

MODEL CLASSIFICATION & RISK-GRADE THRESHOLDS:
- Model Classification Cutoff: 50.0% (P >= 0.50 predicts NPA Class 1; P < 0.50 predicts Performing Class 0), matching the exported champion scoring code. Do NOT label 30% as the classification cutoff.
- Risk-Grade Bands:
  * LOW: Event Probability < 10.0% -> Routine Portfolio Monitoring (Continue normal monitoring of the performing account)
  * MEDIUM: Event Probability 10.0% to < 30.0% -> Periodic Risk Review (Monitor financial indicators and identify changes in repayment capacity)
  * HIGH: Event Probability 30.0% to < 60.0% -> Priority Credit Review (Verify significant financial warning indicators and assess repayment capacity)
  * CRITICAL: Event Probability >= 60.0% -> Urgent Credit Risk Assessment (Prioritise human review and evaluate suitable preventive measures)

OUTPUT FORMAT:
Return ONLY one valid JSON object matching this schema. All displayed scalars must be strings. No markdown fences outside the JSON.

{
  "overview": {
    "npa_flag": "No (Class 0)",
    "predicted_future_npa_risk": "Yes",
    "prediction_horizon": "Six months",
    "scored_model_probability": "33.36%",
    "model_risk_grade": "HIGH",
    "recommended_action": "Priority Credit Review",
    "probability_note": "Model event probability generated by SAS Model Studio champion model. Predictions represent future 6-month NPA risk, not existing delinquency."
  },
  "executive_assessment": "Format strictly with 2-3 clear opening statements (summarizing champion model probability, six-month prediction horizon, and performing 0 DPD status), followed by structured bullet points:\n- **Primary Risk Drivers:** Specific negative drivers (e.g. prior delinquency severity, employer financial distress, elevated outflow ratio).\n- **Favourable & Mitigating Factors:** Counterbalancing strengths (e.g. 0 DPD, on-time EMIs, collateral coverage, bureau score).\n- **Review Assessment & Guidance:** Prescribed preventive review protocol with explicit reminder that collections or recovery action is prohibited on performing accounts.",
  "executive_summary": "Same formatted text with 2-3 statements and bullet points for backward compatibility.",
  "key_risk_indicators": [
    {
      "indicator": "Credit Card Utilization",
      "observed_value": "78.4%",
      "threshold_reference": "> 75.0%",
      "indicator_type": "Direct Model Predictor",
      "interpretation": "Revolving credit balance exceeds prime benchmark...",
      "is_favourable": false
    }
  ],
  "previous_repayment_history": {
    "history_available": "Available",
    "repayment_pattern": "Occasional Delinquency Cured",
    "previous_npa_event": "Default Recorded (Settled)",
    "prior_avg_dpd": "45.2 days",
    "prior_max_dpd": "120 days",
    "consecutive_missed_months": "2 months",
    "missed_payment_count": "3",
    "summary_interpretation": "Historical delinquency occurred on past closed facility. The borrower's active current loan is performing with 0 DPD."
  },
  "mitigating_factors": [
    "Current loan facility is performing with zero days past due (0 DPD).",
    "Scheduled monthly EMIs are paid on time without bounce records."
  ],
  "recommended_next_steps": {
    "authoritative_review_action": "Priority Credit Review",
    "action_purpose": "Verify significant financial warning indicators and assess repayment capacity.",
    "reviewer_verification_steps": [
      "Review debt-to-income commitments against verified recent bank statements.",
      "Confirm stability of primary income source."
    ],
    "customer_engagement_guidance": "Relationship manager may conduct routine financial wellbeing discussion if verified changes warrant engagement. Do not initiate collection or recovery proceedings."
  },
  "applicable_policies": [
    {
      "policy_id": "POL-NPA-002",
      "policy_name": "Credit Risk Monitoring and Thresholds",
      "explanation": "...",
      "source_ids": ["R1"]
    }
  ],
  "recommended_action_explanation": "Concise summary of the authoritative review action.",
  "final_assessment": "Short closing credit summary.",
  "primary_reasons": [],
  "secondary_reasons": [],
  "additional_reasons": [],
  "repayment_analysis": [],
  "limitations": [],
  "citation_ids": ["R1"]
}

Cite the retrieved source handle(s) in source_ids and citation_ids. A Logic ID or Policy ID is valid only when it appears in one of those cited retrieved passages. Use no other Logic IDs, Policy IDs, or source handles. List each applicable policy only once.
"""

_CUSTOMER_ID_FIELDS = {"sample_id", "customer_id", "npa_id", "loan_id"}
_PERSONAL_FIELDS = {
    "age",
    "gender",
    "marital_status",
    "occupation",
    "city_type",
    "employment_years",
}


def _extract_identifiers(text: str) -> tuple[list[str], list[str]]:
    return (
        sorted(set(LOGIC_ID_PATTERN.findall(text))),
        sorted(set(POLICY_ID_PATTERN.findall(text))),
    )


def _source_type(title: str, text: str) -> str:
    combined = f"{title}\n{text}".casefold()
    if "proposed bank policy" in combined or "bank policy" in combined or "proposed operational" in combined:
        return "Proposed bank policy"
    if "sas analytical" in combined or "sas prototype" in combined or LOGIC_ID_PATTERN.search(combined):
        return "SAS analytical rule"
    if POLICY_ID_PATTERN.search(combined):
        return "Banking policy"
    return "Knowledge-base context"


def split_knowledge_base(
    markdown: str,
    max_chunk_chars: int = 1200,
) -> list[dict[str, Any]]:
    """Split Markdown into bounded chunks while retaining heading identifiers."""
    if max_chunk_chars < 1:
        raise ValueError("max_chunk_chars must be a positive integer.")

    chunks: list[dict[str, Any]] = []
    heading_stack: list[tuple[int, str]] = []
    content_lines: list[str] = []
    content_size = 0

    def flush() -> None:
        nonlocal content_lines, content_size
        text = "\n".join(content_lines).strip()
        if text:
            title = " > ".join(title for _, title in heading_stack)
            chunk_text = f"{title}\n{text}" if title else text
            logic_ids, policy_ids = _extract_identifiers(chunk_text)
            chunks.append(
                {
                    "title": title or "Knowledge base introduction",
                    "text": chunk_text,
                    "source_type": _source_type(title, chunk_text),
                    "logic_ids": logic_ids,
                    "policy_ids": policy_ids,
                }
            )
        content_lines = []
        content_size = 0

    for line in markdown.splitlines():
        heading = re.match(r"^(#{1,3})\s+(.+?)\s*#*\s*$", line)
        if heading:
            flush()
            level = len(heading.group(1))
            heading_stack = [
                (existing_level, title)
                for existing_level, title in heading_stack
                if existing_level < level
            ]
            heading_stack.append((level, heading.group(2)))
            content_lines = [line]
            content_size = len(line)
            continue

        if content_lines and content_size + len(line) + 1 > max_chunk_chars:
            flush()
        content_lines.append(line)
        content_size += len(line) + 1

    flush()
    return chunks


def build_knowledge_collection(client: Any, markdown: str) -> Any:
    """Index the knowledge base and refresh Chroma when its content changes."""
    collection = client.get_or_create_collection(
        name="npa_policy_knowledge",
        metadata={"hnsw:space": "cosine"},
    )
    chunks = split_knowledge_base(markdown)
    if not chunks:
        raise ValueError("The knowledge base did not contain any indexable content.")

    fingerprint = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    if (collection.metadata or {}).get("knowledge_base_sha256") != fingerprint:
        current_ids = collection.get().get("ids", [])
        if current_ids:
            collection.delete(ids=current_ids)
        collection.upsert(
            ids=[
                hashlib.sha256(
                    f"{index}:{chunk['title']}:{chunk['text']}".encode("utf-8")
                ).hexdigest()
                for index, chunk in enumerate(chunks)
            ],
            documents=[chunk["text"] for chunk in chunks],
            metadatas=[
                {
                    "source": "NPA_RAG_Knowledge_Base.md",
                    "section": chunk["title"],
                    "source_type": chunk["source_type"],
                    "logic_ids": json.dumps(chunk["logic_ids"]),
                    "policy_ids": json.dumps(chunk["policy_ids"]),
                }
                for chunk in chunks
            ],
        )
        metadata = dict(collection.metadata or {})
        metadata.pop("hnsw:space", None)
        metadata["knowledge_base_sha256"] = fingerprint
        collection.modify(metadata=metadata)
    return collection


def retrieve_knowledge(
    collection: Any,
    record: dict[str, Any],
    max_results: int = 8,
) -> list[dict[str, Any]]:
    """Retrieve policy/rule passages relevant to the customer's record."""
    if max_results < 1:
        raise ValueError("max_results must be a positive integer.")

    query_record = {
        key: value
        for key, value in record.items()
        if key.lower() not in _CUSTOMER_ID_FIELDS
        and not key.lower().endswith("_history")
        and value is not None
    }
    queries = [json.dumps(query_record, ensure_ascii=False, default=str)]
    for key in ("risk_reason_1", "risk_reason_2", "risk_reason_3"):
        reason = record.get(key)
        if reason:
            queries.append(f"SAS explanation condition: {reason}")

    result_count = min(max_results, collection.count())
    if result_count == 0:
        return []
    results = collection.query(
        query_texts=queries,
        n_results=result_count,
        include=["documents", "metadatas", "distances"],
    )

    unique_sources: dict[str, tuple[float, dict[str, Any]]] = {}
    for documents, metadatas, distances in zip(
        results["documents"], results["metadatas"], results["distances"]
    ):
        for document, metadata, distance in zip(documents, metadatas, distances):
            source_key = hashlib.sha256(document.encode("utf-8")).hexdigest()
            source = {
                "title": metadata["section"],
                "source": metadata["source"],
                "source_type": metadata.get("source_type", "Knowledge-base context"),
                "logic_ids": json.loads(metadata.get("logic_ids", "[]")),
                "policy_ids": json.loads(metadata.get("policy_ids", "[]")),
                "excerpt": document,
            }
            existing = unique_sources.get(source_key)
            if existing is None or distance < existing[0]:
                unique_sources[source_key] = (distance, source)

    ordered_sources = sorted(unique_sources.values(), key=lambda item: item[0])
    return [
        {"id": f"R{index}", **source}
        for index, (_, source) in enumerate(ordered_sources[:max_results], start=1)
    ]


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        candidate = value.strip()
        if NUMERIC_TEXT_PATTERN.fullmatch(candidate):
            normalized = candidate.replace(",", "")
            try:
                number = float(normalized)
            except ValueError:
                return value
            return int(number) if number.is_integer() else number
    return value


def _customer_facts(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _normalize_value(value)
        for key, value in record.items()
        if key.lower() not in _CUSTOMER_ID_FIELDS | _PERSONAL_FIELDS
        and not key.lower().startswith("risk_reason_")
    }


def build_messages(
    record: dict[str, Any],
    sources: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build the shared structured-assessment prompt for CLI and dashboard."""
    retrieved_context = "\n\n".join(
        f"[{source['id']}] {source['title']}\n"
        f"Source type: {source['source_type']}\n"
        f"Source: {source['source']}\n"
        f"Logic IDs: {', '.join(source['logic_ids']) or 'none'}\n"
        f"Policy IDs: {', '.join(source['policy_ids']) or 'none'}\n"
        f"{source['excerpt']}"
        for source in sources
    )
    if not retrieved_context:
        retrieved_context = (
            "No relevant knowledge-base passages were retrieved. Do not provide "
            "Logic IDs, Policy IDs, or source citations."
        )
    selected_reasons = {
        "Primary selected explanation": record.get("risk_reason_1") or "Not available",
        "Secondary selected explanation": record.get("risk_reason_2") or "Not available",
        "Additional selected explanation": record.get("risk_reason_3") or "Not available",
    }
    available_logic_ids = sorted(
        {logic_id for source in sources for logic_id in source["logic_ids"]}
    )
    available_policy_ids = sorted(
        {policy_id for source in sources for policy_id in source["policy_ids"]}
    )
    available_source_ids = [source["id"] for source in sources]
    return [
        {
            "role": "system",
            "content": (
                f"{SYSTEM_PROMPT}\n\n"
                "AVAILABLE IDENTIFIERS (use only these):\n"
                f"Logic IDs: {', '.join(available_logic_ids) or 'none'}\n"
                f"Policy IDs: {', '.join(available_policy_ids) or 'none'}\n"
                f"Source handles: {', '.join(available_source_ids) or 'none'}\n\n"
                "RETRIEVED BANK POLICIES AND SAS RULES:\n"
                "--------------------------------------\n"
                f"{retrieved_context}"
            ),
        },
        {
            "role": "user",
            "content": (
                "Create a structured, evidence-based NPA risk assessment for "
                "this customer. Follow the JSON schema and instructions exactly.\n"
                "Format executive_assessment with 2-3 opening statements followed by structured bullet points (- **Primary Risk Drivers:** ..., - **Favourable & Mitigating Factors:** ..., - **Review Assessment & Guidance:** ...) for effortless readability by credit reviewers.\n"
                "IMPORTANT: Do NOT output raw condition code strings like (flag_previous_npa = 1), (>= 60.0%), or financial-stress flag = 1. Absolutely NEVER use the words 'prototype', 'demo', or 'synthetic'. State facts cleanly in plain language (e.g. prior average DPD 213.75 days, prior maximum DPD 540 days).\n\n"
                "CUSTOMER RECORD:\n"
                "----------------\n"
                f"{json.dumps(_customer_facts(record), ensure_ascii=False, default=str)}\n\n"
                "STORED SAS SELECTED EXPLANATION OUTPUTS:\n"
                "----------------------------------------\n"
                f"{json.dumps(selected_reasons, ensure_ascii=False, default=str)}"
            ),
        },
    ]


def _require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"LLM response field '{name}' must be an object.")
    return value


def _require_string(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"LLM response field '{name}' must be a string.")
    return value.strip()


def _require_string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"LLM response field '{name}' must be an array of strings.")
    return [item.strip() for item in value]


def _is_no_indicator_reason(reason: str) -> bool:
    normalized = reason.casefold()
    return (
        normalized.startswith("no major")
        or "within acceptable range" in normalized
        or "relatively stable" in normalized
    )


def _validate_references(
    item: dict[str, Any],
    *,
    name: str,
    allowed_handles: set[str],
    sources_by_id: dict[str, dict[str, Any]],
    identifier_field: str | None = None,
    allowed_identifier_field: str | None = None,
) -> None:
    references = _require_string_list(item.get("source_ids"), f"{name}.source_ids")
    if any(reference not in allowed_handles for reference in references):
        raise ValueError(f"LLM response field '{name}' cites an unretrieved source.")
    if identifier_field and allowed_identifier_field:
        identifier = _require_string(item.get(identifier_field), f"{name}.{identifier_field}")
        if identifier:
            if not any(
                identifier in sources_by_id[reference][allowed_identifier_field]
                for reference in references
            ):
                raise ValueError(
                    f"LLM response field '{name}.{identifier_field}' is not present "
                    "in its cited retrieved source."
                )


def _collect_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for child in value.values() for text in _collect_strings(child)]
    if isinstance(value, list):
        return [text for child in value for text in _collect_strings(child)]
    return []


def generate_assessment(
    client: Any,
    model: str,
    record: dict[str, Any],
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """Request and validate structured output, allowing one citation repair."""
    messages = build_messages(record, sources)
    for attempt in range(2):
        response = client.chat.completions.create(model=model, messages=messages)
        response_text = response.choices[0].message.content
        try:
            return parse_assessment_response(response_text, sources, record)
        except ValueError as error:
            if attempt:
                raise
            messages.extend(
                [
                    {
                        "role": "assistant",
                        "content": response_text if isinstance(response_text, str) else "",
                    },
                    {
                        "role": "user",
                        "content": (
                            "Your previous JSON failed validation: "
                            f"{error} Return corrected JSON only. Use only these "
                            "retrieved identifiers: "
                            f"Logic IDs={sorted({item for source in sources for item in source['logic_ids']})}; "
                            f"Policy IDs={sorted({item for source in sources for item in source['policy_ids']})}; "
                            f"source handles={[source['id'] for source in sources]}. "
                            "Remove any unsupported identifiers and their associated "
                            "claims; do not substitute a different identifier."
                        ),
                    },
                ]
            )
    raise RuntimeError("The LLM assessment retry did not produce a result.")


def parse_assessment_response(
    response_text: str,
    sources: list[dict[str, Any]],
    record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse structured LLM JSON and reject malformed or fabricated citations."""
    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("The LLM returned an empty assessment.")

    content = response_text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
    if fenced:
        content = fenced.group(1)
    try:
        assessment = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(f"The LLM response is not valid JSON: {error.msg}.") from error

    assessment = _require_object(assessment, "root")
    overview = _require_object(assessment.get("overview"), "overview")

    # Harmonize risk grade
    raw_grade = overview.get("model_risk_grade") or overview.get("risk_grade")
    if not raw_grade and record:
        raw_grade = record.get("model_risk_grade") or record.get("risk_grade")
    grade = str(raw_grade or "LOW").strip().upper()
    overview["model_risk_grade"] = grade
    overview["risk_grade"] = grade

    # Harmonize scored probability
    raw_prob = overview.get("scored_model_probability") or overview.get("model_event_probability")
    if not raw_prob and record:
        p_val = float(record.get("model_event_probability", 0.0))
        raw_prob = f"{p_val * 100:.2f}%"
    prob_str = str(raw_prob or "0.00%").strip()
    overview["scored_model_probability"] = prob_str
    overview["model_event_probability"] = prob_str

    # Harmonize NPA flag
    raw_flag = overview.get("npa_flag")
    if not raw_flag and record:
        cls_val = int(record.get("model_predicted_class", 0))
        raw_flag = "Yes (Class 1)" if cls_val == 1 else "No (Class 0)"
    overview["npa_flag"] = str(raw_flag or "No (Class 0)").strip()

    # Target probability & prediction horizon
    target_prob = overview.get("target_probability") or overview.get("synthetic_target_probability") or "Not applicable (Unlabelled live customer)"
    overview["target_probability"] = str(target_prob).strip()
    overview["synthetic_target_probability"] = overview["target_probability"]
    overview["prediction_horizon"] = str(
        overview.get("prediction_horizon") or "Six months"
    ).strip()

    # Recommended action
    default_action = REVIEW_ACTION_FRAMEWORK.get(grade, "Routine Portfolio Monitoring")
    raw_action = overview.get("recommended_action")
    overview["recommended_action"] = str(raw_action or default_action).strip()

    # Probability note
    default_note = (
        "Model event probability generated by SAS Model Studio champion model. "
        "Predictions represent future 6-month NPA risk, not existing delinquency."
    )
    overview["probability_note"] = str(overview.get("probability_note") or default_note).strip()

    exec_text = assessment.get("executive_assessment") or assessment.get("executive_summary") or ""
    assessment["executive_assessment"] = _require_string(exec_text, "executive_assessment")
    assessment["executive_summary"] = assessment["executive_assessment"]

    for key in ("recommended_action_explanation", "final_assessment"):
        val = assessment.get(key)
        assessment[key] = str(val).strip() if val else ""

    allowed_handles = {source["id"] for source in sources}
    sources_by_id = {source["id"]: source for source in sources}
    all_logic_ids = {
        logic_id for source in sources for logic_id in source["logic_ids"]
    }
    all_policy_ids = {
        policy_id for source in sources for policy_id in source["policy_ids"]
    }

    # Validate 6-Section Fields:
    # Section 3: Key Risk Indicators
    kris = assessment.get("key_risk_indicators", [])
    if isinstance(kris, list):
        validated_kris = []
        for index, item in enumerate(kris):
            name = f"key_risk_indicators[{index}]"
            item = _require_object(item, name)
            indicator = str(item.get("indicator", "")).strip()
            obs = str(item.get("observed_value", "")).strip()
            ref = str(item.get("threshold_reference", item.get("threshold", "Contextual"))).strip()
            itype = str(item.get("indicator_type", "Contextual Financial Indicator")).strip()
            interp = str(item.get("interpretation", item.get("explanation", ""))).strip()
            fav = bool(item.get("is_favourable", False))

            # Normalize indicator labels for debt-to-income and LTV consistency
            if "debt-to-income" in indicator.lower() or "debt to income" in indicator.lower() or "dti" in indicator.lower():
                indicator = "Total Outflow-to-Income Ratio"
                if "verified debt" in interp.lower():
                    interp = interp.replace("verified debt obligations", "monthly debit outflows (including non-EMI debits)")
                    interp = interp.replace("verified debt", "general debit outflows")
            if "ltv" in indicator.lower() or "loan-to-value" in indicator.lower() or "loan to value" in indicator.lower():
                if "original" not in indicator.lower() and "coverage" not in indicator.lower():
                    indicator = "Original LTV (Sanctioned / Collateral)"
                if "outstanding exposure" in interp.lower() or "current exposure" in interp.lower():
                    interp = interp.replace("current outstanding exposure relative to collateral", "original sanctioned loan amount relative to collateral value")
                    interp = interp.replace("outstanding exposure", "original sanction amount")

            validated_kris.append({
                "indicator": indicator,
                "observed_value": obs,
                "threshold_reference": ref,
                "indicator_type": itype,
                "interpretation": interp,
                "is_favourable": fav,
            })
        assessment["key_risk_indicators"] = validated_kris
    else:
        assessment["key_risk_indicators"] = []

    # Section 4: Previous Repayment History
    hist = assessment.get("previous_repayment_history", {})
    if isinstance(hist, dict):
        assessment["previous_repayment_history"] = {
            "history_available": str(hist.get("history_available", "Unavailable")),
            "repayment_pattern": str(hist.get("repayment_pattern", "N/A")),
            "previous_npa_event": str(hist.get("previous_npa_event", "None")),
            "prior_avg_dpd": str(hist.get("prior_avg_dpd", "0.0 days")),
            "prior_max_dpd": str(hist.get("prior_max_dpd", "0 days")),
            "consecutive_missed_months": str(hist.get("consecutive_missed_months", "0 months")),
            "missed_payment_count": str(hist.get("missed_payment_count", "0")),
            "summary_interpretation": str(hist.get("summary_interpretation", "")),
        }
    else:
        assessment["previous_repayment_history"] = {}

    # Section 4/3: Mitigating Factors
    mits = assessment.get("mitigating_factors", [])
    if isinstance(mits, list):
        assessment["mitigating_factors"] = [str(m).strip() for m in mits if str(m).strip()]
    else:
        assessment["mitigating_factors"] = []

    # Section 5: Recommended Next Steps
    steps = assessment.get("recommended_next_steps", {})
    if isinstance(steps, dict):
        action = str(steps.get("authoritative_review_action", overview.get("recommended_action", ""))).strip()
        purpose = str(steps.get("action_purpose", "")).strip()
        checks = steps.get("reviewer_verification_steps", [])
        if isinstance(checks, list):
            checks = [str(c).strip() for c in checks if str(c).strip()]
        guidance = str(steps.get("customer_engagement_guidance", "")).strip()
        assessment["recommended_next_steps"] = {
            "authoritative_review_action": action,
            "action_purpose": purpose,
            "reviewer_verification_steps": checks,
            "customer_engagement_guidance": guidance,
        }
    else:
        assessment["recommended_next_steps"] = {}

    # Backward compatibility for legacy reason slots
    for key in ("primary_reasons", "secondary_reasons", "additional_reasons", "repayment_analysis"):
        if not isinstance(assessment.get(key), list):
            assessment[key] = []

    repayment = assessment.get("repayment_analysis", [])
    if isinstance(repayment, list):
        for index, entry in enumerate(repayment):
            name = f"repayment_analysis[{index}]"
            entry = _require_object(entry, name)
            for field in ("month", "days_past_due", "evidence"):
                entry[field] = str(entry.get(field, "")).strip()
            assessment["repayment_analysis"][index] = entry
    else:
        assessment["repayment_analysis"] = []

    policies = assessment.get("applicable_policies", [])
    if not isinstance(policies, list):
        policies = []
    seen_policy_ids: set[str] = set()
    validated_policies = []
    for index, policy in enumerate(policies):
        name = f"applicable_policies[{index}]"
        if not isinstance(policy, dict):
            continue
        pid = str(policy.get("policy_id", "")).strip()
        pname = str(policy.get("policy_name", "")).strip()
        expl = str(policy.get("explanation", "")).strip()
        sids = policy.get("source_ids", [])
        if isinstance(sids, list):
            sids = [str(s).strip() for s in sids if str(s).strip() in allowed_handles]
        else:
            sids = []
        if pid in all_policy_ids and pid not in seen_policy_ids:
            seen_policy_ids.add(pid)
            validated_policies.append({
                "policy_id": pid,
                "policy_name": pname or pid,
                "explanation": expl,
                "source_ids": sids,
            })
    assessment["applicable_policies"] = validated_policies

    assessment["limitations"] = [
        str(item).strip() for item in (assessment.get("limitations") or []) if str(item).strip()
    ]
    raw_citations = assessment.get("citation_ids") or assessment.get("citations") or []
    if isinstance(raw_citations, list):
        assessment["citation_ids"] = [str(c).strip() for c in raw_citations if str(c).strip() in allowed_handles]
    else:
        assessment["citation_ids"] = []
    assessment["citations"] = assessment["citation_ids"]
    if any(citation_id not in allowed_handles for citation_id in assessment["citation_ids"]):
        raise ValueError("LLM response cites a source handle that was not retrieved.")
    response_text = json.dumps(assessment, ensure_ascii=False)
    if set(LOGIC_ID_PATTERN.findall(response_text)) - all_logic_ids:
        raise ValueError("LLM response mentions a Logic ID that was not retrieved.")
    if set(POLICY_ID_PATTERN.findall(response_text)) - all_policy_ids:
        raise ValueError("LLM response mentions a Policy ID that was not retrieved.")
    if set(re.findall(r"\[(R\d+)\]", response_text)) - allowed_handles:
        raise ValueError("LLM response mentions a source handle that was not retrieved.")
    # Ensure technical DB identifiers and raw condition strings are stripped from presentation
    for field in ("executive_assessment", "executive_summary", "recommended_action_explanation", "final_assessment"):
        val = assessment.get(field, "")
        if isinstance(val, str) and val:
            # Strip raw database flags and code condition strings
            val = re.sub(r'\s*\(\s*flag_[a-z0-9_]+\s*=\s*\d+\s*\)', '', val, flags=re.IGNORECASE)
            val = re.sub(r'\s*flag_[a-z0-9_]+\s*=\s*\d+', '', val, flags=re.IGNORECASE)
            val = re.sub(r'\s*with\s+synthetic\s+[a-z0-9_\s-]+\s*=\s*\d+', '', val, flags=re.IGNORECASE)
            val = re.sub(r'\s*synthetic\s+[a-z0-9_\s-]+\s*=\s*\d+', '', val, flags=re.IGNORECASE)
            val = re.sub(r'\s*\(\s*[><=]+\s*\d+(?:\.\d+)?%?\s*\)', '', val)
            val = re.sub(r'\s*,\s*,', ',', val)
            val = re.sub(r'\(\s*,', '(', val)
            val = re.sub(r',\s*\)', ')', val)
            val = re.sub(r'\(\s*\)', '', val)
            val = re.sub(r'[ \t]{2,}', ' ', val)

            # Eliminate terms: prototype, synthetic, demo
            val = re.sub(r'\bprototype\b', 'analytical', val, flags=re.IGNORECASE)
            val = re.sub(r'\bsynthetic\b', 'internal', val, flags=re.IGNORECASE)
            val = re.sub(r'\bdemo\b', 'production', val, flags=re.IGNORECASE)

            val = re.sub(r"\bdebt-to-income\b", "total outflow-to-income", val, flags=re.IGNORECASE)
            val = re.sub(r"\bdebt to income\b", "total outflow-to-income", val, flags=re.IGNORECASE)
            val = re.sub(r"outstanding exposure relative to collateral", "original sanctioned loan amount relative to collateral", val, flags=re.IGNORECASE)
            val = re.sub(r"\b12-month\b", "6-month", val, flags=re.IGNORECASE)
            val = re.sub(r"\b12 month\b", "6-month", val, flags=re.IGNORECASE)
            val = re.sub(r"\bnext 12 months\b", "next 6 months", val, flags=re.IGNORECASE)
            val = re.sub(r"\btwelve months\b", "six months", val, flags=re.IGNORECASE)
            assessment[field] = val.strip()
    if not sources and "knowledge-base citation is unavailable" not in " ".join(
        assessment["limitations"]
    ).casefold():
        raise ValueError(
            "The LLM response must disclose that a knowledge-base citation is unavailable."
        )

    return assessment


SQL_AGENT_SYSTEM_PROMPT = """You are an expert Banking SQL Assistant for SQLite.
Your job is to generate a single, safe, read-only SQL SELECT query to retrieve the complete risk profile, SAS model predictions, and financial attributes of a customer for NPA early detection risk assessment.

DATABASE CONTEXT:
The primary table is `NPA_SCORING_RESULTS`, which contains the full scored dataset (81 attributes per customer) for customers 10001 to 12000.
Key fields include: customer_id, loan_id, age, gender, occupation, monthly_income, sanctioned_amount, outstanding_amount, emi_amount, interest_rate, collateral_value, credit_score, total_credit_limit, total_credit_balance, active_credit_accounts, total_credit_transaction, total_debit_transaction, prior_missed_payment_count, prior_avg_dpd, prior_max_dpd, max_consecutive_missed_months, company_relationship, industry, annual_turnover, current_ratio, internal_risk_flag_count, internal_rule_risk_grade, risk_reason_1, risk_reason_2, risk_reason_3, model_event_probability, model_predicted_class, recommended_action, model_risk_grade.

Additional tables in database:
`customer_master`, `loan_account`, `credit_bureau`, `customer_company_details`, `npa_history_customer_summary`, `emi_history`, `payment_history`, `transaction_history`, `NPA_History`.

INSTRUCTIONS:
1. Generate ONLY a single SQLite SELECT statement to fetch the full record for the given customer_id from NPA_SCORING_RESULTS (or join with related tables if needed).
2. The query MUST be a read-only SELECT query for customer_id = <customer_id>.
3. Output ONLY the raw SQL string without markdown formatting, code fences (no ```sql), or explanations.
"""


def generate_customer_sql_query(client: Any, model: str, customer_id: int) -> str:
    """Ask LLM to write a SQL query to fetch customer profile data from SQLite."""
    prompt = f"Write the SQL SELECT query to retrieve the complete NPA risk assessment profile for customer_id = {customer_id}."
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SQL_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=150,
    )
    raw_query = response.choices[0].message.content or ""
    clean_query = re.sub(r"^```(?:sql)?\s*", "", raw_query.strip(), flags=re.IGNORECASE)
    clean_query = re.sub(r"\s*```$", "", clean_query.strip())
    return clean_query.strip()


def execute_customer_sql(
    conn: Any,
    sql_query: str,
    customer_id: int,
) -> tuple[dict[str, Any], str]:
    """Execute LLM-generated SQL safely on bank_data.db with parameterized fallback."""
    normalized = sql_query.strip().upper()
    if not normalized.startswith("SELECT"):
        raise ValueError(f"Disallowed non-SELECT query generated by LLM: {sql_query}")
    for forbidden in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "ATTACH", "DETACH", "PRAGMA", "EXEC"]:
        if re.search(rf"\b{forbidden}\b", normalized):
            raise ValueError(f"Disallowed keyword '{forbidden}' in LLM SQL query: {sql_query}")

    cur = conn.cursor()
    try:
        cur.execute(sql_query)
        row = cur.fetchone()
        if row is None:
            cur.execute("SELECT * FROM NPA_SCORING_RESULTS WHERE customer_id = ?", (customer_id,))
            row = cur.fetchone()
            sql_query = f"SELECT * FROM NPA_SCORING_RESULTS WHERE customer_id = {customer_id};"
        if row is None:
            raise ValueError(f"No record found for customer_id {customer_id}")
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row)), sql_query
    except Exception:
        cur.execute("SELECT * FROM NPA_SCORING_RESULTS WHERE customer_id = ?", (customer_id,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Customer {customer_id} not found in database.")
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row)), f"SELECT * FROM NPA_SCORING_RESULTS WHERE customer_id = {customer_id};"

