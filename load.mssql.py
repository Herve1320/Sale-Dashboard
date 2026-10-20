import pandas as pd
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

# ==================================================
# 1. DATABASE CONNECTION
# ==================================================
DB_SERVER = "localhost"  # Or "localhost\\SQLEXPRESS"
DB_NAME = "superstore_db"
DB_DRIVER = "ODBC Driver 17 for SQL Server"
DB_TRUSTED = True

driver_encoded = quote_plus(DB_DRIVER)
trusted_flag = "yes" if DB_TRUSTED else "no"

db_url = f"mssql+pyodbc://@{DB_SERVER}/{DB_NAME}?driver={driver_encoded}&trusted_connection={trusted_flag}"
engine = create_engine(db_url)

# ==================================================
# 2. LOAD & TRANSFORM DATA
# ==================================================
df = pd.read_csv("data\\cleaned_sales.csv")
df["Order Date"] = pd.to_datetime(df["Order Date"])
df["Ship Date"] = pd.to_datetime(df["Ship Date"])

# Dimension: Customer
dim_customer = (
    df[["Customer ID", "Customer Name", "Segment"]]
    .drop_duplicates(subset=["Customer ID"])
    .rename(columns={"Customer ID": "Customer_ID", "Customer Name": "Customer_Name"})
)

# Dimension: Product
dim_product = (
    df[["Product ID", "Product Name", "Category", "Sub-Category"]]
    .drop_duplicates(subset=["Product ID"])
    .rename(columns={"Product ID": "Product_ID", "Product Name": "Product_Name", "Sub-Category": "Sub_Category"})
)

# Dimension: Location (NOW INCLUDES REGION)
dim_location = (
    df[["City", "State", "Country", "Market", "Region"]]
    .drop_duplicates()
    .reset_index(drop=True)
)
dim_location["Location_ID"] = dim_location.index + 1

# Merge Location_ID back into main dataframe
df = df.merge(dim_location, on=["City", "State", "Country", "Market", "Region"], how="left")

# Dimension: Date
unique_dates = pd.date_range(
    start=min(df["Order Date"].min(), df["Ship Date"].min()),
    end=max(df["Order Date"].max(), df["Ship Date"].max()),
    freq="D"
)
dim_date = pd.DataFrame({"Date": unique_dates})
dim_date["Date_Key"] = dim_date["Date"].dt.strftime("%Y-%m-%d")
dim_date["Year"] = dim_date["Date"].dt.year
dim_date["Quarter"] = dim_date["Date"].dt.quarter
dim_date["Month"] = dim_date["Date"].dt.month_name()
dim_date["DayOfWeek"] = dim_date["Date"].dt.day_name()
dim_date["WeekNum"] = dim_date["Date"].dt.isocalendar().week

df["Order_Date_Key"] = df["Order Date"].dt.strftime("%Y-%m-%d")
df["Ship_Date_Key"] = df["Ship Date"].dt.strftime("%Y-%m-%d")

# Fact: Sales
fact_sales = df[[
    "Row ID", "Order ID", "Order_Date_Key", "Ship_Date_Key",
    "Customer ID", "Product ID", "Location_ID", "Ship Mode",
    "Order Priority", "Sales", "Quantity", "Discount", "Profit",
    "Shipping Cost", "Profit Margin"
]].rename(columns={
    "Row ID": "Row_ID", "Order ID": "Order_ID", "Order_Date_Key": "Order_Date",
    "Ship_Date_Key": "Ship_Date", "Customer ID": "Customer_ID", "Product ID": "Product_ID",
    "Ship Mode": "Ship_Mode", "Order Priority": "Order_Priority",
    "Shipping Cost": "Shipping_Cost", "Profit Margin": "Profit_Margin"
})

# ==================================================
# 3. TRUNCATE & LOAD DATA INTO MS SQL SERVER
# ==================================================
with engine.begin() as conn:
    print("Clearing old data from tables...")
    conn.execute(text("DELETE FROM fact_sales;"))
    conn.execute(text("DELETE FROM dim_customer;"))
    conn.execute(text("DELETE FROM dim_product;"))
    conn.execute(text("DELETE FROM dim_location;"))
    conn.execute(text("DELETE FROM dim_date;"))

    print("Populating dim_customer...")
    dim_customer.to_sql("dim_customer", conn, if_exists="append", index=False)

    print("Populating dim_product...")
    dim_product.to_sql("dim_product", conn, if_exists="append", index=False)

    print("Populating dim_location (with Region)...")
    dim_location.to_sql("dim_location", conn, if_exists="append", index=False)

    print("Populating dim_date...")
    dim_date.to_sql("dim_date", conn, if_exists="append", index=False)

    print("Populating fact_sales...")
    fact_sales.to_sql("fact_sales", conn, if_exists="append", index=False)

print("Data reloaded successfully with 'Region' included!")