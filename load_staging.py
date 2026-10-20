from urllib.parse import quote_plus
import pandas as pd
from sqlalchemy import create_engine

# Database Connection Settings
DB_SERVER = "localhost"  # Change to "localhost\\SQLEXPRESS" if using SQL Server Express
DB_NAME = "superstore_db"
DB_DRIVER = "ODBC Driver 17 for SQL Server"
DB_TRUSTED = True

driver_encoded = quote_plus(DB_DRIVER)
trusted_flag = "yes" if DB_TRUSTED else "no"

db_url = f"mssql+pyodbc://@{DB_SERVER}/{DB_NAME}?driver={driver_encoded}&trusted_connection={trusted_flag}"
engine = create_engine(db_url)

print("Reading raw Global Superstore CSV...")
# Adjust the path to where your raw CSV file is located
df_raw = pd.read_csv("data/Global_Superstore.csv", encoding="latin1")

print(f"Uploading {len(df_raw)} raw rows to SQL Server as 'staging_raw_sales'...")
df_raw.to_sql("staging_raw_sales", engine, if_exists="replace", index=False)

print("Staging table created successfully in SQL Server!")