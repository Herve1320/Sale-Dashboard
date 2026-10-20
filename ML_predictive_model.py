import os
from urllib.parse import quote_plus
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy import create_engine, text

# ==================================================
# 0. AUTOMATIC LOCAL CLEANUP (Prevents Stale Files)
# ==================================================
print("Checking for previous run local artifacts to clean up...")
local_artifacts = [
    "margin_risk_model.joblib",
    "shipping_cost_model.joblib",
    "ml_model_evaluation.png",
    "feature_importance_profitability.png",
]

for artifact in local_artifacts:
  if os.path.exists(artifact):
    os.remove(artifact)
    print(f" -> Deleted old local file: {artifact}")
print("Local cleanup complete. Starting fresh execution...\n")

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

# SQL Query joining Fact Table with Star Schema Dimensions from SQL
sql_query = """
SELECT 
    f.Row_ID,
    f.Order_ID,
    f.Sales,
    f.Quantity,
    f.Discount,
    f.Profit,
    f.Shipping_Cost,
    f.Ship_Mode,
    f.Order_Priority,
    p.Category,
    p.Sub_Category,
    c.Segment,
    l.Market,
    l.Region
FROM fact_sales f
JOIN dim_product p ON f.Product_ID = p.Product_ID
JOIN dim_customer c ON f.Customer_ID = c.Customer_ID
JOIN dim_location l ON f.Location_ID = l.Location_ID;
"""

df = pd.read_sql(sql_query, engine)
print(f"Loaded {len(df)} transactions from SQL Server for model training.")

# ==================================================
# 2. TARGET CREATION & FEATURE ENGINEERING
# ==================================================
df["Is_Unprofitable"] = (df["Profit"] < 0).astype(int)
df["High_Shipping_Cost"] = (df["Shipping_Cost"] > 25).astype(int)

num_features = ["Discount", "Quantity", "Sales"]
cat_features = [
    "Category",
    "Sub_Category",
    "Segment",
    "Market",
    "Region",
    "Ship_Mode",
    "Order_Priority",
]

X = df[num_features + cat_features]
y_margin = df["Is_Unprofitable"]
y_shipping = df["High_Shipping_Cost"]

preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), num_features),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
    ]
)

# ==================================================
# 3. TRAIN MODEL 1: PROFITABILITY RISK
# ==================================================
print("\nTraining Model 1: Profitability Risk Classifier...")
X_train_m, X_test_m, y_train_m, y_test_m = train_test_split(
    X, y_margin, test_size=0.20, random_state=42, stratify=y_margin
)

margin_pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=100, max_depth=12, random_state=42
            ),
        ),
    ]
)

margin_pipeline.fit(X_train_m, y_train_m)
y_pred_m = margin_pipeline.predict(X_test_m)
y_proba_m = margin_pipeline.predict_proba(X_test_m)[:, 1]

print("\nClassification Report (Profitability Risk):")
print(classification_report(y_test_m, y_pred_m))
print(f"ROC-AUC Score: {roc_auc_score(y_test_m, y_proba_m):.4f}")

# Save model locally
joblib.dump(margin_pipeline, "margin_risk_model.joblib")
print("Saved local model: 'margin_risk_model.joblib'")

# ==================================================
# 4. TRAIN MODEL 2: HIGH LOGISTICS COST
# ==================================================
print("\nTraining Model 2: High Logistics Cost Classifier...")
X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(
    X, y_shipping, test_size=0.20, random_state=42, stratify=y_shipping
)

shipping_pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=100, max_depth=12, random_state=42
            ),
        ),
    ]
)

shipping_pipeline.fit(X_train_s, y_train_s)
y_pred_s = shipping_pipeline.predict(X_test_s)
y_proba_s = shipping_pipeline.predict_proba(X_test_s)[:, 1]

print("\nClassification Report (High Logistics Cost):")
print(classification_report(y_test_s, y_pred_s))
print(f"ROC-AUC Score: {roc_auc_score(y_test_s, y_proba_s):.4f}")

# Save model locally
joblib.dump(shipping_pipeline, "shipping_cost_model.joblib")
print("Saved local model: 'shipping_cost_model.joblib'")

# ==================================================
# 5. GENERATE & SAVE LOCAL EXPLANATION GRAPHICS
# ==================================================
print("\nGenerating and saving local explanation graphics...")

# Graphic 1: Confusion Matrix & ROC Curves
fig, axes = plt.subplots(1, 2, figsize=(15, 5))

cm = confusion_matrix(y_test_m, y_pred_m)
sns.heatmap(
    cm,
    annot=True,
    fmt="d",
    cmap="Blues",
    ax=axes[0],
    xticklabels=["Profitable (0)", "Unprofitable (1)"],
    yticklabels=["Profitable (0)", "Unprofitable (1)"],
)
axes[0].set_title(
    "Confusion Matrix: Profitability Risk Model", fontsize=12, fontweight="bold"
)
axes[0].set_xlabel("Predicted Label")
axes[0].set_ylabel("True Label")

fpr_m, tpr_m, _ = roc_curve(y_test_m, y_proba_m)
fpr_s, tpr_s, _ = roc_curve(y_test_s, y_proba_s)

axes[1].plot(
    fpr_m,
    tpr_m,
    color="#e74c3c",
    lw=2,
    label=f"Margin Risk (AUC = {roc_auc_score(y_test_m, y_proba_m):.3f})",
)
axes[1].plot(
    fpr_s,
    tpr_s,
    color="#3498db",
    lw=2,
    label=f"Shipping Cost (AUC = {roc_auc_score(y_test_s, y_proba_s):.3f})",
)
axes[1].plot([0, 1], [0, 1], color="gray", linestyle="--")
axes[1].set_title(
    "ROC-AUC Curves for Predictive Models", fontsize=12, fontweight="bold"
)
axes[1].set_xlabel("False Positive Rate")
axes[1].set_ylabel("True Positive Rate")
axes[1].legend(loc="lower right")

plt.tight_layout()
plt.savefig("ml_model_evaluation.png", dpi=300)
plt.close()
print("Saved local image: 'ml_model_evaluation.png'")

# Graphic 2: Feature Importances
ohe = margin_pipeline.named_steps["preprocessor"].named_transformers_["cat"]
cat_names = ohe.get_feature_names_out(cat_features).tolist()
all_feature_names = num_features + cat_names

importances = margin_pipeline.named_steps["classifier"].feature_importances_
df_imp = (
    pd.DataFrame({"Feature": all_feature_names, "Importance": importances})
    .sort_values("Importance", ascending=False)
    .head(10)
)

plt.figure(figsize=(10, 5))
sns.barplot(data=df_imp, x="Importance", y="Feature", palette="viridis")
plt.title(
    "Top 10 Feature Importances: Profitability Risk Model",
    fontsize=12,
    fontweight="bold",
)
plt.xlabel("Importance Score")
plt.tight_layout()
plt.savefig("feature_importance_profitability.png", dpi=300)
plt.close()
print("Saved local image: 'feature_importance_profitability.png'")

# ==================================================
# 6. WRITE PREDICTIONS BACK TO MS SQL SERVER
# ==================================================
print("\nWriting predictions back to MS SQL Server...")

df["Predicted_Loss_Risk"] = margin_pipeline.predict(X)
df["Loss_Probability_Score"] = np.round(
    margin_pipeline.predict_proba(X)[:, 1], 4
)

df["Predicted_High_Ship_Cost"] = shipping_pipeline.predict(X)
df["Ship_Cost_Probability_Score"] = np.round(
    shipping_pipeline.predict_proba(X)[:, 1], 4
)

df_predictions = df[
    [
        "Row_ID",
        "Order_ID",
        "Is_Unprofitable",
        "Predicted_Loss_Risk",
        "Loss_Probability_Score",
        "High_Shipping_Cost",
        "Predicted_High_Ship_Cost",
        "Ship_Cost_Probability_Score",
    ]
].copy()

with engine.begin() as conn:
  conn.execute(
      text(
          "IF OBJECT_ID('fact_sales_predictions', 'U') IS NOT NULL DROP TABLE"
          " fact_sales_predictions;"
      )
  )
  df_predictions.to_sql(
      "fact_sales_predictions", conn, if_exists="replace", index=False
  )

print("Exported fresh 'fact_sales_predictions' table to MS SQL Server successfully!")
print("ML Pipeline Execution Completed Successfully!")