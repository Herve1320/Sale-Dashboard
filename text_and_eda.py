import os
import re
from urllib.parse import quote_plus
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sqlalchemy import create_engine
from wordcloud import STOPWORDS, WordCloud

# ==================================================
# 0. AUTOMATIC LOCAL CLEANUP (Prevents Stale Files)
# ==================================================
print("Checking for previous run local EDA artifacts to clean up...")
local_artifacts = [
    "wordcloud_comparison.png",
    "discount_profitability_analysis.png",
]

for artifact in local_artifacts:
  if os.path.exists(artifact):
    os.remove(artifact)
    print(f" -> Deleted old local file: {artifact}")
print("Local cleanup complete. Starting fresh execution...\n")

# ==================================================
# 1. DATABASE CONFIGURATION & SQL INGESTION
# ==================================================
DB_SERVER = "localhost"  # Or "localhost\\SQLEXPRESS"
DB_NAME = "superstore_db"
DB_DRIVER = "ODBC Driver 17 for SQL Server"
DB_TRUSTED = True

driver_encoded = quote_plus(DB_DRIVER)
trusted_flag = "yes" if DB_TRUSTED else "no"

db_url = f"mssql+pyodbc://@{DB_SERVER}/{DB_NAME}?driver={driver_encoded}&trusted_connection={trusted_flag}"
engine = create_engine(db_url)

print(f"Connecting to MS SQL Server database '{DB_NAME}'...")

# Query pulling directly from SQL Star Schema tables
query = """
SELECT 
    f.Row_ID,
    f.Sales,
    f.Quantity,
    f.Discount,
    f.Profit,
    f.Shipping_Cost,
    f.Profit_Margin,
    p.Product_Name,
    p.Category,
    p.Sub_Category
FROM fact_sales f
JOIN dim_product p ON f.Product_ID = p.Product_ID;
"""

df = pd.read_sql(query, engine)
print(f"Successfully loaded {len(df)} records from MS SQL Server!")

# ==================================================
# 2. TEXT CLEANING & TOKENIZATION
# ==================================================
custom_stopwords = set(STOPWORDS)
custom_stopwords.update([
    "pack",
    "set",
    "box",
    "per",
    "size",
    "black",
    "white",
    "blue",
    "red",
    "clear",
    "model",
    "series",
    "paper",
    "s",
    "x",
    "ct",
    "lb",
    "inch",
    "inches",
    "mm",
    "cm",
])


def clean_product_name(text):
  if not isinstance(text, str):
    return ""
  text = re.sub(r"[^a-zA-Z\s]", "", text.lower())
  words = [w for w in text.split() if w not in custom_stopwords and len(w) > 2]
  return " ".join(words)


df["Clean_Product_Name"] = df["Product_Name"].apply(clean_product_name)

# ==================================================
# 3. GENERATE & SAVE COMPARATIVE WORD CLOUDS LOCALLY
# ==================================================
profitable_text = " ".join(df[df["Profit"] > 0]["Clean_Product_Name"])
unprofitable_text = " ".join(df[df["Profit"] < 0]["Clean_Product_Name"])

wc_profit = WordCloud(
    width=800, height=400, background_color="white", colormap="Greens"
).generate(profitable_text)
wc_loss = WordCloud(
    width=800, height=400, background_color="white", colormap="Reds"
).generate(unprofitable_text)

fig, axes = plt.subplots(1, 2, figsize=(18, 7))

axes[0].imshow(wc_profit, interpolation="bilinear")
axes[0].set_title(
    "Top Product Keywords in Profitable Orders",
    fontsize=15,
    fontweight="bold",
    pad=15,
)
axes[0].axis("off")

axes[1].imshow(wc_loss, interpolation="bilinear")
axes[1].set_title(
    "Top Product Keywords in Unprofitable Orders (Losses)",
    fontsize=15,
    fontweight="bold",
    pad=15,
)
axes[1].axis("off")

plt.tight_layout()
plt.savefig("wordcloud_comparison.png", dpi=300)
plt.close()
print("Saved local image: 'wordcloud_comparison.png'")

# ==================================================
# 4. DISCOUNT SENSITIVITY & PROFIT LEAKAGE ANALYSIS
# ==================================================
bins = [-0.01, 0.0, 0.10, 0.20, 0.30, 0.50, 1.0]
labels = [
    "0% (Full Price)",
    "1% - 10%",
    "11% - 20%",
    "21% - 30%",
    "31% - 50%",
    "> 50%",
]

df["Discount_Band"] = pd.cut(df["Discount"], bins=bins, labels=labels)

band_summary = (
    df.groupby("Discount_Band", observed=False)
    .agg(
        Total_Orders=("Row_ID", "count"),
        Total_Sales=("Sales", "sum"),
        Total_Profit=("Profit", "sum"),
        Avg_Margin=("Profit_Margin", "mean"),
        Unprofitable_Orders=("Profit", lambda x: (x < 0).sum()),
    )
    .reset_index()
)

band_summary["Unprofitable_Pct"] = (
    band_summary["Unprofitable_Orders"] / band_summary["Total_Orders"]
) * 100

print("\n--- Discount Band Performance Summary (MS SQL Source) ---")
print(
    band_summary[
        [
            "Discount_Band",
            "Total_Orders",
            "Total_Profit",
            "Avg_Margin",
            "Unprofitable_Pct",
        ]
    ]
)

# ==================================================
# 5. GENERATE & SAVE DUAL-AXIS DIAGNOSTIC CHART LOCALLY
# ==================================================
fig, ax1 = plt.subplots(figsize=(12, 6))

color_bars = np.where(band_summary["Total_Profit"] > 0, "#2ecc71", "#e74c3c")
bars = ax1.bar(
    band_summary["Discount_Band"],
    band_summary["Total_Profit"],
    color=color_bars,
    alpha=0.85,
    width=0.45,
)

ax1.set_xlabel("Discount Band", fontsize=12, fontweight="bold")
ax1.set_ylabel(
    "Total Net Profit ($)", color="#2c3e50", fontsize=12, fontweight="bold"
)
ax1.axhline(0, color="black", linewidth=1, linestyle="--")
ax1.tick_params(axis="y", labelcolor="#2c3e50")

ax2 = ax1.twinx()
line = ax2.plot(
    band_summary["Discount_Band"],
    band_summary["Unprofitable_Pct"],
    color="#8e44ad",
    marker="o",
    linewidth=3,
    markersize=8,
)

ax2.set_ylabel(
    "Unprofitable Orders (%)", color="#8e44ad", fontsize=12, fontweight="bold"
)
ax2.tick_params(axis="y", labelcolor="#8e44ad")

plt.title(
    "Discount Sensitivity & Profit Leakage Diagnostic (MS SQL Server Source)",
    fontsize=14,
    fontweight="bold",
    pad=15,
)
fig.tight_layout()
plt.savefig("discount_profitability_analysis.png", dpi=300)
plt.close()

print("Saved local image: 'discount_profitability_analysis.png'")
print("\nText & Discount EDA Script Completed Successfully!")