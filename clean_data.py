import argparse
import math
import sqlite3
from pathlib import Path
from typing import Optional, Tuple

SAMPLE_SIZE = 10_000
QUALITY_PREDICATE = """
    customer_id BETWEEN 100001 AND 2000000
    AND age BETWEEN 21 AND 70
    AND employment_years BETWEEN 0 AND 25
    AND employment_years <= age - 18
    AND gender IN ('M', 'F')
    AND marital_status IN ('MARRIED', 'SINGLE')
    AND occupation IN ('SALARIED', 'BUSINESS', 'SELF_EMPLOYED', 'PROFESSIONAL')
    AND city_type IN ('METRO', 'URBAN', 'SEMI_URBAN', 'RURAL')
    AND CAST(REPLACE(monthly_income, ',', '') AS REAL) BETWEEN 15000 AND 200000
    AND loan_id = 5000001 + (customer_id - 100001)
    AND loan_type IN ('HOME', 'PERSONAL', 'AUTO', 'BUSINESS')
    AND CAST(REPLACE(sanctioned_amount, ',', '') AS REAL)
        BETWEEN 100000 AND 5000000
    AND CAST(REPLACE(outstanding_amount, ',', '') AS REAL)
        / CAST(REPLACE(sanctioned_amount, ',', '') AS REAL) BETWEEN 0.195 AND 0.955
    AND CAST(REPLACE(emi_amount, ',', '') AS REAL)
        BETWEEN CAST(REPLACE(outstanding_amount, ',', '') AS REAL) / 84 - 100
            AND CAST(REPLACE(outstanding_amount, ',', '') AS REAL) / 13 + 100
    AND interest_rate BETWEEN 7 AND 17
    AND CAST(REPLACE(collateral_value, ',', '') AS REAL)
        / CAST(REPLACE(sanctioned_amount, ',', '') AS REAL) BETWEEN 0.799 AND 2.301
    AND loan_age_months BETWEEN 3 AND 120
    AND remaining_tenure BETWEEN 6 AND 84
    AND avg_dpd BETWEEN 0 AND 120
    AND max_dpd BETWEEN avg_dpd AND 120
    AND dpd_30_count BETWEEN 0 AND 12
    AND dpd_60_count BETWEEN 0 AND dpd_30_count
    AND dpd_90_count BETWEEN 0 AND dpd_60_count
    AND historical_npa_count = dpd_90_count
    AND bounce_count BETWEEN 0 AND 12
    AND late_payment_count BETWEEN 0 AND 12
    AND avg_payment_delay BETWEEN 0 AND 60
    AND max_payment_delay BETWEEN avg_payment_delay AND 60
    AND credit_score BETWEEN 550 AND 850
    AND CAST(REPLACE(total_credit_limit, ',', '') AS REAL)
        BETWEEN 50000 AND 2000000
    AND CAST(REPLACE(total_credit_balance, ',', '') AS REAL)
        BETWEEN 0 AND CAST(REPLACE(total_credit_limit, ',', '') AS REAL)
    AND active_credit_accounts BETWEEN 1 AND 12
    AND overdue_accounts BETWEEN 0 AND 5
    AND bureau_dpd BETWEEN 0 AND 120
    AND recent_enquiries BETWEEN 0 AND 10
    AND writeoff_accounts BETWEEN 0 AND 2
    AND total_payment_amount BETWEEN 12000 AND 612000
    AND avg_transaction_count BETWEEN 5 AND 150
    AND total_credit_transaction BETWEEN 0 AND 1200000
    AND total_debit_transaction BETWEEN 0 AND 1200000
    AND total_cash_withdrawal BETWEEN 0 AND 600000
    AND ABS(
        outstanding_ratio
        - CAST(REPLACE(outstanding_amount, ',', '') AS REAL)
            / CAST(REPLACE(sanctioned_amount, ',', '') AS REAL)
    ) < 0.002
    AND ABS(
        credit_utilization
        - CAST(REPLACE(total_credit_balance, ',', '') AS REAL)
            / CAST(REPLACE(total_credit_limit, ',', '') AS REAL)
    ) < 0.002
    AND ABS(
        loan_to_value
        - CAST(REPLACE(sanctioned_amount, ',', '') AS REAL)
            / CAST(REPLACE(collateral_value, ',', '') AS REAL)
    ) < 0.002
    AND ABS(
        emi_income_ratio
        - CAST(REPLACE(emi_amount, ',', '') AS REAL) / monthly_income_final
    ) < 0.002
    AND monthly_income_final = CAST(REPLACE(monthly_income, ',', '') AS INTEGER)
    AND credit_risk_score BETWEEN 0 AND 1
    AND npa_probability_actual BETWEEN 0 AND 1
    AND npa_flag IN (0, 1)
"""


def _number(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _add_monthly_histories(conn: sqlite3.Connection) -> None:
    history_specs = (
        (
            "EMI_HISTORY_DQ",
            "emi_history",
            "month_no",
            (
                ("month_no", "month_no"),
                ("emi_due", "CAST(REPLACE(emi_due, ',', '') AS REAL)"),
                ("emi_paid", "CAST(REPLACE(emi_paid, ',', '') AS REAL)"),
                ("days_past_due", "days_past_due"),
                ("npa_indicator", "npa_indicator"),
            ),
        ),
        (
            "PAYMENT_HISTORY_DQ",
            "payment_history",
            "payment_month",
            (
                ("payment_month", "payment_month"),
                (
                    "payment_amount",
                    "CAST(REPLACE(payment_amount, ',', '') AS REAL)",
                ),
                ("payment_delay", "payment_delay"),
                ("bounce_flag", "bounce_flag"),
                ("late_payment_flag", "late_payment_flag"),
            ),
        ),
        (
            "TRANSACTION_HISTORY",
            "transaction_history",
            "transaction_month",
            (
                ("transaction_month", "transaction_month"),
                (
                    "credit_transaction",
                    "CAST(REPLACE(credit_transaction, ',', '') AS REAL)",
                ),
                (
                    "debit_transaction",
                    "CAST(REPLACE(debit_transaction, ',', '') AS REAL)",
                ),
                ("transaction_count", "transaction_count"),
                (
                    "cash_withdrawal",
                    "CAST(REPLACE(cash_withdrawal, ',', '') AS REAL)",
                ),
            ),
        ),
    )
    for table, column, month_field, fields in history_specs:
        temp_table = f"_sample_{column}"
        conn.execute(f"DROP TABLE IF EXISTS {_quote_identifier(temp_table)}")
        json_fields = ", ".join(
            f"'{key}', {expression}" for key, expression in fields
        )
        conn.execute(
            f"""
            CREATE TEMP TABLE {_quote_identifier(temp_table)} AS
            SELECT customer_id, json_group_array(json(record)) AS history_json
            FROM (
                SELECT customer_id, json_object({json_fields}) AS record
                FROM {_quote_identifier(table)}
                WHERE customer_id IN (
                    SELECT customer_id FROM NPA_MASTER_10K
                )
                ORDER BY customer_id, {_quote_identifier(month_field)}
            )
            GROUP BY customer_id
            """
        )
        conn.execute(
            f"CREATE UNIQUE INDEX {_quote_identifier(temp_table + '_id')} "
            f"ON {_quote_identifier(temp_table)}(customer_id)"
        )
        conn.execute(
            f"ALTER TABLE NPA_MASTER_10K "
            f"ADD COLUMN {_quote_identifier(column)} TEXT"
        )
        conn.execute(
            f"""
            UPDATE NPA_MASTER_10K
            SET {_quote_identifier(column)} = (
                SELECT history_json
                FROM {_quote_identifier(temp_table)}
                WHERE {_quote_identifier(temp_table)}.customer_id
                    = NPA_MASTER_10K.customer_id
            )
            """
        )
        conn.execute(f"DROP TABLE {_quote_identifier(temp_table)}")


def build_quality_sample(conn: sqlite3.Connection) -> int:
    """Create a stable sample containing only generation-rule-consistent rows."""
    conn.execute("DROP TABLE IF EXISTS NPA_MASTER_10K")
    conn.execute(
        f"""
        CREATE TABLE NPA_MASTER_10K AS
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY ((sampled.customer_id * 2654435761 + 1013904223)
                          % 2147483647),
                         sampled.customer_id
            ) AS sample_id,
            CASE
                WHEN sampled.npa_flag = 1 THEN ROW_NUMBER() OVER (
                    PARTITION BY sampled.npa_flag ORDER BY sampled.customer_id
                )
                ELSE NULL
            END AS NPA_ID,
            sampled.*
        FROM (
            SELECT *
            FROM NPA_MASTER
            WHERE {QUALITY_PREDICATE}
            ORDER BY ((customer_id * 2654435761 + 1013904223) % 2147483647),
                     customer_id
            LIMIT {SAMPLE_SIZE}
        ) AS sampled
        """
    )
    sample_count = conn.execute(
        "SELECT COUNT(*) FROM NPA_MASTER_10K"
    ).fetchone()[0]
    if sample_count != SAMPLE_SIZE:
        raise RuntimeError(
            f"Expected {SAMPLE_SIZE:,} quality-checked customers, "
            f"but found {sample_count:,}."
        )
    conn.execute(
        "CREATE UNIQUE INDEX idx_npa_master_10k_sample_id "
        "ON NPA_MASTER_10K(sample_id)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX idx_npa_master_10k_customer_id "
        "ON NPA_MASTER_10K(customer_id)"
    )
    flagged_count, assigned_count, distinct_npa_ids, first_npa_id, last_npa_id = (
        conn.execute(
            """
            SELECT SUM(npa_flag = 1), SUM(NPA_ID IS NOT NULL),
                   COUNT(DISTINCT NPA_ID), MIN(NPA_ID), MAX(NPA_ID)
            FROM NPA_MASTER_10K
            """
        ).fetchone()
    )
    invalid_npa_id_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM NPA_MASTER_10K
        WHERE (npa_flag = 1 AND NPA_ID IS NULL)
           OR (npa_flag != 1 AND NPA_ID IS NOT NULL)
        """
    ).fetchone()[0]
    if (
        invalid_npa_id_count
        or flagged_count != assigned_count
        or flagged_count != distinct_npa_ids
        or first_npa_id != 1
        or last_npa_id != flagged_count
    ):
        conn.execute("DROP TABLE NPA_MASTER_10K")
        raise RuntimeError(
            "NPA_ID values must be sequential and assigned only to flagged customers."
        )
    history_checks = (
        (
            "EMI_HISTORY_DQ",
            """
            WITH history AS (
                SELECT customer_id, COUNT(*) AS row_count,
                       COUNT(DISTINCT month_no) AS month_count,
                       MIN(month_no) AS first_month, MAX(month_no) AS last_month,
                       AVG(days_past_due) AS avg_dpd,
                       MAX(days_past_due) AS max_dpd,
                       SUM(days_past_due > 30) AS dpd_30_count,
                       SUM(days_past_due > 60) AS dpd_60_count,
                       SUM(days_past_due > 90) AS dpd_90_count,
                       SUM(npa_indicator) AS historical_npa_count,
                       SUM(CASE WHEN
                           emi_due IS NULL OR emi_paid IS NULL
                           OR days_past_due IS NULL OR npa_indicator IS NULL
                           OR CAST(REPLACE(emi_due, ',', '') AS REAL)
                               NOT BETWEEN 1000 AND 51000
                           OR CAST(REPLACE(emi_paid, ',', '') AS REAL)
                               < CAST(REPLACE(emi_due, ',', '') AS REAL) * 0.75 - 0.01
                           OR CAST(REPLACE(emi_paid, ',', '') AS REAL)
                               > CAST(REPLACE(emi_due, ',', '') AS REAL) * 1.05 + 0.01
                           OR days_past_due NOT BETWEEN 0 AND 120
                           OR npa_indicator != (days_past_due > 90)
                           THEN 1 ELSE 0 END) AS invalid_rows
                FROM EMI_HISTORY_DQ
                WHERE customer_id IN (SELECT customer_id FROM NPA_MASTER_10K)
                GROUP BY customer_id
            )
            SELECT COUNT(*)
            FROM NPA_MASTER_10K AS sample
            LEFT JOIN history USING (customer_id)
            WHERE history.customer_id IS NULL
               OR history.row_count != 12 OR history.month_count != 12
               OR history.first_month != 1 OR history.last_month != 12
               OR history.invalid_rows != 0
               OR ABS(history.avg_dpd - sample.avg_dpd) > 0.000001
               OR history.max_dpd != sample.max_dpd
               OR history.dpd_30_count != sample.dpd_30_count
               OR history.dpd_60_count != sample.dpd_60_count
               OR history.dpd_90_count != sample.dpd_90_count
               OR history.historical_npa_count != sample.historical_npa_count
            """,
        ),
        (
            "PAYMENT_HISTORY_DQ",
            """
            WITH history AS (
                SELECT customer_id, COUNT(*) AS row_count,
                       COUNT(DISTINCT payment_month) AS month_count,
                       MIN(payment_month) AS first_month,
                       MAX(payment_month) AS last_month,
                       SUM(bounce_flag) AS bounce_count,
                       SUM(late_payment_flag) AS late_payment_count,
                       AVG(payment_delay) AS avg_payment_delay,
                       MAX(payment_delay) AS max_payment_delay,
                       SUM(CAST(REPLACE(payment_amount, ',', '') AS REAL))
                           AS total_payment_amount,
                       SUM(CASE WHEN
                           payment_amount IS NULL OR payment_delay IS NULL
                           OR bounce_flag IS NULL OR late_payment_flag IS NULL
                           OR CAST(REPLACE(payment_amount, ',', '') AS REAL)
                               NOT BETWEEN 1000 AND 51000
                           OR payment_delay NOT BETWEEN 0 AND 60
                           OR bounce_flag NOT IN (0, 1)
                           OR late_payment_flag != (payment_delay > 30)
                           THEN 1 ELSE 0 END) AS invalid_rows
                FROM PAYMENT_HISTORY_DQ
                WHERE customer_id IN (SELECT customer_id FROM NPA_MASTER_10K)
                GROUP BY customer_id
            )
            SELECT COUNT(*)
            FROM NPA_MASTER_10K AS sample
            LEFT JOIN history USING (customer_id)
            WHERE history.customer_id IS NULL
               OR history.row_count != 12 OR history.month_count != 12
               OR history.first_month != 1 OR history.last_month != 12
               OR history.invalid_rows != 0
               OR history.bounce_count != sample.bounce_count
               OR history.late_payment_count != sample.late_payment_count
               OR ABS(history.avg_payment_delay - sample.avg_payment_delay)
                    > 0.000001
               OR history.max_payment_delay != sample.max_payment_delay
               OR history.total_payment_amount != sample.total_payment_amount
            """,
        ),
        (
            "TRANSACTION_HISTORY",
            """
            WITH history AS (
                SELECT customer_id, COUNT(*) AS row_count,
                       COUNT(DISTINCT transaction_month) AS month_count,
                       MIN(transaction_month) AS first_month,
                       MAX(transaction_month) AS last_month,
                       SUM(CAST(REPLACE(credit_transaction, ',', '') AS REAL))
                           AS total_credit_transaction,
                       SUM(CAST(REPLACE(debit_transaction, ',', '') AS REAL))
                           AS total_debit_transaction,
                       AVG(transaction_count) AS avg_transaction_count,
                       SUM(CAST(REPLACE(cash_withdrawal, ',', '') AS REAL))
                           AS total_cash_withdrawal,
                       SUM(CASE WHEN
                           credit_transaction IS NULL OR debit_transaction IS NULL
                           OR transaction_count IS NULL OR cash_withdrawal IS NULL
                           OR CAST(REPLACE(credit_transaction, ',', '') AS REAL)
                               NOT BETWEEN 0 AND 100000
                           OR CAST(REPLACE(debit_transaction, ',', '') AS REAL)
                               NOT BETWEEN 0 AND 100000
                           OR transaction_count NOT BETWEEN 5 AND 150
                           OR CAST(REPLACE(cash_withdrawal, ',', '') AS REAL)
                               NOT BETWEEN 0 AND 50000
                           THEN 1 ELSE 0 END) AS invalid_rows
                FROM TRANSACTION_HISTORY
                WHERE customer_id IN (SELECT customer_id FROM NPA_MASTER_10K)
                GROUP BY customer_id
            )
            SELECT COUNT(*)
            FROM NPA_MASTER_10K AS sample
            LEFT JOIN history USING (customer_id)
            WHERE history.customer_id IS NULL
               OR history.row_count != 12 OR history.month_count != 12
               OR history.first_month != 1 OR history.last_month != 12
               OR history.invalid_rows != 0
               OR history.total_credit_transaction
                    != sample.total_credit_transaction
               OR history.total_debit_transaction
                    != sample.total_debit_transaction
               OR ABS(history.avg_transaction_count - sample.avg_transaction_count)
                    > 0.000001
               OR history.total_cash_withdrawal != sample.total_cash_withdrawal
            """,
        ),
    )
    for table, query in history_checks:
        mismatches = conn.execute(query).fetchone()[0]
        if mismatches:
            conn.execute("DROP TABLE NPA_MASTER_10K")
            raise RuntimeError(
                f"{mismatches:,} sample customers have invalid or inconsistent "
                f"{table} history."
            )
    _add_monthly_histories(conn)
    return sample_count


def clean_database(conn: sqlite3.Connection) -> Tuple[int, int]:
    """Clean customer-linked tables and build a validated 10,000-row LLM master."""
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    table_names = [row[0] for row in tables]
    if "CUSTOMER_MASTER_DQ" not in table_names:
        raise RuntimeError("Required table CUSTOMER_MASTER_DQ was not found.")
    if "NPA_FEATURES" not in table_names:
        raise RuntimeError("Required table NPA_FEATURES was not found.")

    conn.execute("DROP TABLE IF EXISTS NPA_MASTER_10K")
    conn.execute("DROP TABLE IF EXISTS NPA_MASTER")
    conn.execute(
        "CREATE TEMP TABLE invalid_customer_ids (customer_id INTEGER PRIMARY KEY)"
    )

    invalid_ids = []
    for customer_id, age_value, experience_value in conn.execute(
        "SELECT customer_id, age, employment_years FROM CUSTOMER_MASTER_DQ"
    ):
        age = _number(age_value)
        experience = _number(experience_value)
        if (
            age is None
            or experience is None
            or not age.is_integer()
            or age < 21
            or age > 70
            or experience < 0
            or experience > 25
            or experience > age - 18
        ):
            invalid_ids.append((customer_id,))

    conn.executemany(
        "INSERT INTO invalid_customer_ids (customer_id) VALUES (?)",
        invalid_ids,
    )
    print(f"Found {len(invalid_ids):,} invalid customers.", flush=True)

    deleted_rows = 0
    for table in table_names:
        if table == "NPA_MASTER":
            continue
        columns = {
            row[1].lower()
            for row in conn.execute(
                f"PRAGMA table_info({_quote_identifier(table)})"
            )
        }
        if "customer_id" not in columns:
            continue
        print(f"Cleaning {table}...", flush=True)
        cursor = conn.execute(
            f"""
            DELETE FROM {_quote_identifier(table)}
            WHERE customer_id IN (
                SELECT customer_id FROM invalid_customer_ids
            )
            """
        )
        deleted_rows += max(cursor.rowcount, 0)

    conn.execute(
        """
        CREATE TABLE NPA_MASTER AS
        SELECT
            f.*,
            CASE
                WHEN f.avg_dpd > 60 THEN 'High average Days Past Due.'
                WHEN f.credit_utilization > 0.80 THEN 'High credit utilization.'
                WHEN f.debt_to_income > 0.50 THEN 'High debt-to-income ratio.'
                WHEN f.bounce_count >= 3 THEN 'Multiple payment bounces.'
                WHEN f.credit_score < 650 THEN 'Low credit bureau score.'
                ELSE 'No major primary risk indicator.'
            END AS risk_reason_1,
            CASE
                WHEN f.max_dpd > 90
                    THEN 'Customer has severe historical delinquency.'
                WHEN f.overdue_accounts >= 3
                    THEN 'Multiple overdue credit accounts.'
                WHEN f.recent_enquiries >= 6
                    THEN 'High recent credit enquiries.'
                ELSE 'Secondary risk indicators within acceptable range.'
            END AS risk_reason_2,
            CASE
                WHEN f.payment_trend > 5
                    THEN 'Negative payment trend observed.'
                WHEN f.outstanding_ratio > 0.80
                    THEN 'High outstanding loan ratio.'
                ELSE 'Payment behaviour is relatively stable.'
            END AS risk_reason_3
        FROM NPA_FEATURES AS f
        """
    )
    conn.execute(
        "CREATE UNIQUE INDEX idx_npa_master_customer_id "
        "ON NPA_MASTER(customer_id)"
    )
    build_quality_sample(conn)
    conn.execute("DROP TABLE invalid_customer_ids")

    return len(invalid_ids), deleted_rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove invalid customer records and build the NPA master table."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(__file__).with_name("bank_data.db"),
        help="SQLite database to clean (default: bank_data.db beside this script)",
    )
    parser.add_argument(
        "--sample-only",
        action="store_true",
        help="Rebuild NPA_MASTER_10K from an already-cleaned NPA_MASTER",
    )
    args = parser.parse_args()
    if not args.database.is_file():
        raise FileNotFoundError(f"Database not found: {args.database}")

    with sqlite3.connect(args.database) as conn:
        if args.sample_only:
            sample_count = build_quality_sample(conn)
            print(f"Created NPA_MASTER_10K with {sample_count:,} customers.")
            return
        invalid_customers, deleted_rows = clean_database(conn)

    print(f"Invalid customers removed: {invalid_customers:,}")
    print(f"Customer-linked rows removed: {deleted_rows:,}")
    print(
        f"Created NPA_MASTER_10K with {SAMPLE_SIZE:,} "
        "quality-checked customers."
    )


if __name__ == "__main__":
    main()
