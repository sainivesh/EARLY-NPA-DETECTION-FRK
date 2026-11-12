import os
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "bank_data.db"
SCORING_CSV = ROOT / "NPA_DATA_PIPELINE" / "07_SCORED_OUTPUT" / "NPA_SCORING_RESULTS.csv"
PIPELINE_SQLITE = ROOT / "NPA_DATA_PIPELINE" / "04_SQL_DATABASE" / "npa_project.sqlite"


def setup_bank_database() -> None:
    print(f"Setting up {DB_PATH.name} for 2,000 scored customers...")
    if not SCORING_CSV.is_file():
        raise FileNotFoundError(f"Scoring CSV not found: {SCORING_CSV}")
    if not PIPELINE_SQLITE.is_file():
        raise FileNotFoundError(f"Pipeline SQLite not found: {PIPELINE_SQLITE}")

    if DB_PATH.exists():
        try:
            os.remove(DB_PATH)
        except OSError:
            pass

    conn = sqlite3.connect(DB_PATH)

    # 1. Load 2,000 scored customers
    df_scoring = pd.read_csv(SCORING_CSV)
    df_scoring.to_sql("NPA_SCORING_RESULTS", conn, if_exists="replace", index=False)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_scoring_cust_id ON NPA_SCORING_RESULTS(customer_id)")

    # 2. Backward compatibility tables NPA_MASTER_10K and NPA_MASTER
    df_master = df_scoring.copy()
    df_master["sample_id"] = range(1, len(df_master) + 1)
    df_master["npa_flag"] = df_master["model_predicted_class"].astype(int)
    df_master["NPA_ID"] = df_master.apply(
        lambda r: f"NPA_{int(r['customer_id'])}" if int(r["npa_flag"]) == 1 else None,
        axis=1,
    )
    df_master.to_sql("NPA_MASTER_10K", conn, if_exists="replace", index=False)
    df_master.to_sql("NPA_MASTER", conn, if_exists="replace", index=False)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_master_10k_sample_id ON NPA_MASTER_10K(sample_id)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_master_10k_cust_id ON NPA_MASTER_10K(customer_id)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_master_cust_id ON NPA_MASTER(customer_id)")

    # 3. Relational tables filtered to the 2,000 customers
    conn_pipe = sqlite3.connect(PIPELINE_SQLITE)
    min_cid = int(df_scoring["customer_id"].min())
    max_cid = int(df_scoring["customer_id"].max())

    tables_to_copy = [
        "customer_master",
        "loan_account",
        "credit_bureau",
        "customer_company_details",
        "npa_history_customer_summary",
        "emi_history",
        "payment_history",
        "transaction_history",
        "NPA_History",
        "NPA_CUSTOMER_SPLIT",
    ]

    for t in tables_to_copy:
        query = f"SELECT * FROM {t} WHERE customer_id BETWEEN {min_cid} AND {max_cid}"
        df_t = pd.read_sql_query(query, conn_pipe)
        df_t.to_sql(t, conn, if_exists="replace", index=False)
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{t}_cust_id ON {t}(customer_id)")

    conn_pipe.close()
    conn.commit()
    conn.close()
    print("Database created successfully with 2,000 customers and full relational tables.")


if __name__ == "__main__":
    setup_bank_database()
