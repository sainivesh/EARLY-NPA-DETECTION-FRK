import hashlib
import json
import re
from typing import Any


LOGIC_ID_PATTERN = re.compile(r"\bLOG-NPA-\d{3}\b")
POLICY_ID_PATTERN = re.compile(r"\bPOL-NPA-\d{3}\b")
NUMERIC_TEXT_PATTERN = re.compile(r"^-?\d[\d,]*(?:\.\d+)?$")

SYSTEM_PROMPT = """\
You are an AI-powered Banking NPA Risk Explanation Assistant.

Use the supplied customer record as the only source of customer-specific
facts. Use only retrieved knowledge-base passages for SAS rules, thresholds,
Logic IDs, Policy IDs, policy names, and policy context. Do not invent missing
facts or treat a database field as a knowledge-base citation.

Respect the ordered reason priority described by retrieved SAS rules. Report
only indicators supported by the customer's values and retrieved rules.
When stored risk_reason_1, risk_reason_2, and risk_reason_3 fields are present,
use them as the selected primary, secondary, and additional reason outputs,
respectively, after cross-checking each against its retrieved condition and
the actual value. Do not promote a later condition over an earlier selected
reason or list lower-priority alternatives as additional SAS triggers.
Translate technical fields into clear banking terminology. Do not expose raw
database variable names, customer IDs, loan IDs, or unnecessary personal
details. Do not claim that a payment was missed unless the supplied history
confirms it. Distinguish the dataset's NPA flag and synthetic probability from
a scored model probability and an actual regulatory NPA classification.
Only report a risk grade or recommended action when present in the record.
Describe proposed bank guidance as proposed, not as approved bank policy.

Return ONLY one valid JSON object matching this schema. Every displayed value
must be a string; use "Not available in the record" when a scalar is unknown.
Use empty strings and empty arrays for unsupported IDs/references. Do not
include Markdown fences or prose outside the JSON.

{
  "overview": {
    "npa_flag": "",
    "synthetic_target_probability": "",
    "scored_model_probability": "",
    "risk_grade": "",
    "recommended_action": "",
    "probability_note": ""
  },
  "executive_summary": "",
  "primary_reasons": [
    {
      "title": "",
      "observed_value": "",
      "threshold": "",
      "explanation": "",
      "logic_id": "",
      "policy_id": "",
      "selected_reason": "",
      "source_ids": ["R1"]
    }
  ],
  "secondary_reasons": [],
  "additional_reasons": [],
  "repayment_analysis": [
    {
      "month": "",
      "days_past_due": "",
      "evidence": ""
    }
  ],
  "applicable_policies": [
    {
      "policy_id": "",
      "policy_name": "",
      "explanation": "",
      "source_ids": ["R1"]
    }
  ],
  "recommended_action_explanation": "",
  "final_assessment": "",
  "limitations": [],
  "citation_ids": ["R1"]
}

For each factor, put the actual value and applicable threshold in their
respective fields, and explain why the factor matters. Cite the retrieved
source handle(s) in source_ids. A Logic ID or Policy ID is valid only when it
appears in one of those cited retrieved passages. Use no other Logic IDs,
Policy IDs, or source handles. citation_ids must contain retrieved source
handles only. Do not cite customer data as a knowledge-base source. List each
applicable policy only once.

Use the supplied selected SAS explanation outputs as the authoritative
ordered reason slots: primary_reasons matches the selected primary output,
secondary_reasons matches the selected secondary output, and additional_reasons
matches the selected additional output. Each non-empty slot must contain one
factor whose selected_reason exactly repeats that supplied explanation. If a
slot says there is no major indicator or that behaviour is stable, leave its
array empty. Do not add a different condition to an occupied slot.

Keep executive_summary to at most 75 words, each factor explanation to at
most 35 words, and final_assessment to at most 50 words. Avoid repeating the
same explanation across sections.

Repayment analysis must be based on the supplied monthly history. Use the
recorded month number and DPD; never infer a missed payment from DPD alone.
The field synthetic_target_probability may report npa_probability_actual.
The field scored_model_probability may report EM_EVENTPROBABILITY only; never
substitute npa_probability_actual for a scored model probability. If either is
absent, state that it is unavailable in the record. Explain their distinction
in probability_note. Do not infer the risk grade or recommended action.

If there are no retrieved sources, use empty citation/reference arrays,
explicitly state that a knowledge-base citation is unavailable in limitations,
and do not provide Logic or Policy IDs.
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
    if "proposed bank policy" in combined or "proposed operational" in combined:
        return "Proposed bank policy"
    if "sas prototype" in combined or LOGIC_ID_PATTERN.search(combined):
        return "SAS prototype rule"
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
            queries.append(f"Prototype SAS explanation condition: {reason}")

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
                "this customer. Follow the JSON schema and instructions exactly.\n\n"
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
    for key in (
        "npa_flag",
        "synthetic_target_probability",
        "scored_model_probability",
        "risk_grade",
        "recommended_action",
        "probability_note",
    ):
        overview[key] = _require_string(overview.get(key), f"overview.{key}")

    for key in (
        "executive_summary",
        "recommended_action_explanation",
        "final_assessment",
    ):
        assessment[key] = _require_string(assessment.get(key), key)

    allowed_handles = {source["id"] for source in sources}
    sources_by_id = {source["id"]: source for source in sources}
    all_logic_ids = {
        logic_id for source in sources for logic_id in source["logic_ids"]
    }
    all_policy_ids = {
        policy_id for source in sources for policy_id in source["policy_ids"]
    }

    reason_slots = (
        ("primary_reasons", "risk_reason_1"),
        ("secondary_reasons", "risk_reason_2"),
        ("additional_reasons", "risk_reason_3"),
    )
    for key, record_field in reason_slots:
        reasons = assessment.get(key)
        if not isinstance(reasons, list):
            raise ValueError(f"LLM response field '{key}' must be an array.")
        expected_reason = record.get(record_field) if record is not None else None
        if expected_reason:
            expected_reason = str(expected_reason).strip()
            if _is_no_indicator_reason(expected_reason):
                if reasons:
                    raise ValueError(f"LLM response adds an unsupported factor to '{key}'.")
            elif len(reasons) != 1:
                raise ValueError(
                    f"LLM response must include only the selected SAS reason in '{key}'."
                )
        for index, reason in enumerate(reasons):
            name = f"{key}[{index}]"
            reason = _require_object(reason, name)
            for field in (
                "title",
                "observed_value",
                "threshold",
                "explanation",
                "logic_id",
                "policy_id",
                "selected_reason",
            ):
                reason[field] = _require_string(reason.get(field), f"{name}.{field}")
            if expected_reason and reason["selected_reason"] != expected_reason:
                raise ValueError(
                    f"LLM response does not match the stored selected SAS reason in '{name}'."
                )
            if reason["logic_id"] and reason["logic_id"] not in all_logic_ids:
                raise ValueError(f"LLM response contains an unretrieved Logic ID in '{name}'.")
            if reason["policy_id"] and reason["policy_id"] not in all_policy_ids:
                raise ValueError(f"LLM response contains an unretrieved Policy ID in '{name}'.")
            _validate_references(
                reason,
                name=name,
                allowed_handles=allowed_handles,
                sources_by_id=sources_by_id,
                identifier_field="logic_id",
                allowed_identifier_field="logic_ids",
            )
            if reason["policy_id"] and not any(
                reason["policy_id"] in sources_by_id[reference]["policy_ids"]
                for reference in reason["source_ids"]
            ):
                raise ValueError(f"LLM response field '{name}' cites the wrong Policy ID.")
            reason.pop("selected_reason")
            assessment[key][index] = reason

    repayment = assessment.get("repayment_analysis")
    if not isinstance(repayment, list):
        raise ValueError("LLM response field 'repayment_analysis' must be an array.")
    for index, entry in enumerate(repayment):
        name = f"repayment_analysis[{index}]"
        entry = _require_object(entry, name)
        for field in ("month", "days_past_due", "evidence"):
            entry[field] = _require_string(entry.get(field), f"{name}.{field}")
        assessment["repayment_analysis"][index] = entry

    policies = assessment.get("applicable_policies")
    if not isinstance(policies, list):
        raise ValueError("LLM response field 'applicable_policies' must be an array.")
    seen_policy_ids: set[str] = set()
    for index, policy in enumerate(policies):
        name = f"applicable_policies[{index}]"
        policy = _require_object(policy, name)
        for field in ("policy_id", "policy_name", "explanation"):
            policy[field] = _require_string(policy.get(field), f"{name}.{field}")
        if policy["policy_id"] not in all_policy_ids:
            raise ValueError(f"LLM response contains an unretrieved Policy ID in '{name}'.")
        if policy["policy_id"] in seen_policy_ids:
            raise ValueError(f"LLM response repeats a Policy ID in '{name}'.")
        seen_policy_ids.add(policy["policy_id"])
        _validate_references(
            policy,
            name=name,
            allowed_handles=allowed_handles,
            sources_by_id=sources_by_id,
            identifier_field="policy_id",
            allowed_identifier_field="policy_ids",
        )
        assessment["applicable_policies"][index] = policy

    assessment["limitations"] = _require_string_list(
        assessment.get("limitations"), "limitations"
    )
    assessment["citation_ids"] = _require_string_list(
        assessment.get("citation_ids"), "citation_ids"
    )
    if any(citation_id not in allowed_handles for citation_id in assessment["citation_ids"]):
        raise ValueError("LLM response cites a source handle that was not retrieved.")
    response_text = json.dumps(assessment, ensure_ascii=False)
    if set(LOGIC_ID_PATTERN.findall(response_text)) - all_logic_ids:
        raise ValueError("LLM response mentions a Logic ID that was not retrieved.")
    if set(POLICY_ID_PATTERN.findall(response_text)) - all_policy_ids:
        raise ValueError("LLM response mentions a Policy ID that was not retrieved.")
    if set(re.findall(r"\[(R\d+)\]", response_text)) - allowed_handles:
        raise ValueError("LLM response mentions a source handle that was not retrieved.")
    if record:
        output_strings = _collect_strings(assessment)
        raw_fields = {
            key
            for key in record
            if "_" in key and key.lower() not in _CUSTOMER_ID_FIELDS
        }
        for field in raw_fields:
            if any(re.search(rf"(?<!\w){re.escape(field)}(?!\w)", text, re.IGNORECASE) for text in output_strings):
                raise ValueError("LLM response exposes a raw database field name.")
    if not sources and "knowledge-base citation is unavailable" not in " ".join(
        assessment["limitations"]
    ).casefold():
        raise ValueError(
            "The LLM response must disclose that a knowledge-base citation is unavailable."
        )

    return assessment
