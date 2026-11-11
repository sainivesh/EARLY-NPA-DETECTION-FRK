import sqlite3
import chromadb
import pandas as pd
import os
from clean_data import clean_database

db_name="bank_data.db"

if os.path.exists(db_name):
    os.remove(db_name)

conn=sqlite3.connect(db_name)
folder_path="raw_data"


for file_name in os.listdir(folder_path):
    if file_name.endswith("csv"):
        file_path=f"{folder_path}/{file_name}"
        df=pd.read_csv(file_path)

        table_name=file_name.replace(".csv","")
        print(f"Currently processing {file_name}...")
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"processed {file_name}...")

with conn:
    invalid_customers, deleted_rows = clean_database(conn)

print(f"removed {invalid_customers:,} invalid customers and {deleted_rows:,} rows")
print("created NPA_MASTER and NPA_MASTER_10K")
conn.close()
print("database created successfully")