import json
import os
import sqlite3
from pathlib import Path

import chromadb
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from npa_assessment import (
    build_knowledge_collection,
    generate_assessment,
    retrieve_knowledge,
)


ROOT = Path(__file__).resolve().parent
DATABASE_PATH = ROOT / "bank_data.db"
KNOWLEDGE_BASE_PATH = ROOT / "NPA_RAG_Knowledge_Base.md"


def main() -> None:
    load_dotenv(ROOT / ".env")
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")
    if not KNOWLEDGE_BASE_PATH.is_file():
        raise FileNotFoundError(f"Knowledge base not found: {KNOWLEDGE_BASE_PATH}")

    with sqlite3.connect(DATABASE_PATH) as conn:
        min_id, max_id = conn.execute(
            "SELECT MIN(sample_id), MAX(sample_id) FROM NPA_MASTER_10K"
        ).fetchone()
    if min_id is None or max_id is None:
        raise RuntimeError("The NPA_MASTER_10K customer sample is empty.")

    try:
        sample_id = int(input(f"Enter sample ID ({min_id}-{max_id}): "))
    except ValueError as error:
        raise SystemExit("Sample ID must be an integer.") from error

    with sqlite3.connect(DATABASE_PATH) as conn:
        customer_data = pd.read_sql_query(
            "SELECT * FROM NPA_MASTER_10K WHERE sample_id = ?",
            conn,
            params=(sample_id,),
        )
    if customer_data.empty:
        raise SystemExit(f"No customer found for sample ID {sample_id}.")

    record = json.loads(customer_data.to_json(orient="records"))[0]
    markdown = KNOWLEDGE_BASE_PATH.read_text(encoding="utf-8")
    collection = build_knowledge_collection(chromadb.Client(), markdown)
    sources = retrieve_knowledge(collection, record)

    api_key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set API_KEY or OPENAI_API_KEY in .env to generate summaries.")
    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("BASE_URL") or None,
    )
    assessment = generate_assessment(
        client,
        os.getenv("OPENAI_MODEL", "deepseek-v4.1-flash"),
        record,
        sources,
    )
    print("\n--- STRUCTURED NPA ASSESSMENT ---")
    print(json.dumps(assessment, indent=2, ensure_ascii=False))
    print("\n--- RETRIEVED SOURCES ---")
    for source in sources:
        print(f"[{source['id']}] {source['title']} ({source['source']})")


if __name__ == "__main__":
    main()
