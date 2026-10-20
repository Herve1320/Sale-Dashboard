import os
from urllib.parse import quote_plus
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

# ==================================================
# 1. DATABASE CONNECTION & SQL INGESTION
# ==================================================
DB_SERVER = "localhost"  # Change to "localhost\\SQLEXPRESS" if using SQL Server Express
DB_NAME = "superstore_db"
DB_DRIVER = "ODBC Driver 17 for SQL Server"
DB_TRUSTED = True

driver_encoded = quote_plus(DB_DRIVER)
trusted_flag = "yes" if DB_TRUSTED else "no"

db_url = f"mssql+pyodbc://@{DB_SERVER}/{DB_NAME}?driver={driver_encoded}&trusted_connection={trusted_flag}"
engine = create_engine(db_url)

print(f"Connecting to MS SQL Server: '{DB_NAME}'...")

try:
  query = "SELECT * FROM staging_raw_sales;"
  df = pd.read_sql(query, engine)
  print(
      f"Successfully loaded {len(df)} raw records from 'staging_raw_sales'."
  )
except Exception as e:
  print(
      f"Error loading table from SQL Server: {e}\nMake sure 'staging_raw_sales'"
      " exists in your database."
  )
  exit()

# ==================================================
# 2. DEFENSIVE COLUMN STANDARDIZATION & MAPPING
# ==================================================
df.columns = (
    df.columns.str.strip().str.replace(" ", "_").str.replace("-", "_")
)


def find_col(df, candidates, default=None):
  for c in candidates:
    if c in df.columns:
      return c
  return default


col_map = {
    "Row_ID": find_col(df, ["Row_ID", "Row_Id", "row_id"]),
    "Order_ID": find_col(df, ["Order_ID", "Order_Id", "order_id"]),
    "Order_Date": find_col(df, ["Order_Date", "Order_date", "order_date"]),
    "Ship_Date": find_col(df, ["Ship_Date", "Ship_date", "ship_date"]),
    "Ship_Mode": find_col(df, ["Ship_Mode", "Ship_mode", "ship_mode"]),
    "Customer_ID": find_col(df, ["Customer_ID", "Customer_Id", "customer_id"]),
    "Customer_Name": find_col(
        df, ["Customer_Name", "Customer_name", "customer_name", "Customer"]
    ),
    "Segment": find_col(df, ["Segment", "segment"]),
    "Product_ID": find_col(df, ["Product_ID", "Product_Id", "product_id"]),
    "Product_Name": find_col(
        df, ["Product_Name", "Product_name", "product_name", "Product"]
    ),
    "Category": find_col(df, ["Category", "category"]),
    "Sub_Category": find_col(
        df, ["Sub_Category", "Sub_category", "sub_category"]
    ),
    "Sales": find_col(df, ["Sales", "sales"]),
    "Quantity": find_col(df, ["Quantity", "quantity"]),
    "Discount": find_col(df, ["Discount", "discount"]),
    "Profit": find_col(df, ["Profit", "profit"]),
    "Shipping_Cost": find_col(
        df, ["Shipping_Cost", "Shipping_cost", "shipping_cost", "ShippingCost"]
    ),
    "Order_Priority": find_col(
        df, ["Order_Priority", "Order_priority", "order_priority", "Priority"]
    ),
    "Country": find_col(df, ["Country", "country"]),
    "City": find_col(df, ["City", "city"]),
    "State": find_col(df, ["State", "state"]),
    "Postal_Code": find_col(
        df, ["Postal_Code", "Postal_code", "postal_code", "Postal"]
    ),
    "Region": find_col(df, ["Region", "region"]),
    "Market": find_col(df, ["Market", "market"]),
}

for drop_col in ["ji_lu_shu", "Unnamed:_0"]:
  if drop_col in df.columns:
    df.drop(columns=[drop_col], inplace=True)
    print(f"Dropped redundant column: {drop_col}")

# ==================================================
# 3. DATA CLEANING & TEXT FORMATTING
# ==================================================
initial_count = len(df)
df = df.drop_duplicates()
print(f"Dropped {initial_count - len(df)} duplicate rows.")

text_cols = df.select_dtypes(include=["object"]).columns
for col in text_cols:
  df[col] = df[col].astype(str).str.strip().replace("nan", np.nan)
print("Text cleaning and whitespace stripping complete.")

# ==================================================
# 4. ROBUST TYPE CONVERSIONS
# ==================================================
for date_col in ["Order_Date", "Ship_Date"]:
  mapped = col_map[date_col]
  if mapped and mapped in df.columns:
    df[date_col] = pd.to_datetime(df[mapped], errors="coerce")
    print(f"Converted '{mapped}' to datetime as '{date_col}'.")

numeric_cols = ["Sales", "Quantity", "Discount", "Profit", "Shipping_Cost"]
for num_col in numeric_cols:
  mapped = col_map[num_col]
  if mapped and mapped in df.columns:
    if df[mapped].dtype == "object":
      df[mapped] = (
          df[mapped]
          .astype(str)
          .str.replace("$", "", regex=False)
          .str.replace(",", "", regex=False)
      )
    df[num_col] = pd.to_numeric(df[mapped], errors="coerce")
    print(f"Converted '{mapped}' to numeric as '{num_col}'.")
  else:
    df[num_col] = 0.0
    print(
        f"Warning: Numeric column '{num_col}' missing from source. Initialized"
        " with 0.0."
    )

# ==================================================
# 5. BUSINESS LOGIC & MISSING VALUE VALIDATION
# ==================================================
df.fillna(
    {
        "Sales": 0.0,
        "Quantity": 0,
        "Discount": 0.0,
        "Profit": 0.0,
        "Shipping_Cost": 0.0,
    },
    inplace=True,
)

if "Order_Date" in df.columns and "Ship_Date" in df.columns:
  before_drop = len(df)
  df.dropna(subset=["Order_Date", "Ship_Date"], inplace=True)
  print(
      f"Dropped {before_drop - len(df)} rows with missing Order or Ship Dates."
  )

  invalid_dates_count = (df["Ship_Date"] < df["Order_Date"]).sum()
  if invalid_dates_count > 0:
    df = df[df["Ship_Date"] >= df["Order_Date"]]
    print(
        f"Filtered out {invalid_dates_count} rows where Ship Date < Order Date."
    )

if "Discount" in df.columns and df["Discount"].max() > 1.0:
  df["Discount"] = df["Discount"] / 100.0
  print("Normalized 'Discount' values from percentage to decimal format (0-1).")

# ==================================================
# 6. FEATURE ENGINEERING & SAFEGUARDS FOR DIMENSIONS
# ==================================================
if "Order_Date" in df.columns:
  df["Year"] = df["Order_Date"].dt.year
  df["Month"] = df["Order_Date"].dt.month_name()
  df["Quarter"] = df["Order_Date"].dt.quarter
  df["DayOfWeek"] = df["Order_Date"].dt.day_name()

if "Sales" in df.columns and "Profit" in df.columns:
  df["Profit_Margin"] = np.where(df["Sales"] != 0, df["Profit"] / df["Sales"], 0)

dim_defaults = {
    "Product_ID": "PROD_UNKNOWN",
    "Product_Name": "Unknown Product",
    "Category": "Uncategorized",
    "Sub_Category": "General",
    "Customer_ID": "CUST_UNKNOWN",
    "Customer_Name": "Unknown Customer",
    "Segment": "Consumer",
    "Ship_Mode": "Standard",
    "Order_Priority": "Medium",
    "Country": "Unknown",
    "City": "Unknown",
    "State": "Unknown",
    "Postal_Code": "N/A",
    "Region": "Unknown",
    "Market": "Unknown",
}

for col, default_val in dim_defaults.items():
  if col not in df.columns or df[col].isnull().all():
    df[col] = default_val

if "Row_ID" not in df.columns or df["Row_ID"].isnull().all():
  df["Row_ID"] = range(1, len(df) + 1)

if "Location_ID" not in df.columns:
  df["Location_ID"] = (
      df["Country"].astype(str)
      + "_"
      + df["State"].astype(str)
      + "_"
      + df["City"].astype(str)
  ).factorize()[0] + 1

print("Feature engineering and dimension safeguards completed.")

# ==================================================
# 7. STAR SCHEMA TRANSFORMATION & SQL WRITE-BACK
# ==================================================
print("\nPreparing Star Schema tables for SQL Server write-back...")

dim_product = (
    df[["Product_ID", "Product_Name", "Category", "Sub_Category"]]
    .drop_duplicates(subset=["Product_ID"])
    .copy()
)
dim_customer = (
    df[["Customer_ID", "Customer_Name", "Segment"]]
    .drop_duplicates(subset=["Customer_ID"])
    .copy()
)
dim_location = (
    df[
        [
            "Location_ID",
            "Country",
            "City",
            "State",
            "Postal_Code",
            "Region",
            "Market",
        ]
    ]
    .drop_duplicates(subset=["Location_ID"])
    .copy()
)
fact_sales = df[
    [
        "Row_ID",
        "Order_ID",
        "Order_Date",
        "Ship_Date",
        "Ship_Mode",
        "Customer_ID",
        "Product_ID",
        "Location_ID",
        "Sales",
        "Quantity",
        "Discount",
        "Profit",
        "Shipping_Cost",
        "Order_Priority",
        "Year",
        "Month",
        "Quarter",
        "DayOfWeek",
        "Profit_Margin",
    ]
].copy()

# Write clean tables to SQL Server using safe drop order (children first, then parents)
with engine.begin() as conn:
  print(
      "Dropping existing tables in correct dependency order to prevent"
      " constraint errors..."
  )
  # Drop child / prediction tables first
  conn.execute(
      text(
          "IF OBJECT_ID('fact_sales_predictions', 'U') IS NOT NULL DROP TABLE"
          " fact_sales_predictions;"
      )
  )
  conn.execute(
      text(
          "IF OBJECT_ID('fact_sales', 'U') IS NOT NULL DROP TABLE fact_sales;"
      )
  )
  # Now drop parent dimension tables safely
  conn.execute(
      text(
          "IF OBJECT_ID('dim_product', 'U') IS NOT NULL DROP TABLE dim_product;"
      )
  )
  conn.execute(
      text(
          "IF OBJECT_ID('dim_customer', 'U') IS NOT NULL DROP TABLE"
          " dim_customer;"
      )
  )
  conn.execute(
      text(
          "IF OBJECT_ID('dim_location', 'U') IS NOT NULL DROP TABLE"
          " dim_location;"
      )
  )

  print("Writing fresh Star Schema tables to MS SQL Server...")
  dim_product.to_sql("dim_product", conn, if_exists="append", index=False)
  dim_customer.to_sql("dim_customer", conn, if_exists="append", index=False)
  dim_location.to_sql("dim_location", conn, if_exists="append", index=False)
  fact_sales.to_sql("fact_sales", conn, if_exists="append", index=False)

print("\n" + "=" * 60)
print("ETL PIPELINE COMPLETED SUCCESSFULLY IN MS SQL SERVER")
print("Clean tables successfully updated: dim_product, dim_customer, dim_location, fact_sales")
print("=" * 60)