USE superstore_db;
GO

-- 1. RFM Customer Analysis View
IF OBJECT_ID('vw_rfm_analysis', 'V') IS NOT NULL DROP VIEW vw_rfm_analysis;
GO
CREATE VIEW vw_rfm_analysis AS
SELECT 
    c.Customer_ID,
    c.Customer_Name,
    c.Segment,
    MAX(f.Order_Date) AS Last_Order_Date,
    COUNT(DISTINCT f.Order_ID) AS Frequency,
    ROUND(SUM(f.Sales), 2) AS Monetary_Value,
    ROUND(SUM(f.Profit), 2) AS Total_Profit
FROM fact_sales f
JOIN dim_customer c ON f.Customer_ID = c.Customer_ID
GROUP BY c.Customer_ID, c.Customer_Name, c.Segment;
GO

-- 2. High Discount Margin Leakage View
IF OBJECT_ID('vw_discount_leakage', 'V') IS NOT NULL DROP VIEW vw_discount_leakage;
GO
CREATE VIEW vw_discount_leakage AS
SELECT 
    p.Category,
    p.Sub_Category,
    f.Discount,
    COUNT(f.Row_ID) AS Total_Orders,
    ROUND(SUM(f.Sales), 2) AS Total_Sales,
    ROUND(SUM(f.Profit), 2) AS Total_Profit,
    ROUND(AVG(f.Profit_Margin), 4) AS Avg_Profit_Margin
FROM fact_sales f
JOIN dim_product p ON f.Product_ID = p.Product_ID
WHERE f.Discount > 0.20
GROUP BY p.Category, p.Sub_Category, f.Discount;
GO

-- 3. Shipping Performance View
IF OBJECT_ID('vw_shipping_performance', 'V') IS NOT NULL DROP VIEW vw_shipping_performance;
GO
CREATE VIEW vw_shipping_performance AS
SELECT 
    f.Ship_Mode,
    f.Order_Priority,
    COUNT(f.Row_ID) AS Order_Count,
    ROUND(AVG(f.Shipping_Cost), 2) AS Avg_Shipping_Cost,
    ROUND(AVG(CAST(DATEDIFF(day, CAST(f.Order_Date AS DATE), CAST(f.Ship_Date AS DATE)) AS FLOAT)), 2) AS Avg_Shipping_Days
FROM fact_sales f
GROUP BY f.Ship_Mode, f.Order_Priority;
GO