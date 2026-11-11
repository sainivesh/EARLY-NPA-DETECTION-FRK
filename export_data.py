import argparse
import csv
import sqlite3
from pathlib import Path


def export_table(database: Path, table: str, output: Path) -> int:
    if not database.is_file():
        raise FileNotFoundError(f"Database not found: {database}")

    database_uri = f"file:{database.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(database_uri, uri=True) as conn:
        available_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if table not in available_tables:
            raise ValueError(f"Table {table!r} was not found in {database}.")

        escaped_table = '"' + table.replace('"', '""') + '"'
        cursor = conn.execute(f"SELECT * FROM {escaped_table}")
        output.parent.mkdir(parents=True, exist_ok=True)
        row_count = 0
        with output.open("w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(column[0] for column in cursor.description)
            while rows := cursor.fetchmany(1000):
                writer.writerows(rows)
                row_count += len(rows)

    return row_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export one SQLite table to a spreadsheet-friendly CSV file."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(__file__).with_name("bank_data.db"),
    )
    parser.add_argument(
        "--table",
        default="NPA_MASTER_10K",
        help="Table to export (default: NPA_MASTER_10K)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="CSV output path (default: <table>.csv beside this script)",
    )
    args = parser.parse_args()

    output = args.output or Path(__file__).with_name(f"{args.table}.csv")
    row_count = export_table(args.database, args.table, output)
    print(f"Exported {row_count:,} rows from {args.table} to {output}")


if __name__ == "__main__":
    main()
